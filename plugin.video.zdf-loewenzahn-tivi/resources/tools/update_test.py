# -*- coding: utf-8 -*-
import os
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, ROOT)

from updater import check_for_update, is_newer_version, latest_release_info  # noqa: E402


def main():
    fake_release = {
        "tag_name": "2026.09.11.3",
        "html_url": "https://example.invalid/release",
        "assets": [
            {
                "name": "plugin.video.zdf-loewenzahn-tivi-2026.09.11.3.zip",
                "browser_download_url": "https://example.invalid/addon.zip",
            }
        ],
    }

    assert is_newer_version("2026.09.11.3", "2026.09.11.2")
    assert not is_newer_version("2026.09.11.2", "2026.09.11.2")
    assert check_for_update("2026.09.11.2", fake_release)["version"] == "2026.09.11.3"
    assert check_for_update("2026.09.11.3", fake_release) is None

    latest = latest_release_info()
    if latest:
        print("Latest GitHub release:", latest["version"])
        print("Release asset:", latest["filename"])
    print("Update-Test: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
