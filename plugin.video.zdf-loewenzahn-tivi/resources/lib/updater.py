# -*- coding: utf-8 -*-
import json
import os
import re
import time
import urllib.error
import urllib.request


ADDON_ID = "plugin.video.zdf-loewenzahn-tivi"
GITHUB_LATEST_RELEASE_URL = (
    "https://api.github.com/repos/mojomedia1812/zdf-loewenzahn-tivi/releases/latest"
)
CHECK_INTERVAL_SECONDS = 6 * 60 * 60
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


def should_check_now(xbmcvfs, now=None, interval=CHECK_INTERVAL_SECONDS):
    now = now or time.time()
    state = _load_state(xbmcvfs)
    return now - float(state.get("last_checked") or 0) >= interval


def _record_check(xbmcvfs, now=None):
    _save_state(xbmcvfs, {"last_checked": now or time.time()})


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
    target_directory = _translate_path(xbmcvfs, "special://temp")
    if not os.path.isdir(target_directory):
        os.makedirs(target_directory, exist_ok=True)
    target_path = os.path.join(target_directory, filename)
    _download_file(update_info["download_url"], target_path)
    return target_path


def maybe_offer_update(addon, xbmc, xbmcgui, xbmcvfs, force=False):
    if not force and not should_check_now(xbmcvfs):
        return None

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

    message = (
        "Installiert: {0}\n"
        "Verfügbar: {1}\n\n"
        "Update-ZIP herunterladen und den Kodi-Installationsdialog öffnen?"
    ).format(current_version, update_info["version"])
    dialog = xbmcgui.Dialog()
    if not dialog.yesno("Update verfügbar", message):
        return update_info

    try:
        zip_path = download_update_zip(update_info, xbmcvfs)
    except UpdateError as exc:
        dialog.notification(ADDON_ID, str(exc), xbmcgui.NOTIFICATION_ERROR, 8000)
        return update_info

    dialog.ok(
        "Update heruntergeladen",
        "Kodi öffnet jetzt die ZIP-Installation.\n\nDatei: {0}".format(zip_path),
    )
    xbmc.executebuiltin('InstallFromZip("{0}")'.format(zip_path.replace("\\", "/")))
    return update_info
