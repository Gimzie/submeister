
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
        self._username: str = "Unknown"


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
        ''' The total duration of the song as a human readable string in the format `mm:ss`. '''
        return f"{(self._duration // 60):02d}:{(self._duration % 60):02d}"
    

    @property
    def username(self) -> str:
        ''' The user who added/played this song. '''
        return self._username
    

    @username.setter
    def username(self, name: str) -> None:
        self._username = name
