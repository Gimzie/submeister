import requests
import os

from dotenv import load_dotenv
from urllib import parse as urlParse


load_dotenv(os.path.relpath("data.env"))

# Get Subsonic server details
SUB_SERVER = os.getenv("SUBSONIC_SERVER")
SUB_USER = os.getenv("SUBSONIC_USER")
SUB_PASSWORD = os.getenv("SUBSONIC_PASSWORD")

# Parameters for the Subsonic API
SUBSONIC_REQUEST_PARAMS = {
        "u": SUB_USER,
        "p": SUB_PASSWORD,
        "v": "1.15.0",
        "c": "submeister",
        "f": "json"
    }


def search(query: str, *, artist_count: int=20, artist_offset: int=0, album_count: int=20, album_offset: int=0, song_count: int=20, song_offset: int=0) -> dict:
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

    response = requests.get(f"{SUB_SERVER}/rest/search3.view", params=params)
    search_data = response.json()

    songs = search_data["subsonic-response"]["searchResult3"]["song"]

    return songs


def stream(id: int, *, max_bitrate: int=None, format: str=None, estimate_content_length: bool=False):
    ''' Send a stream request to the subsonic API '''

    # TODO: make more configurable
    stream_params = {
        "id": id
        # "maxBitRate": max_bitrate,
        # "format": format,
        # "estimateContentLength": estimate_content_length
    }

    response = requests.get(f"{SUB_SERVER}/rest/stream.view", params=SUBSONIC_REQUEST_PARAMS|stream_params, stream=True)

    return response.url
