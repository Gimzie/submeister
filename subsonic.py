''' For interfacing with the Subsonic API '''

import logging
import os
import requests

from pathlib import Path

from util import env

logger = logging.getLogger(__name__)


# Parameters for the Subsonic API
SUBSONIC_REQUEST_PARAMS = {
        "u": env.SUBSONIC_USER,
        "p": env.SUBSONIC_PASSWORD,
        "v": "1.15.0",
        "c": "submeister",
        "f": "json"
    }


class Song():
    ''' Object representing a song returned from the Subsonic API '''
    def __init__(self, json_object: dict) -> None:
        #! Other properties exist in the initial json response but are currently unused by Submeister and thus aren't supported here
        self._id: str = json_object["id"] if "id" in json_object else ""
        self._title: str = json_object["title"] if "title" in json_object else "Unknown Track"
        self._album: str = json_object["album"] if "album" in json_object else "Unknown Album"
        self._artist: str = json_object["artist"] if "artist" in json_object else "Unknown Artist"
        self._cover_id: str = json_object["coverArt"] if "coverArt" in json_object else ""
        self._duration: int = json_object["duration"] if "duration" in json_object else 0

    @property
    def song_id(self) -> str:
        ''' The song's id '''
        return self._id

    @property
    def title(self) -> str:
        ''' The song's title '''
        return self._title

    @property
    def album(self) -> str:
        ''' The album containing the song '''
        return self._album

    @property
    def artist(self) -> str:
        ''' The song's artist '''
        return self._artist

    @property
    def cover_id(self) -> str:
        ''' The id of the cover art used by the song '''
        return self._cover_id

    @property
    def duration(self) -> int:
        ''' The total duration of the song '''
        return self._duration

    @property
    def duration_printable(self) -> str:
        ''' The total duration of the song as a human readable string in the format `mm:ss` '''
        return f"{(self._duration // 60):02d}:{(self._duration % 60):02d}"


def check_subsonic_error(response: requests.Response) -> bool:
    ''' Checks and logs error codes returned by the subsonic API. Returns True if an error is present. '''

    try:
        json = response.json()
    except requests.exceptions.JSONDecodeError:
        return False

    try:
        err_code: int = json["subsonic-response"]["error"]["code"]
    except KeyError:
        return False

    match err_code:
        case 0:
            err_msg = "Generic Error."
        case 10:
            err_msg = "Required Parameter Missing."
        case 20:
            err_msg = "Incompatible Subsonic REST protocol version. Client must upgrade."
        case 30:
            err_msg = "Incompatible Subsonic REST protocol version. Server must upgrade."
        case 40:
            err_msg = "Wrong username or password."
        case 41:
            err_msg = "Token authentication not supported for LDAP users."
        case 50:
            err_msg = "User is not authorized for the given operation."
        case 60:
            err_msg = "The trial period for the Subsonic server is over."
        case 70:
            err_msg = "The requested data was not found."
        case _:
            err_msg = "Unknown Error Code."

    logger.warning("Subsonic API request responded with error code %s: %s", err_code, err_msg)
    return True

def search(query: str, *, artist_count: int=20, artist_offset: int=0, album_count: int=20, album_offset: int=0, song_count: int=20, song_offset: int=0) -> list[Song]:
    ''' Send a search request to the subsonic API '''

    # Sanitize special characters in the user's query
    #parsed_query = urlParse.quote(query, safe='')

    search_params = {
        "query": query, #todo: fix parsed query
        "artistCount": str(artist_count),
        "artistOffset": str(artist_offset),
        "albumCount": str(album_count),
        "albumOffset": str(album_offset),
        "songCount": str(song_count),
        "songOffset": str(song_offset)
    }

    params = SUBSONIC_REQUEST_PARAMS | search_params

    response = requests.get(f"{env.SUBSONIC_SERVER}/rest/search3.view", params=params, timeout=20)
    search_data = response.json()

    results: list[Song] = []

    try:
        for item in search_data["subsonic-response"]["searchResult3"]["song"]:
            results.append(Song(item))
    except KeyError:
        return []

    return results

def get_album_art_file(cover_id: str, size: int=300) -> str:
    ''' Request album art from the subsonic API '''
    target_path = f"cache/{cover_id}.jpg"

    # Check if the cover art is already cached (TODO: Check for last-modified date?)
    if os.path.exists(target_path):
        return target_path

    cover_params = {
        "id": cover_id,
        "size": str(size)
    }

    params = SUBSONIC_REQUEST_PARAMS | cover_params
    response = requests.get(f"{env.SUBSONIC_SERVER}/rest/getCoverArt", params=params, timeout=20)

    # Grab cover art for the current song
    if check_subsonic_error(response):
        return "resources/cover_not_found.jpg"

    file = Path(target_path)
    file.parent.mkdir(exist_ok=True, parents=True)
    file.write_bytes(response.content)
    return target_path

def get_random_songs(size: int=None, genre: str=None, from_year: int=None, to_year: int=None, music_folder_id: str=None) -> list[Song]:
    ''' Request random songs from the subsonic API '''

    search_params: dict[str, any] = {}

    # Handle Optional params
    if size is not None:
        search_params["size"] = size

    if genre is not None:
        search_params["genre"] = genre

    if from_year is not None:
        search_params["fromYear"] = from_year

    if to_year is not None:
        search_params["toYear"] = to_year

    if music_folder_id is not None:
        search_params["musicFolderId"] = music_folder_id


    params = SUBSONIC_REQUEST_PARAMS | search_params
    response = requests.get(f"{env.SUBSONIC_SERVER}/rest/getRandomSongs.view", params=params, timeout=20)
    search_data = response.json()

    results: list[Song] = []
    for item in search_data["subsonic-response"]["randomSongs"]["song"]:
        results.append(Song(item))

    return results

def get_similar_songs(song_id: str, count: int=50) -> list[Song]:
    ''' Request similar songs from the subsonic API '''

    search_params = {
        "id": song_id,
        "count": count
    }

    params = SUBSONIC_REQUEST_PARAMS | search_params
    response = requests.get(f"{env.SUBSONIC_SERVER}/rest/getSimilarSongs2.view", params=params, timeout=20)
    search_data = response.json()

    results: list[Song] = []
    for item in search_data["subsonic-response"]["similarSongs2"]["song"]:
        results.append(Song(item))

    return results

def stream(stream_id: str):
    ''' Send a stream request to the subsonic API '''

    stream_params = {
        "id": stream_id
        # TODO: handle other params
    }

    params = SUBSONIC_REQUEST_PARAMS | stream_params
    response = requests.get(f"{env.SUBSONIC_SERVER}/rest/stream.view", params=params, timeout=20, stream=True)

    return response.url
