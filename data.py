'''Data used throughout the application'''

import logging
import os
import pickle

from enum import Enum
from typing import Final

from subsonic import Song

logger = logging.getLogger(__name__)

# Guild data
_default_data: dict[str, any] = {
    'current-song': None,
    "current-position": 0
}

class GuildData():
    '''Class that holds all Submeister data specific to a guild (not saved to disk)'''
    def __init__(self) -> None:
        self._data = _default_data

    @property
    def current_song(self) -> Song:
        '''The current song'''
        return self._data["current-song"]

    @current_song.setter
    def current_song(self, song: Song) -> None:
        self._data["current-song"] = song

    @property
    def current_position(self) -> int:
        ''' The current position for the current song, in seconds. '''
        return self._data["current-position"]

    @current_position.setter
    def current_position(self, position: int) -> None:
        ''' Set the current position for the current song, in seconds. '''
        self._data["current-position"] = position

_guild_data_instances: dict[int, GuildData] = {} # Dictionary to store temporary data for each guild instance

def guild_data(guild_id: int) -> GuildData:
    ''' Returns the temporary data for the chosen guild '''

    # Return property if guild exists
    if guild_id in _guild_data_instances:
        return _guild_data_instances[guild_id]

    # Create & store new data object if guild does not already exist
    data = GuildData()
    _guild_data_instances[guild_id] = data
    return _guild_data_instances[guild_id]


# Guild properties
class AutoplayMode(Enum):
    '''Enum representing an autoplay mode'''
    NONE : Final[int] = 0
    RANDOM : Final[int] = 1
    SIMILAR : Final[int] = 2

_default_properties: dict[str, any] = {
    "queue": [],
    "autoplay-mode": AutoplayMode.NONE
}

class GuildProperties():
    '''Class that holds all Submeister properties specific to a guild (saved to disk)'''

    def __init__(self) -> None:
        self._properties = _default_properties

    @property
    def queue(self) -> list[Song]:
        '''The audio queue for this guild'''

        return self._properties["queue"]

    @queue.setter
    def queue(self, value: list) -> None:
        self._properties["queue"] = value

    @property
    def autoplay_mode(self) -> AutoplayMode:
        '''The autoplay mode in use by this guild'''

        return self._properties["autoplay-mode"]

    @autoplay_mode.setter
    def autoplay_mode(self, value: AutoplayMode) -> None:
        self._properties["autoplay-mode"] = value
        save_guild_properties_to_disk()

_guild_property_instances: dict[int, GuildProperties] = {} # Dictionary to store properties for each guild instance

def guild_properties(guild_id: int) -> GuildProperties:
    ''' Returns the properties for the chosen guild '''

    # Return property if guild exists
    if guild_id in _guild_property_instances:
        return _guild_property_instances[guild_id]

    # Create & store new properties object if guild does not already exist
    properties = GuildProperties()
    _guild_property_instances[guild_id] = properties
    return _guild_property_instances[guild_id]

def save_guild_properties_to_disk() -> None:
    ''' Saves guild properties to disk '''

    with open('guild_properties.pickle', 'wb') as file:
        try:
            pickle.dump(_guild_property_instances, file, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info("Guild properties saved successfully.")
        except pickle.PicklingError as err:
            logger.error("Failed to save guild properties to disk.", exc_info=err)

def load_guild_properties_from_disk() -> None:
    ''' Loads guild properties that have been saved to disk '''

    if not os.path.exists('guild_properties.pickle'):
        logger.info("Unable to load guild properties from disk. File was not found.")
        return

    with open('guild_properties.pickle', 'rb') as file:
        try:
            _guild_property_instances.update(pickle.load(file))
            logger.info("Guild properties loaded successfully.")
        except pickle.UnpicklingError as err:
            logger.error("Failed to load guild properties from disk.", exc_info=err)
