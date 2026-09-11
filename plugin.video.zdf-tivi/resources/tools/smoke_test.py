# -*- coding: utf-8 -*-
import argparse
import os
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, ROOT)

from zdf_api import (  # noqa: E402
    AZ_CATALOG_CANONICAL,
    START_COLLECTION_CANONICAL,
    ZdfSession,
    document_title,
    format_video_label,
    is_movie_collection,
    is_series_collection,
    pick_vod_media,
    video_title,
)


def _find_first(items, predicate):
    for item in items:
        if predicate(item):
            return item
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-stream", action="store_true", help="skip PTMD stream resolution")
    args = parser.parse_args()

    api = ZdfSession()

    modules = api.get_curated_modules(START_COLLECTION_CANONICAL)
    print("Startseiten-Module:", len(modules))
    for module in modules[:8]:
        print(" - {0} ({1})".format(module["title"], module["totalCount"]))
    if not modules:
        raise SystemExit("Keine ZDFtivi-Startseitenmodule gefunden")

    first_module = modules[0]
    module_items = api.get_curated_module_items(START_COLLECTION_CANONICAL, first_module["id"])
    print("Erstes Modul:", first_module["title"], "Items:", len(module_items["items"]))
    if not module_items["items"]:
        raise SystemExit("Keine Items im ersten ZDFtivi-Modul gefunden")

    catalog = api.get_catalog_tabs(AZ_CATALOG_CANONICAL)
    tabs = [tab for tab in catalog["tabs"] if tab.get("count")]
    print("A-Z-Tabs mit Inhalt:", len(tabs))
    if not tabs:
        raise SystemExit("Keine ZDFtivi-A-Z-Tabs gefunden")

    b_tab = _find_first(tabs, lambda tab: tab.get("title") == "B") or tabs[0]
    catalog_items = api.get_catalog_items(b_tab["index"], AZ_CATALOG_CANONICAL)
    print("A-Z {0}: {1} Items".format(b_tab["title"], len(catalog_items["items"])))
    if not catalog_items["items"]:
        raise SystemExit("Keine ZDFtivi-A-Z-Items gefunden")

    all_seen = module_items["items"] + catalog_items["items"]
    first_series = _find_first(all_seen, is_series_collection)
    if not first_series:
        raise SystemExit("Keine Serien-Sammlung gefunden")

    seasons = api.get_seasons(first_series["canonical"])
    print("Serie:", document_title(first_series), "Staffeln:", len(seasons))
    if not seasons:
        raise SystemExit("Keine Staffeln fuer {0} gefunden".format(document_title(first_series)))

    episodes = api.get_episodes(first_series["canonical"], seasons[0]["id"], seasons[0].get("number"))
    print("Erste Staffel:", seasons[0].get("title"), "Folgen:", len(episodes))
    if not episodes:
        raise SystemExit("Keine Folgen fuer {0} gefunden".format(document_title(first_series)))

    playable_video = _find_first(episodes, pick_vod_media)
    if not playable_video:
        raise SystemExit("Keine abspielbare Folge fuer {0} gefunden".format(document_title(first_series)))
    print("Erste abspielbare Folge:", format_video_label(playable_video))

    movie = _find_first(all_seen, is_movie_collection)
    if movie:
        collection = api.get_collection(movie["canonical"])
        movie_video = collection.get("video") or {}
        print("Film:", document_title(collection), "Video:", video_title(movie_video))

    if args.no_stream:
        return 0

    media = pick_vod_media(playable_video)
    stream = api.resolve_ptmd_template(media["ptmdTemplate"])
    print("Stream MIME:", stream.get("mime_type"))
    print("Stream HLS:", stream.get("is_hls"))
    print("Stream URL:", stream["url"][:180])
    print("Untertitel:", len(stream.get("subtitles") or []))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
