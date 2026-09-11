# -*- coding: utf-8 -*-
import argparse
import os
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, ROOT)

from zdf_api import (  # noqa: E402
    ZdfSession,
    episode_title,
    format_episode_label,
    pick_vod_media,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-stream", action="store_true", help="skip PTMD stream resolution")
    args = parser.parse_args()

    api = ZdfSession()
    series = api.get_series()
    print("Serien:", ", ".join("{0}={1}".format(item["key"], item["title"]) for item in series))

    first_episode = None
    for item in series:
        seasons = api.get_seasons(item["canonical"])
        print(
            "{0}: {1} Staffeln, erste API-Staffel: {2}".format(
                item["label"],
                len(seasons),
                seasons[0].get("number") if seasons else "-",
            )
        )
        if item["key"] == "fritz" and seasons:
            episodes = api.get_episodes(item["canonical"], seasons[0]["id"])
            print("Fritz Staffel {0}: {1} Folgen".format(seasons[0].get("number"), len(episodes)))
            if episodes:
                first_episode = episodes[0]
                print("Erste Folge:", format_episode_label(first_episode))

    if args.no_stream or not first_episode:
        return 0

    media = pick_vod_media(first_episode)
    if not media:
        raise SystemExit("Keine abspielbare Media-Node fuer {0}".format(episode_title(first_episode)))
    stream = api.resolve_ptmd_template(media["ptmdTemplate"])
    print("Stream MIME:", stream.get("mime_type"))
    print("Stream HLS:", stream.get("is_hls"))
    print("Stream URL:", stream["url"][:180])
    print("Untertitel:", len(stream.get("subtitles") or []))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
