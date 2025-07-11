''' Data used throughout the application '''

''' 
    TODO: Save one properties pickle file per-guild, instead of saving all in one file at once
'''

import logging
import os
import pickle

from enum import Enum
from typing import Final
from typing import Any

from subsonic.song import Song
from player import Player

logger = logging.getLogger(__name__)

# Guild data
_default_data: dict[str, Any] = {
    "player": None,
}

class GuildData():
    ''' Class that holds all Submeister data specific to a guild (not saved to disk) '''

    def __init__(self, guild_id: int) -> None:
        self._data = _default_data
        self._guild_id = guild_id
        self.player = Player(guild_id)
        if self.player.queue is None:
            self.player.queue = []


    @property
    def player(self) -> Player:
        '''The guild's player.'''
        return self._data["player"]
    

    @player.setter
    def player(self, value: Player) -> None:
        self._data["player"] = value


    @property
    def guild_id(self) -> int:
        ''' The guild ID this data belongs to. '''
        return self.guild_id



_guild_data_instances: dict[int, GuildData] = {} # Dictionary to store temporary data for each guild instance


def guild_data(guild_id: int) -> GuildData:
    ''' Returns the temporary data for the chosen guild '''

    # Return property if guild exists
    if guild_id in _guild_data_instances:
        return _guild_data_instances[guild_id]

    # Create & store new data object if guild does not already exist
    data = GuildData(guild_id)

    # Load queue from disk if it exists
    if guild_properties(guild_id).queue is not None:
        data.player.queue = guild_properties(guild_id).queue

    _guild_data_instances[guild_id] = data
    return _guild_data_instances[guild_id]



# Guild properties
class AutoplayMode(Enum):
    ''' Enum representing an autoplay mode '''
    NONE: Final[int] = 0
    RANDOM: Final[int] = 1
    SIMILAR: Final[int] = 2
    PLAYLIST: Final[int] = 3


_default_properties: dict[str, Any] = {
    "queue": None,
    "autoplay-mode": AutoplayMode.NONE,
    "autoplay-source-id": ""
}



class GuildProperties():
    ''' Class that holds all Submeister properties specific to a guild (saved to disk) '''

    def __init__(self) -> None:
        self._properties = _default_properties


    @property
    def autoplay_mode(self) -> AutoplayMode:
        '''The autoplay mode in use by this guild'''
        return self._properties["autoplay-mode"]


    @autoplay_mode.setter
    def autoplay_mode(self, value: AutoplayMode) -> None:
        self._properties["autoplay-mode"] = value


    @property
    def autoplay_source_id(self) -> str:
        ''' The id (album or playlist) the autoplay source can be obtained from. '''
        return self._properties["autoplay-source-id"]


    @autoplay_source_id.setter
    def autoplay_source_id(self, value: str) -> None:
        self._properties["autoplay-source-id"] = value


    @property
    def queue(self) -> list[Song]:
        '''  The queue last stored to disk for this guild. '''
        return self._properties["queue"]


    @queue.setter
    def queue(self, value: list[Song]) -> None:
        self._properties["queue"] = value



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
    ''' Saves guild properties to disk. '''

    # Copy the queues from each guild data into each guild property
    for guild_id, properties in _guild_property_instances.items():
        properties.queue = guild_data(guild_id).player.queue

    with open("guild_properties.pickle", "wb") as file:
        try:
            pickle.dump(_guild_property_instances, file, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info("Guild properties saved successfully.")
        except pickle.PicklingError as err:
            logger.error("Failed to save guild properties to disk.", exc_info=err)


def load_guild_properties_from_disk() -> None:
    ''' Loads guild properties that have been saved to disk. '''

    if not os.path.exists("guild_properties.pickle"):
        logger.info("Unable to load guild properties from disk. File was not found.")
        return

    with open("guild_properties.pickle", "rb") as file:
        try:
            loaded: dict[int, GuildProperties] = pickle.load(file)
            
            # Ensure only currently-valid keys are updated, and otherwise set defaults
            for guild_id, props in loaded.items():
                
                _guild_property_instances[guild_id] = GuildProperties()

                for key in _default_properties:
                    if key in props._properties:
                        _guild_property_instances[guild_id]._properties[key] = props._properties[key]

            logger.info("Guild properties loaded successfully.")
        except pickle.UnpicklingError as err:
            logger.error("Failed to load guild properties from disk.", exc_info=err)
