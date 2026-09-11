# -*- coding: utf-8 -*-
import json
import os
import re
import time
import urllib.error
import urllib.request
import zipfile
import xml.etree.ElementTree as ET


ADDON_ID = "plugin.video.zdf-loewenzahn-tivi"
GITHUB_LATEST_RELEASE_URL = (
    "https://api.github.com/repos/mojomedia1812/zdf-loewenzahn-tivi/releases/latest"
)
USER_AGENT = "zdf-loewenzahn-tivi-update-check"


class UpdateError(Exception):
    """Raised when an available update cannot be downloaded or prepared."""


def parse_version(value):
    numbers = [int(part) for part in re.findall(r"\d+", value or "")[:4]]
    while len(numbers) < 4:
        numbers.append(0)
    return tuple(numbers)


def is_newer_version(remote_version, current_version):
    return parse_version(remote_version) > parse_version(current_version)


def _http_json(url, timeout=10):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def _find_zip_asset(release):
    assets = release.get("assets") or []
    for asset in assets:
        name = asset.get("name") or ""
        if (
            name.startswith(ADDON_ID)
            and name.endswith(".zip")
            and asset.get("browser_download_url")
        ):
            return asset
    return None


def latest_release_info(release=None):
    release = release or _http_json(GITHUB_LATEST_RELEASE_URL)
    version = release.get("tag_name") or release.get("name") or ""
    asset = _find_zip_asset(release)
    if not version or not asset:
        return None
    return {
        "version": version,
        "release_url": release.get("html_url"),
        "filename": asset.get("name"),
        "download_url": asset.get("browser_download_url"),
    }


def check_for_update(current_version, release=None):
    info = latest_release_info(release)
    if info and is_newer_version(info["version"], current_version):
        return info
    return None


def _translate_path(xbmcvfs, path):
    translated = xbmcvfs.translatePath(path)
    if isinstance(translated, bytes):
        translated = translated.decode("utf-8", "replace")
    return translated


def _state_path(xbmcvfs):
    directory = _translate_path(xbmcvfs, "special://profile/addon_data/{0}".format(ADDON_ID))
    if not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, "update-check.json")


