# -*- coding: utf-8 -*-
import sys
import traceback
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from zdf_api import (
    AZ_CATALOG_CANONICAL,
    START_COLLECTION_CANONICAL,
    ZdfError,
    ZdfSession,
    document_image,
    document_plot,
    document_title,
    format_video_label,
    is_movie_collection,
    is_series_collection,
    pick_vod_media,
    video_image,
    video_plot,
    video_title,
)


ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo("name")
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]


def build_url(params):
    clean = {}
    for key, value in params.items():
        if value is not None:
            clean[key] = value
    return BASE_URL + "?" + urllib.parse.urlencode(clean)


def _as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _art(image_url):
    if not image_url:
        return {}
    return {
        "icon": image_url,
        "thumb": image_url,
        "poster": image_url,
        "fanart": image_url,
    }


def _notify_error(message):
    xbmc.log("{0}: {1}".format(ADDON_NAME, message), xbmc.LOGERROR)
    xbmcgui.Dialog().notification(ADDON_NAME, message, xbmcgui.NOTIFICATION_ERROR, 8000)


def _set_content(content):
    xbmcplugin.setContent(HANDLE, content)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL)


def _year(value):
    return _as_int(value, 0)


def _iso_date(value):
    if not value:
        return None
    return value[:10]


def _count_label(document):
    parts = []
    seasons = _as_int(document.get("countSeasons"))
    episodes = _as_int(document.get("countEpisodes"))
    if seasons:
        parts.append("{0} Staffel{1}".format(seasons, "" if seasons == 1 else "n"))
    if episodes:
        parts.append("{0} Folge{1}".format(episodes, "" if episodes == 1 else "n"))
    return ", ".join(parts)


def _collection_info(document):
    info = {
        "title": document_title(document),
        "plot": document_plot(document),
        "mediatype": "tvshow",
    }
    year = _year((document.get("editorialDate") or "")[:4])
    if year:
        info["year"] = year
    return info


def add_directory(label, params, image_url=None, info=None):
    item = xbmcgui.ListItem(label=label)
    item.setArt(_art(image_url))
    if info:
        item.setInfo("video", info)
    xbmcplugin.addDirectoryItem(HANDLE, build_url(params), item, isFolder=True)


def add_video(video, label=None, mediatype=None):
    media = pick_vod_media(video)
    if not media:
        return False

    info = video.get("episodeInfo") or {}
    title = video_title(video)
    item = xbmcgui.ListItem(label=label or format_video_label(video))
    item.setProperty("IsPlayable", "true")
    item.setArt(_art(video_image(video)))
    item.setInfo(
        "video",
        {
            "title": title,
            "plot": video_plot(video),
            "season": info.get("seasonNumber") or 0,
            "episode": info.get("episodeNumber") or 0,
            "year": video.get("productionYear") or 0,
            "duration": media.get("duration") or 0,
            "aired": _iso_date(video.get("editorialDate")) or "",
            "mediatype": mediatype or ("episode" if info.get("episodeNumber") else "movie"),
        },
    )
    xbmcplugin.addDirectoryItem(
        HANDLE,
        build_url(
            {
                "mode": "play",
                "ptmd": media.get("ptmdTemplate"),
                "title": title,
                "thumb": video_image(video) or "",
            }
        ),
        item,
        isFolder=False,
    )
    return True


