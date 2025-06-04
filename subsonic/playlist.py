from subsonic.song import Song

class Playlist():
    ''' Object representing a playlist returned from the Subsonic API '''
    def __init__(self, json_object: dict) -> None:
        #! Other properties exist in the initial json response but are currently unused by Submeister and thus aren't supported here
        self._id: str = json_object["id"] if "id" in json_object else ""
        self._name: str = json_object["name"] if "name" in json_object else "Unknown Name"
        self._song_count: int = json_object["songCount"] if "songCount" in json_object else 0
        self._duration: int = json_object["duration"] if "duration" in json_object else 0
        self._username: str = "Unknown"
        self._songs: list[Song] = []


    @property
    def playlist_id(self) -> str:
        ''' The playlist's id '''
        return self._id
    

    @property
    def name(self) -> str:
        ''' The playlist's name '''
        return self._name
    

    @property
    def song_count(self) -> int:
        ''' The number of songs in this playlist '''
        return self._song_count
    

    @property
    def duration(self) -> int:
        ''' The playlist's total duration '''
        return self._duration
    

    @property
    def duration_printable(self) -> str:
        ''' The total duration of the playlist as a human readable string in the format `dd::hh::mm:ss`. '''

        days = self._duration // 86400
        hours = (self._duration % 86400) // 3600
        minutes = (self._duration % 3600) // 60
        seconds = self._duration % 60

        output = ""

        if days > 0: output += f"{days:2d}:"
        if hours > 0: output += f"{hours:02d}:"
        output += f"{minutes:02d}:{seconds:02d}"

        return output
    

    @property
    def username(self) -> str:
        ''' The user who added/played this playlist '''
        return self._username
    

    @username.setter
    def username(self, name: str) -> None:
        self._username = name


    @property
    def songs(self) -> list[Song]:
        ''' The songs in this playlist '''
        return self._songs
    

    @songs.setter
    def songs(self, songs: list[Song]) -> None:
        self._songs = songs
