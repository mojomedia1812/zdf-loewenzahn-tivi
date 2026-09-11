# -*- coding: utf-8 -*-
import hashlib
import os
import shutil
import xml.etree.ElementTree as ET
import zipfile


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ADDON_IDS = (
    "plugin.video.zdf-loewenzahn-tivi",
    "repository.m0j01812",
)
REPOSITORY_DIR = os.path.join(ROOT, "repository")


def read_addon_xml(addon_id):
    path = os.path.join(ROOT, addon_id, "addon.xml")
    tree = ET.parse(path)
    return path, tree.getroot()


def addon_version(addon_id):
    _, root = read_addon_xml(addon_id)
    return root.get("version")


def should_skip(path):
    normalized = path.replace("\\", "/")
    return (
        "/__pycache__/" in normalized
        or normalized.endswith(".pyc")
        or normalized.endswith(".pyo")
        or "/resources/artwork/" in normalized
    )


def write_zip(addon_id, target_path):
    addon_root = os.path.join(ROOT, addon_id)
    with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for current_root, _, files in os.walk(addon_root):
            for filename in files:
                full_path = os.path.join(current_root, filename)
                if should_skip(full_path):
                    continue
                rel_path = os.path.relpath(full_path, ROOT).replace("\\", "/")
                archive.write(full_path, rel_path)


def metadata_text(addon_id, version):
    _, root = read_addon_xml(addon_id)
    news = root.find("./extension[@point='xbmc.addon.metadata']/news")
    if news is not None and news.text:
        return news.text.strip() + "\n"
    return "{0} {1}\n".format(addon_id, version)


def write_repository_assets(addon_id, version, zip_path):
    target_dir = os.path.join(REPOSITORY_DIR, addon_id)
    os.makedirs(target_dir, exist_ok=True)
    shutil.copy2(zip_path, os.path.join(target_dir, os.path.basename(zip_path)))
    for asset in ("icon.png", "fanart.jpg"):
        source = os.path.join(ROOT, addon_id, asset)
        if os.path.isfile(source):
            shutil.copy2(source, os.path.join(target_dir, asset))
    changelog = os.path.join(target_dir, "changelog-{0}.txt".format(version))
    with open(changelog, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(metadata_text(addon_id, version))


def strip_xml_declaration(text):
    lines = text.splitlines()
    if lines and lines[0].lstrip().startswith("<?xml"):
        return "\n".join(lines[1:])
    return text


def build_addons_xml():
    parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', "<addons>"]
    for addon_id in ADDON_IDS:
        addon_xml_path = os.path.join(ROOT, addon_id, "addon.xml")
        with open(addon_xml_path, "r", encoding="utf-8") as handle:
            parts.append(strip_xml_declaration(handle.read()).strip())
    parts.append("</addons>")
    text = "\n".join(parts) + "\n"
    addons_xml_path = os.path.join(REPOSITORY_DIR, "addons.xml")
    with open(addons_xml_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    checksum = hashlib.md5(text.encode("utf-8")).hexdigest()
    with open(addons_xml_path + ".md5", "w", encoding="utf-8", newline="\n") as handle:
        handle.write(checksum)


def main():
    os.makedirs(REPOSITORY_DIR, exist_ok=True)
    built = []
    for addon_id in ADDON_IDS:
        version = addon_version(addon_id)
        zip_name = "{0}-{1}.zip".format(addon_id, version)
        zip_path = os.path.join(ROOT, zip_name)
        write_zip(addon_id, zip_path)
        write_repository_assets(addon_id, version, zip_path)
        built.append(zip_name)
    build_addons_xml()
    print("Built:", ", ".join(built))
    print("Repository:", REPOSITORY_DIR)


if __name__ == "__main__":
    main()