def add_document(document):
    typename = document.get("__typename")
    if typename == "Video":
        return add_video(document)

    if is_movie_collection(document):
        movie_video = document.get("video") or {}
        if add_video(movie_video, label=document_title(document), mediatype="movie"):
            return True

    if is_series_collection(document):
        suffix = _count_label(document)
        label = document_title(document)
        if suffix:
            label = "{0} ({1})".format(label, suffix)
        add_directory(
            label,
            {
                "mode": "collection",
                "canonical": document.get("canonical"),
                "label": document_title(document),
            },
            document_image(document),
            _collection_info(document),
        )
        return True

    if typename == "CuratedCollection":
        add_directory(
            document_title(document),
            {
                "mode": "curated",
                "canonical": document.get("canonical"),
                "label": document_title(document),
            },
            document_image(document),
            {"title": document_title(document), "plot": document_plot(document), "mediatype": "tvshow"},
        )
        return True

    if typename == "MetaCollection":
        add_directory(
            document_title(document),
            {
                "mode": "meta",
                "canonical": document.get("canonical"),
                "label": document_title(document),
            },
            document_image(document),
            {"title": document_title(document), "plot": document_plot(document), "mediatype": "tvshow"},
        )
        return True

    if typename == "Catalog":
        add_directory(
            document_title(document),
            {"mode": "az", "canonical": document.get("canonical") or AZ_CATALOG_CANONICAL},
            document_image(document),
            {"title": document_title(document), "mediatype": "tvshow"},
        )
        return True

    return False


def list_root(api):
    _set_content("videos")
    add_directory(
        "Startseite / Rubriken",
        {"mode": "curated", "canonical": START_COLLECTION_CANONICAL, "label": "ZDFtivi"},
        None,
        {"title": "ZDFtivi", "mediatype": "tvshow"},
    )
    add_directory(
        "Sendungen A-Z",
        {"mode": "az", "canonical": AZ_CATALOG_CANONICAL},
        None,
        {"title": "ZDFtivi von A-Z", "mediatype": "tvshow"},
    )
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)


def list_curated(api, params):
    _set_content("tvshows")
    canonical = params.get("canonical") or START_COLLECTION_CANONICAL
    modules = api.get_curated_modules(canonical)
    for module in modules:
        count = _as_int(module.get("totalCount"))
        label = module.get("title") or "Weitere Inhalte"
        if count:
            label = "{0} ({1})".format(label, count)
        add_directory(
            label,
            {
                "mode": "module",
                "canonical": canonical,
                "module_id": module.get("id"),
                "offset": 0,
                "label": module.get("title") or "",
            },
            None,
            {"title": module.get("title") or label, "mediatype": "tvshow"},
        )
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)


def list_module_items(api, params):
    _set_content("videos")
    canonical = params.get("canonical") or START_COLLECTION_CANONICAL
    module_id = params.get("module_id")
    offset = _as_int(params.get("offset"))
    data = api.get_curated_module_items(canonical, module_id, grid_offset=offset)
    added = 0
    for document in data.get("items") or []:
        if add_document(document):
            added += 1

    if data.get("hasMore"):
        add_directory(
            "Weitere laden...",
            {
                "mode": "module",
                "canonical": canonical,
                "module_id": module_id,
                "offset": data.get("nextOffset"),
                "label": params.get("label") or data.get("moduleTitle") or "",
            },
        )
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.endOfDirectory(HANDLE, succeeded=added > 0 or bool(data.get("hasMore")), cacheToDisc=True)


def list_az(api, params):
    _set_content("tvshows")
    canonical = params.get("canonical") or AZ_CATALOG_CANONICAL
    catalog = api.get_catalog_tabs(canonical)
    for tab in catalog.get("tabs") or []:
        count = _as_int(tab.get("count"))
        if not count:
            continue
        label = "{0} ({1})".format(tab.get("title"), count)
        add_directory(
            label,
            {
                "mode": "catalog",
                "canonical": catalog.get("canonical") or canonical,
                "tab_index": tab.get("index"),
                "tab_title": tab.get("title"),
            },
            None,
            {"title": tab.get("title"), "mediatype": "tvshow"},
        )
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)


def list_catalog_items(api, params):
    _set_content("tvshows")
    canonical = params.get("canonical") or AZ_CATALOG_CANONICAL
    data = api.get_catalog_items(
        params.get("tab_index"),
        canonical=canonical,
        end_cursor=params.get("cursor"),
    )
    added = 0
    for document in data.get("items") or []:
        if add_document(document):
            added += 1
    if data.get("hasMore"):
        add_directory(
            "Weitere laden...",
            {
                "mode": "catalog",
                "canonical": canonical,
                "tab_index": params.get("tab_index"),
                "tab_title": params.get("tab_title") or "",
                "cursor": data.get("endCursor"),
            },
        )
    xbmcplugin.endOfDirectory(HANDLE, succeeded=added > 0 or bool(data.get("hasMore")), cacheToDisc=True)


