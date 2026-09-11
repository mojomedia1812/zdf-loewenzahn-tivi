# -*- coding: utf-8 -*-
import sys
import traceback
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

from zdf_api import (
    ZdfError,
    ZdfSession,
    episode_image,
    episode_plot,
    episode_title,
    format_episode_label,
    pick_vod_media,
)


ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo("name")
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]


def build_url(params):
    return BASE_URL + "?" + urllib.parse.urlencode(params)


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


def add_directory(label, params, image_url=None, info=None):
    item = xbmcgui.ListItem(label=label)
    item.setArt(_art(image_url))
    if info:
        item.setInfo("video", info)
    xbmcplugin.addDirectoryItem(HANDLE, build_url(params), item, isFolder=True)


def add_episode(video):
    media = pick_vod_media(video)
    if not media:
        return
    info = video.get("episodeInfo") or {}
    title = episode_title(video)
    item = xbmcgui.ListItem(label=format_episode_label(video))
    item.setProperty("IsPlayable", "true")
    item.setArt(_art(episode_image(video)))
    item.setInfo(
        "video",
        {
            "title": title,
            "plot": episode_plot(video),
            "season": info.get("seasonNumber") or 0,
            "episode": info.get("episodeNumber") or 0,
            "year": video.get("productionYear") or 0,
            "duration": media.get("duration") or 0,
            "mediatype": "episode",
        },
    )
    xbmcplugin.addDirectoryItem(
        HANDLE,
        build_url(
            {
                "mode": "play",
                "ptmd": media.get("ptmdTemplate"),
                "title": title,
                "thumb": episode_image(video) or "",
            }
        ),
        item,
        isFolder=False,
    )


def list_root(api):
    _set_content("tvshows")
    for series in api.get_series():
        suffix = []
        if series.get("countSeasons"):
            suffix.append("{0} Staffeln".format(series["countSeasons"]))
        if series.get("countEpisodes"):
            suffix.append("{0} Folgen".format(series["countEpisodes"]))
        label = series["label"]
        if suffix:
            label = "{0} ({1})".format(label, ", ".join(suffix))
        add_directory(
            label,
            {"mode": "seasons", "canonical": series["canonical"], "label": series["label"]},
            series.get("image"),
            {"title": series["title"], "mediatype": "tvshow"},
        )
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)


def list_seasons(api, params):
    _set_content("seasons")
    canonical = params["canonical"]
    series_label = params.get("label") or "Löwenzahn"
    for season in api.get_seasons(canonical):
        number = season.get("number")
        count = season.get("countEpisodes")
        title = season.get("title") or "Staffel {0}".format(number)
        label = title
        if number and "staffel" not in title.lower():
            label = "Staffel {0} - {1}".format(number, title)
        if count:
            label = "{0} ({1} Folgen)".format(label, count)
        add_directory(
            label,
            {
                "mode": "episodes",
                "canonical": canonical,
                "season_id": season["id"],
                "series_label": series_label,
                "season_label": title,
            },
            None,
            {"title": title, "season": number or 0, "mediatype": "season"},
        )
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)


def list_episodes(api, params):
    _set_content("episodes")
    episodes = api.get_episodes(params["canonical"], params["season_id"])
    for video in episodes:
        add_episode(video)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_EPISODE)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=True)


def play(api, params):
    try:
        stream = api.resolve_ptmd_template(params.get("ptmd"))
        item = xbmcgui.ListItem(label=params.get("title") or "Löwenzahn")
        item.setPath(stream["url"])
        if params.get("thumb"):
            item.setArt(_art(params["thumb"]))
        if stream.get("mime_type"):
            item.setMimeType(stream["mime_type"])
        if stream.get("is_hls"):
            item.setProperty("inputstream", "inputstream.adaptive")
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
        if mode == "seasons":
            list_seasons(api, params)
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
