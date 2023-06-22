'''Data used throughout the application'''

import os
import pickle

from enum import Enum

# Discord-related
sm_client = None

# Guild properties
class AutoplayMode(Enum):
    RANDOM = 0,
    SIMILAR = 1

_default_properties: dict[str, any] = {
    "queue": [],
    "autoplay": False,
    "autoplay-mode": AutoplayMode.RANDOM
}

class GuildProperties():
    ''' Class that holds all Submeister properties specific to a guild '''
    def __init__(self) -> None:
        self._properties = _default_properties
        pass

    @property
    def queue(self) -> list:
        return self._properties["queue"]
    
    @queue.setter
    def queue(self, value: list) -> None:
        self._properties["queue"] = value

    @property
    def autoplay(self) -> bool:
        return self._properties["autoplay"]
    
    @autoplay.setter
    def autoplay(self, value: bool) -> None:
        self._properties["autoplay"] = value

    @property
    def autoplay_mode(self) -> AutoplayMode:
        return self._properties["autoplay-mode"]
    
    @autoplay_mode.setter
    def autoplay_mode(self, value: AutoplayMode) -> None:
        self._properties["autoplay-mode"] = value

_guild_instances: dict[int, GuildProperties] = {} # Dictionary to store properties for each guild instance

def guild_properties(guild_id: int) -> GuildProperties:
    ''' Returns the properties for the chosen guild '''

    # Return property if guild exists
    if guild_id in _guild_instances:
        return _guild_instances[guild_id]
    
    # Create & store new properties object if guild does not already exist
    properties = GuildProperties()
    _guild_instances[guild_id] = properties
    return _guild_instances[guild_id]

def save_guild_properties_to_disk() -> None:
    ''' Saves guild properties to disk '''

    with open('guild_properties.pickle', 'wb') as file:
        pickle.dump(_guild_instances, file, protocol=pickle.HIGHEST_PROTOCOL)

def load_guild_properties_from_disk() -> None:
    ''' Loads guild properties that have been saved to disk '''

    if not os.path.exists('guild_properties.pickle'):
        return
    
    with open('guild_properties.pickle', 'rb') as file:
        _guild_instances.update(pickle.load(file))