def list_meta_items(api, params):
    _set_content("tvshows")
    data = api.get_meta_collection_items(params.get("canonical"))
    added = 0
    for document in data.get("items") or []:
        if add_document(document):
            added += 1
    xbmcplugin.endOfDirectory(HANDLE, succeeded=added > 0, cacheToDisc=True)


def list_collection(api, params):
    canonical = params.get("canonical")
    collection = api.get_collection(canonical)
    if not collection:
        raise ZdfError("Sammlung nicht gefunden: {0}".format(canonical))

    if is_movie_collection(collection):
        _set_content("movies")
        if not add_video(collection.get("video") or {}, label=document_title(collection), mediatype="movie"):
            raise ZdfError("Kein abspielbarer Film gefunden: {0}".format(document_title(collection)))
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)
        return

    _set_content("seasons")
    seasons = api.get_seasons(canonical)
    for season in seasons:
        number = season.get("number")
        count = _as_int(season.get("countEpisodes"))
        title = season.get("title") or "Staffel {0}".format(number)
        label = title
        if number and "staffel" not in title.lower() and _as_int(number) < 1900:
            label = "Staffel {0} - {1}".format(number, title)
        if count:
            label = "{0} ({1} Folge{2})".format(label, count, "" if count == 1 else "n")
        add_directory(
            label,
            {
                "mode": "episodes",
                "canonical": canonical,
                "season_id": season.get("id"),
                "season_number": number,
                "series_label": document_title(collection),
                "season_label": title,
            },
            document_image(collection),
            {"title": title, "season": number or 0, "mediatype": "season"},
        )
    xbmcplugin.endOfDirectory(HANDLE, succeeded=bool(seasons), cacheToDisc=True)


def list_episodes(api, params):
    _set_content("episodes")
    episodes = api.get_episodes(
        params.get("canonical"),
        params.get("season_id"),
        season_number=params.get("season_number"),
    )
    added = 0
    for video in episodes:
        if add_video(video):
            added += 1
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_EPISODE)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.endOfDirectory(HANDLE, succeeded=added > 0, cacheToDisc=True)


def play(api, params):
    try:
        stream = api.resolve_ptmd_template(params.get("ptmd"))
        item = xbmcgui.ListItem(label=params.get("title") or "ZDFtivi")
        item.setPath(stream["url"])
        if params.get("thumb"):
            item.setArt(_art(params["thumb"]))
        if stream.get("mime_type"):
            item.setMimeType(stream["mime_type"])
        if stream.get("is_hls"):
            item.setProperty("inputstream", "inputstream.adaptive")
            item.setProperty("inputstreamaddon", "inputstream.adaptive")
            item.setProperty("inputstream.adaptive.manifest_type", "hls")
        if stream.get("subtitles"):
            item.setSubtitles(stream["subtitles"])
        xbmcplugin.setResolvedUrl(HANDLE, True, item)
    except Exception as exc:
        _notify_error(str(exc))
        xbmc.log(traceback.format_exc(), xbmc.LOGERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def run():
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
    api = ZdfSession()
    try:
        mode = params.get("mode")
        if mode == "curated":
            list_curated(api, params)
        elif mode == "module":
            list_module_items(api, params)
        elif mode == "az":
            list_az(api, params)
        elif mode == "catalog":
            list_catalog_items(api, params)
        elif mode == "meta":
            list_meta_items(api, params)
        elif mode == "collection":
            list_collection(api, params)
        elif mode == "episodes":
            list_episodes(api, params)
        elif mode == "play":
            play(api, params)
        else:
            list_root(api)
    except ZdfError as exc:
        _notify_error(str(exc))
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    except Exception as exc:
        _notify_error(str(exc))
        xbmc.log(traceback.format_exc(), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
