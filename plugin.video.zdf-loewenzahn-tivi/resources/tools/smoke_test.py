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


def assert_episode_order(name, episodes):
    episode_numbers = [
        (episode.get("episodeInfo") or {}).get("episodeNumber")
        for episode in episodes
        if (episode.get("episodeInfo") or {}).get("episodeNumber")
    ]
    if episode_numbers != sorted(episode_numbers):
        raise SystemExit("{0}: Folgen sind nicht nach Folgennummer sortiert".format(name))


def assert_season_order(name, seasons):
    season_numbers = [
        season.get("number")
        for season in seasons
        if season.get("number")
    ]
    if season_numbers != sorted(season_numbers):
        raise SystemExit("{0}: Staffeln sind nicht aufsteigend sortiert".format(name))


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
        assert_season_order(item["label"], seasons)
        print(
            "{0}: {1} Staffeln, erste Staffel: {2}".format(
                item["label"],
                len(seasons),
                seasons[0].get("number") if seasons else "-",
            )
        )
        if item["key"] == "fritz" and seasons:
            episodes = api.get_episodes(item["canonical"], seasons[0]["id"])
            assert_episode_order("Fritz", episodes)
            print("Fritz Staffel {0}: {1} Folgen".format(seasons[0].get("number"), len(episodes)))
            print("Folgensortierung:", "OK")
            if episodes:
                first_episode = episodes[0]
                print("Erste Folge:", format_episode_label(first_episode))

        if item["key"] == "peter":
            season_one = next((season for season in seasons if season.get("number") == 1), None)
            if not season_one:
                raise SystemExit("Peter Lustig Staffel 1 nicht gefunden")
            peter_episodes = api.get_episodes(item["canonical"], season_one["id"])
            assert_episode_order("Peter Lustig Staffel 1", peter_episodes)
            if not peter_episodes:
                raise SystemExit("Peter Lustig Staffel 1 enthaelt keine Folgen")
            peter_first = peter_episodes[0]
            peter_label = format_episode_label(peter_first)
            if episode_title(peter_first) != "Umzug":
                raise SystemExit("Peter Lustig Staffel 1: erste Folge ist nicht Umzug")
            if not peter_label.startswith("Folge 01 - "):
                raise SystemExit("Peter Lustig Staffel 1: Folgenbezeichnung enthaelt keine Folgennummer")
            print("Peter Staffel 1: {0} an Position 1".format(peter_label))

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
