# -*- coding: utf-8 -*-
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request


ROOT_URL = "https://www.zdf.de/kinder/loewenzahn-156"
ROOT_COLLECTION_ID = "12390175-a4e3-4eca-960e-3a66e921831a"
GRAPHQL_URL = "https://api.zdf.de/graphql"
API_BASE_URL = "https://api.zdf.de"
AB_GROUP_URL = "https://abgroup.zdf.de/PROD/"
PLAYER_CONFIG_URL = "https://ngp.zdf.de/configs/zdf/zdfmt25/configuration.json"

CONTENT_APP_ID = "ffw-mt-web-722181b4"
PERSONALIZATION_APP_ID = "zdf-web-722181b4"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)

EXPECTED_SERIES = (
    {
        "key": "fritz",
        "label": "Fritz Fuchs",
        "fallback_title": "Löwenzahn mit Fritz Fuchs",
        "canonical": "loewenzahn-mit-fritz-fuchs-100",
    },
    {
        "key": "peter",
        "label": "Peter Lustig",
        "fallback_title": "Löwenzahn mit Peter Lustig",
        "canonical": "loewenzahn-mit-peter-lustig-104",
    },
    {
        "key": "keks",
        "label": "Löwenzähnchen mit Keks",
        "fallback_title": "Löwenzähnchen",
        "canonical": "loewenzaehnchen-122",
    },
)


COLLECTION_QUERY = """
query getMetaCollectionContent($collectionId: String!, $input: MetaCollectionContentInput!) {
  metaCollectionContent(collectionId: $collectionId, input: $input) {
    pageInfo {
      hasNextPage
      endCursor
    }
    smartCollections {
      __typename
      ... on ISmartCollection {
        id
        title
        canonical
        collectionType
        teaser {
          title
          imageWithoutLogo {
            layouts {
              dim384X216
              dim768X432
              original
            }
          }
        }
      }
      ... on ISeriesSmartCollection {
        countSeasons
        countEpisodes
      }
    }
  }
}
"""


SEASONS_QUERY = """
query GetSmartCollectionSeasons($canonical: String!, $seasonFilterBy: SeasonsConnectionFilterByInput) {
  smartCollectionByCanonical(canonical: $canonical) {
    __typename
    id
    title
    canonical
    collectionType
    ... on ISeriesSmartCollection {
      countSeasons
      countEpisodes
      seasons(first: 100, filterBy: $seasonFilterBy) {
        nodes {
          id
          number
          title
          countEpisodes
        }
      }
    }
  }
}
"""