def _load_state(xbmcvfs):
    try:
        with open(_state_path(xbmcvfs), "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


def _save_state(xbmcvfs, state):
    with open(_state_path(xbmcvfs), "w", encoding="utf-8") as handle:
        json.dump(state, handle, sort_keys=True)


def _record_check(xbmcvfs, now=None):
    state = _load_state(xbmcvfs)
    state["last_checked"] = now or time.time()
    _save_state(xbmcvfs, state)


def _record_dismissed(xbmcvfs, version, now=None):
    state = _load_state(xbmcvfs)
    state["dismissed_version"] = version
    state["dismissed_at"] = now or time.time()
    _save_state(xbmcvfs, state)


def should_prompt_for_update(xbmcvfs, update_info):
    state = _load_state(xbmcvfs)
    return state.get("dismissed_version") != update_info.get("version")


def _download_file(url, target_path, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            with open(target_path, "wb") as handle:
                while True:
                    chunk = response.read(1024 * 128)
                    if not chunk:
                        break
                    handle.write(chunk)
    except urllib.error.URLError as exc:
        raise UpdateError("Download fehlgeschlagen: {0}".format(exc))


def download_update_zip(update_info, xbmcvfs):
    filename = update_info.get("filename") or "{0}-{1}.zip".format(
        ADDON_ID,
        update_info["version"],
    )
    target_directory = _translate_path(xbmcvfs, "special://home/addons/packages")
    if not os.path.isdir(target_directory):
        os.makedirs(target_directory, exist_ok=True)
    target_path = os.path.join(target_directory, filename)
    _download_file(update_info["download_url"], target_path)
    return target_path


def _is_safe_zip_member(name):
    normalized = name.replace("\\", "/").strip("/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        return False
    return all(part not in ("", ".", "..") for part in normalized.split("/"))


def validate_update_zip(zip_path, expected_version):
    try:
        archive = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        raise UpdateError("Update-ZIP ist beschädigt: {0}".format(exc))

    with archive:
        names = archive.namelist()
        addon_xml_name = "{0}/addon.xml".format(ADDON_ID)
        if addon_xml_name not in names:
            raise UpdateError("Update-ZIP enthält kein gültiges addon.xml")

        for name in names:
            if not _is_safe_zip_member(name):
                raise UpdateError("Update-ZIP enthält einen unsicheren Dateipfad: {0}".format(name))
            if not name.startswith("{0}/".format(ADDON_ID)):
                raise UpdateError("Update-ZIP enthält unerwartete Dateien: {0}".format(name))

        try:
            addon_xml = ET.fromstring(archive.read(addon_xml_name))
        except ET.ParseError as exc:
            raise UpdateError("Update-ZIP enthält ein ungültiges addon.xml: {0}".format(exc))

        addon_id = addon_xml.get("id")
        version = addon_xml.get("version")
        if addon_id != ADDON_ID:
            raise UpdateError("Update-ZIP gehört zu einem anderen Addon: {0}".format(addon_id))
        if version != expected_version:
            raise UpdateError(
                "Update-ZIP-Version passt nicht zum GitHub-Release: {0} statt {1}".format(
                    version,
                    expected_version,
                )
            )

    return True


def _extract_update_zip(zip_path, xbmcvfs):
    target_directory = _translate_path(xbmcvfs, "special://home/addons")
    if not os.path.isdir(target_directory):
        os.makedirs(target_directory, exist_ok=True)

    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            if not _is_safe_zip_member(member.filename):
                raise UpdateError("Update-ZIP enthält einen unsicheren Dateipfad: {0}".format(member.filename))

            target_path = os.path.abspath(
                os.path.join(target_directory, *member.filename.replace("\\", "/").split("/"))
            )
            target_root = os.path.normcase(os.path.abspath(target_directory) + os.sep)
            if not os.path.normcase(target_path).startswith(target_root):
                raise UpdateError("Update-ZIP würde außerhalb des Addon-Verzeichnisses schreiben")

            parent = os.path.dirname(target_path)
            if not os.path.isdir(parent):
                os.makedirs(parent, exist_ok=True)
            with archive.open(member) as source, open(target_path, "wb") as target:
                while True:
                    chunk = source.read(1024 * 128)
                    if not chunk:
                        break
                    target.write(chunk)


def install_update(update_info, xbmcvfs, xbmc):
    zip_path = download_update_zip(update_info, xbmcvfs)
    validate_update_zip(zip_path, update_info["version"])
    _extract_update_zip(zip_path, xbmcvfs)
    xbmc.executebuiltin("UpdateLocalAddons", True)
    xbmc.executebuiltin("UpdateAddonRepos", True)
    xbmc.executebuiltin("Container.Refresh")
    return zip_path


def maybe_offer_update(addon, xbmc, xbmcgui, xbmcvfs, force=False):
    current_version = addon.getAddonInfo("version")
    try:
        update_info = check_for_update(current_version)
        _record_check(xbmcvfs)
    except Exception as exc:
        xbmc.log("{0}: Update check failed: {1}".format(ADDON_ID, exc), xbmc.LOGWARNING)
        _record_check(xbmcvfs)
        return None

    if not update_info:
        xbmc.log(
            "{0}: No GitHub update available for {1}".format(ADDON_ID, current_version),
            xbmc.LOGDEBUG,
        )
        return None

    if not force and not should_prompt_for_update(xbmcvfs, update_info):
        xbmc.log(
            "{0}: GitHub update {1} was dismissed before".format(
                ADDON_ID,
                update_info["version"],
            ),
            xbmc.LOGDEBUG,
        )
        return update_info

    message = (
        "Installiert: {0}\n"
        "Verfügbar: {1}\n\n"
        "Update-ZIP herunterladen, prüfen und installieren?"
    ).format(current_version, update_info["version"])
    dialog = xbmcgui.Dialog()
    if not dialog.yesno("Update verfügbar", message):
        _record_dismissed(xbmcvfs, update_info["version"])
        return update_info

    try:
        zip_path = install_update(update_info, xbmcvfs, xbmc)
    except UpdateError as exc:
        dialog.notification(ADDON_ID, str(exc), xbmcgui.NOTIFICATION_ERROR, 8000)
        return update_info

    dialog.ok(
        "Update installiert",
        "Version {0} wurde installiert.\n\nFalls Kodi noch die alte Version zeigt, Kodi neu starten.\n\nDatei: {1}".format(
            update_info["version"],
            zip_path,
        ),
    )
    return update_info