EPISODES_QUERY = """
query GetSeasonEpisodes(
  $canonical: String!,
  $seasonFilterBy: SeasonsConnectionFilterByInput,
  $episodesPageSize: Int,
  $episodesAfter: Cursor,
  $episodesSortBy: [VideosConnectionSortByInput!],
  $episodesFilterBy: VideosConnectionFilterByInput
) {
  smartCollectionByCanonical(canonical: $canonical) {
    __typename
    id
    title
    canonical
    ... on ISeriesSmartCollection {
      seasons(first: 1, filterBy: $seasonFilterBy) {
        nodes {
          id
          number
          title
          countEpisodes
          episodes(
            first: $episodesPageSize,
            after: $episodesAfter,
            sortBy: $episodesSortBy,
            filterBy: $episodesFilterBy
          ) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              __typename
              id
              title
              canonical
              editorialDate
              productionYear
              teaser {
                title
                description
                imageWithoutLogo {
                  layouts {
                    dim384X216
                    dim768X432
                    original
                  }
                }
              }
              episodeInfo {
                seasonNumber
                episodeNumber
              }
              availability {
                fskBlocked
                vod {
                  visibleTo
                  endDate
                  fsk
                }
              }
              currentMedia {
                nodes {
                  __typename
                  ptmdTemplate
                  ... on VodMedia {
                    vodMediaType
                    duration
                    downloadAllowed
                    geoLocation
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


class ZdfError(Exception):
    """Raised when the ZDF API cannot be queried or interpreted."""


class ZdfHttpError(ZdfError):
    def __init__(self, status, url, body):
        self.status = status
        self.url = url
        self.body = body
        super().__init__("HTTP {0} for {1}: {2}".format(status, url, body[:300]))


def _decode(data):
    return data.decode("utf-8", "replace")


def _request(url, data=None, headers=None, method=None, timeout=20):
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/plain,*/*",
    }
    if headers:
        request_headers.update(headers)
    if data is not None and isinstance(data, str):
        data = data.encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return _decode(response.read())
    except urllib.error.HTTPError as exc:
        body = _decode(exc.read() or b"")
        raise ZdfHttpError(exc.code, url, body)
    except urllib.error.URLError as exc:
        raise ZdfError("Network error for {0}: {1}".format(url, exc))


def _get_json(url, headers=None, timeout=20):
    return json.loads(_request(url, headers=headers, timeout=timeout))


def _strip_html(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _first_layout(entity):
    image = ((entity.get("teaser") or {}).get("imageWithoutLogo") or {})
    layouts = image.get("layouts") or {}
    for key in ("dim768X432", "dim384X216", "original"):
        if layouts.get(key):
            return layouts[key]
    return None


def _as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _sort_seasons(seasons):
    return sorted(seasons, key=lambda item: _as_int(item.get("number")), reverse=True)


def pick_vod_media(video):
    nodes = ((video.get("currentMedia") or {}).get("nodes") or [])
    vods = [
        node for node in nodes
        if node.get("__typename") == "VodMedia" and node.get("ptmdTemplate")
    ]
    for media_type in ("DEFAULT", "MAIN", None):
        for node in vods:
            if node.get("vodMediaType") == media_type:
                return node
    return vods[0] if vods else None


def episode_title(video):
    return (
        ((video.get("teaser") or {}).get("title"))
        or video.get("title")
        or "Unbenannte Folge"
    )


def episode_plot(video):
    return _strip_html((video.get("teaser") or {}).get("description"))


def episode_image(video):
    return _first_layout(video)


def format_episode_label(video):
    info = video.get("episodeInfo") or {}
    season_number = _as_int(info.get("seasonNumber"))
    episode_number = _as_int(info.get("episodeNumber"))
    title = episode_title(video)
    if season_number and episode_number:
        return "S{0:02d}E{1:02d} - {2}".format(season_number, episode_number, title)
    if episode_number:
        return "E{0:02d} - {1}".format(episode_number, title)
    return title


class ZdfSession:
    def __init__(self):
        self._api_token = None
        self._api_token_refresh_at = 0
        self._ab_group = None
        self._player_id = None

    def _extract_api_token(self, html_text):
        patterns = (
            r'"apiAuthToken"\s*:\s*"([^"]+)"',
            r'apiAuthToken\\?"\s*:\s*\\?"([^"\\]+)',
            r'apiAuthToken\\u0022\s*:\s*\\u0022([^"\\]+)',
        )
        for pattern in patterns:
            match = re.search(pattern, html_text)
            if match:
                return match.group(1)
        raise ZdfError("Could not find ZDF API token on {0}".format(ROOT_URL))

    def api_token(self, force_refresh=False):
        now = time.time()
        if not force_refresh and self._api_token and now < self._api_token_refresh_at:
            return self._api_token
        page = _request(ROOT_URL, headers={"Accept": "text/html,*/*"})
        self._api_token = self._extract_api_token(page)
        self._api_token_refresh_at = now + 25 * 60
        return self._api_token

    def ab_group(self):
        if self._ab_group:
            return self._ab_group
        try:
            data = _get_json(AB_GROUP_URL)
            self._ab_group = data.get("group") or data.get("abGroup") or "gruppe-c"
        except Exception:
            self._ab_group = "gruppe-c"
        return self._ab_group

    def player_id(self):
        if self._player_id:
            return self._player_id
        try:
            data = _get_json(PLAYER_CONFIG_URL)
            self._player_id = data.get("ptmdPlayerId") or "ngplayer_2_5"
        except Exception:
            self._player_id = "ngplayer_2_5"
        return self._player_id

    def _api_headers(self, force_token_refresh=False):
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Api-Auth": "Bearer {0}".format(self.api_token(force_token_refresh)),
            "zdf-app-id": CONTENT_APP_ID,
        }

    def graphql(self, query, variables, operation_name):
        payload = json.dumps(
            {
                "operationName": operation_name,
                "query": query,
                "variables": variables,
            },
            separators=(",", ":"),
        )
        for attempt in range(2):
            try:
                response = _request(
                    GRAPHQL_URL,
                    data=payload,
                    headers=self._api_headers(force_token_refresh=attempt > 0),
                    method="POST",
                )
                data = json.loads(response)
                if data.get("errors"):
                    raise ZdfError(json.dumps(data["errors"], ensure_ascii=False))
                return data.get("data") or {}
            except ZdfHttpError as exc:
                if exc.status in (401, 403) and attempt == 0:
                    continue
                raise
        raise ZdfError("ZDF GraphQL request failed")

    def _collection_input(self, first=24, after=None):
        return {
            "appId": PERSONALIZATION_APP_ID,
            "filters": {"onlyChildrenContent": True},
            "pagination": {"first": first, "after": after},
            "user": {
                "abGroup": self.ab_group(),
                "userSegment": "anonymous",
            },
            "tabId": None,
        }

    def get_series(self):
        variables = {
            "collectionId": ROOT_COLLECTION_ID,
            "input": self._collection_input(),
        }
        data = self.graphql(COLLECTION_QUERY, variables, "getMetaCollectionContent")
        nodes = ((data.get("metaCollectionContent") or {}).get("smartCollections") or [])
        by_canonical = {node.get("canonical"): node for node in nodes}

        series = []
        for expected in EXPECTED_SERIES:
            node = by_canonical.get(expected["canonical"]) or {}
            series.append(
                {
                    "key": expected["key"],
                    "label": expected["label"],
                    "title": node.get("title") or expected["fallback_title"],
                    "canonical": expected["canonical"],
                    "id": node.get("id"),
                    "countSeasons": node.get("countSeasons"),
                    "countEpisodes": node.get("countEpisodes"),
                    "image": _first_layout(node),
                }
            )
        return series

    def get_seasons(self, canonical):
        variables = {
            "canonical": canonical,
            "seasonFilterBy": {"availableStreamTypesIn": ["VOD"]},
        }
        data = self.graphql(SEASONS_QUERY, variables, "GetSmartCollectionSeasons")
        collection = data.get("smartCollectionByCanonical") or {}
        seasons = (((collection.get("seasons") or {}).get("nodes")) or [])
        return _sort_seasons(seasons)

    def get_episodes(self, canonical, season_id):
        after = None
        episodes = []
        while True:
            variables = {
                "canonical": canonical,
                "seasonFilterBy": {
                    "idIn": [season_id],
                    "availableStreamTypesIn": ["VOD"],
                },
                "episodesPageSize": 50,
                "episodesAfter": after,
                "episodesSortBy": [
                    {"field": "EPISODE_NUMBER", "direction": "ASC"},
                ],
                "episodesFilterBy": {"availableStreamTypeIn": ["VOD"]},
            }
            data = self.graphql(EPISODES_QUERY, variables, "GetSeasonEpisodes")
            collection = data.get("smartCollectionByCanonical") or {}
            season_nodes = (((collection.get("seasons") or {}).get("nodes")) or [])
            if not season_nodes:
                return episodes
            edge = (season_nodes[0].get("episodes") or {})
            episodes.extend(edge.get("nodes") or [])
            page_info = edge.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                return episodes
            after = page_info.get("endCursor")
            if not after:
                return episodes

    def resolve_ptmd_template(self, ptmd_template):
        if not ptmd_template:
            raise ZdfError("Episode has no playable ZDF PTMD template")

        player_ids = []
        preferred = self.player_id()
        for candidate in (preferred, "ngplayer_2_5", "ngplayer_2_4"):
            if candidate and candidate not in player_ids:
                player_ids.append(candidate)

        last_error = None
        for player_id in player_ids:
            url = ptmd_template.replace("{playerId}", player_id)
            if url.startswith("/"):
                url = API_BASE_URL + url
            try:
                ptmd = _get_json(url, headers=self._api_headers())
                return select_stream(ptmd)
            except ZdfError as exc:
                last_error = exc
        raise last_error or ZdfError("Could not resolve ZDF stream")


def _iter_formats(ptmd):
    for priority_index, priority in enumerate(ptmd.get("priorityList") or []):
        for format_index, fmt in enumerate(priority.get("formitaeten") or []):
            yield priority_index, format_index, fmt
    for format_index, fmt in enumerate(ptmd.get("formitaeten") or []):
        yield 0, format_index, fmt


def _quality_rank(value):
    value = (value or "").lower()
    ranks = {
        "auto": 700,
        "veryhigh": 600,
        "high": 500,
        "med": 400,
        "medium": 400,
        "low": 300,
        "verylow": 200,
    }
    return ranks.get(value, 100)


def _format_text(fmt, track_url):
    try:
        return json.dumps(
            {
                "type": fmt.get("type"),
                "facets": fmt.get("facets"),
                "mimeType": fmt.get("mimeType"),
                "url": track_url,
            },
            sort_keys=True,
        ).lower()
    except Exception:
        return (track_url or "").lower()


def _iter_stream_candidates(ptmd):
    for priority_index, format_index, fmt in _iter_formats(ptmd):
        mime_type = fmt.get("mimeType") or fmt.get("mime")
        for quality_index, quality in enumerate(fmt.get("qualities") or []):
            quality_name = quality.get("quality") or quality.get("name")
            for carrier_name in ("audio", "video"):
                carrier = quality.get(carrier_name) or {}
                for track in carrier.get("tracks") or []:
                    url = track.get("uri") or track.get("url")
                    if not url:
                        continue
                    lower_url = url.lower()
                    lower_mime = (mime_type or "").lower()
                    text = _format_text(fmt, url)
                    is_hls = "mpegurl" in lower_mime or ".m3u8" in lower_url
                    is_mp4 = "mp4" in lower_mime or ".mp4" in lower_url
                    restricted = "restriction_useragent" in text
                    score = (
                        10000
                        - priority_index * 100
                        - format_index * 10
                        - quality_index
                        + _quality_rank(quality_name)
                    )
                    if (track.get("class") or "").lower() == "main":
                        score += 25
                    yield {
                        "url": url,
                        "mime_type": mime_type,
                        "is_hls": is_hls,
                        "is_mp4": is_mp4,
                        "restricted": restricted,
                        "score": score,
                    }


def _subtitle_urls(ptmd):
    webvtt = []
    fallback = []
    for caption in ptmd.get("captions") or []:
        url = caption.get("uri") or caption.get("url")
        if not url:
            continue
        caption_format = (caption.get("format") or "").lower()
        target = webvtt if caption_format == "webvtt" or url.lower().endswith(".vtt") else fallback
        if url not in target:
            target.append(url)
    return webvtt or fallback


def select_stream(ptmd):
    candidates = list(_iter_stream_candidates(ptmd))
    hls = sorted(
        [candidate for candidate in candidates if candidate["is_hls"]],
        key=lambda candidate: candidate["score"],
        reverse=True,
    )
    mp4 = sorted(
        [candidate for candidate in candidates if candidate["is_mp4"] and not candidate["restricted"]],
        key=lambda candidate: candidate["score"],
        reverse=True,
    )
    restricted_mp4 = sorted(
        [candidate for candidate in candidates if candidate["is_mp4"] and candidate["restricted"]],
        key=lambda candidate: candidate["score"],
        reverse=True,
    )
    selected = (hls or mp4 or restricted_mp4 or candidates[:1])
    if not selected:
        raise ZdfError("No playable stream found in ZDF PTMD response")
    stream = selected[0]
    return {
        "url": stream["url"],
        "mime_type": stream["mime_type"],
        "is_hls": stream["is_hls"],
        "subtitles": _subtitle_urls(ptmd),
    }
