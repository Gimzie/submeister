''' A player object that handles playback and data for its respective guild '''

import asyncio
import discord
import logging
import random
import time

import data
import ui
import util.discord

from typing import cast
from subsonic.song import Song
from subsonic.playlist import Playlist
import subsonic.backend as backend

logger = logging.getLogger(__name__)

# Default player data
_default_data: dict[str, any] = {
    "guild-id": 0,
    "current-song": None,
    "last-elapsed": 0,
    "last-start-time": 0,
    "paused": False,
    "now-playing-message": None,
    "now-playing-update-task": None,
    "now-playing-channel": None,
    "now-playing-last-song": None,
    "queue": [],
    "autoplay-source": None
}

class Player():
    ''' Class that represents an audio player '''

    def __init__(self, guild_id: int) -> None:
        self._data = _default_data
        self._data["guild-id"] = guild_id


    @property
    def guild_id(self) -> int:
        ''' The guild ID for this player. '''
        return self._data["guild-id"]


    @property
    def current_song(self) -> Song:
        ''' The current song. '''
        return self._data["current-song"]


    @current_song.setter
    def current_song(self, song: Song) -> None:
        self._data["current-song"] = song


    @property
    def last_elapsed(self) -> int:
        ''' The time elapsed prior to pausing the player, in seconds. '''
        return self._data["last-elapsed"]
    

    @last_elapsed.setter
    def last_elapsed(self, elapsed: int) -> None:
        self._data["last-elapsed"] = int(elapsed)


    @property
    def last_start_time(self) -> int:
        ''' The last time the player was started, in seconds. '''
        return self._data["last-start-time"]
    
    
    @last_start_time.setter
    def last_start_time(self, time: int) -> None:
        self._data["last-start-time"] = int(time)


    @property
    def paused(self) -> bool:
        ''' Whether the player is paused. '''
        return self._data["paused"]
    

    @paused.setter
    def paused(self, paused: bool) -> None:
        self._data["paused"] = paused


    @property
    def now_playing_message(self) -> discord.Message:
        ''' The last sent now-playing message. '''
        return self._data["now-playing-message"]
    

    @now_playing_message.setter
    def now_playing_message(self, message: discord.Message) ->  None:
        self._data["now-playing-message"] =  message


    @property
    def elapsed(self) -> int:
        ''' The elapsed time for the current song, in seconds. '''
        if self.paused:
            return self.last_elapsed
        else:
            return int(time.time()) - self.last_start_time + self.last_elapsed


    @property
    def elapsed_printable(self) -> str:
        ''' The elapsed time for the current song as a human readable string in the format `mm:ss`. '''
        return f"{(self.elapsed // 60):02d}:{(self.elapsed % 60):02d}"


    @property
    def queue(self) -> list[Song]:
        ''' The current audio queue. '''
        return self._data["queue"]


    @queue.setter
    def queue(self, value: list[Song]) -> None:
        self._data["queue"] = value


    @property
    def now_playing_update_task(self) -> asyncio.Task:
        ''' An update task that updates the now-playing message on an interval. '''
        return self._data["now-playing-update-task"]
    

    @now_playing_update_task.setter
    def now_playing_update_task(self, task: asyncio.Task) -> None:
        self._data["now-playing-update-task"] = task


    @property
    def now_playing_channel(self) -> discord.TextChannel:
        ''' The last channel the now-playing message was sent in. '''
        return self._data["now-playing-channel"]
    

    @now_playing_channel.setter
    def now_playing_channel(self, channel: discord.TextChannel) -> None:
        self._data["now-playing-channel"] = channel


    @property
    def now_playing_last_song(self) -> Song:
        ''' The last song that received an update on the now-playing view. '''
        return self._data["now-playing-last-song"]
    

    @now_playing_last_song.setter
    def now_playing_last_song(self, song: Song) -> None:
        self._data["now-playing-last-song"] = song


    @property
    def autoplay_source(self) -> list[Song]:
        ''' The current autoplay source. '''
        return self._data["autoplay-source"]


    @autoplay_source.setter
    def autoplay_source(self, value: any) -> None:
        self._data["autoplay-source"] = value



    async def stream_track(self, interaction: discord.Interaction, song: Song, voice_client: discord.VoiceClient) -> None:
        ''' Streams a track from the Subsonic server to a connected voice channel, and updates guild data accordingly '''

        # Make sure the voice client is available
        if voice_client is None:
            await ui.ErrMsg.bot_not_in_voice_channel(interaction)
            return

        # Make sure the bot isn't already playing music
        if voice_client.is_playing():
            await ui.ErrMsg.already_playing(interaction)
            return

        # Get the stream from the Subsonic server, using the provided song's ID
        ffmpeg_options = {"before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                           "options": "-filter:a loudnorm=I=-14:LRA=11:TP=-1.5"}
        audio_src = discord.FFmpegOpusAudio(backend.stream(song.song_id), **ffmpeg_options)
        # audio_src.read()

        # Update the currently playing song's data
        self.current_song = song
        self.last_start_time = int(time.time())
        self.last_elapsed = 0
        self.paused = False

        # Set up a callback to set up the next track after a song finishes playing
        loop = asyncio.get_event_loop()

        def playback_finished(error: Exception):
            if error is not None:
                logger.error("Exception occurred during playback: %s", error)

            # Don't remove anything else from the queue if we're not connected to a voice channel
            if not voice_client.is_connected():
                return

            asyncio.run_coroutine_threadsafe(self.handle_autoplay(interaction, self.current_song.song_id), loop)
            asyncio.run_coroutine_threadsafe(self.play_audio_queue(interaction, voice_client), loop)

            # If the now-playing message has been "buried" in chat, re-send it
            if (self.now_playing_message is not None
                    and asyncio.run_coroutine_threadsafe(util.discord.visually_has_n_messages_after(24, self.now_playing_message), loop).result()):
                asyncio.run_coroutine_threadsafe(self.update_now_playing(interaction, force_create=True), loop)
                return

            # Otherwise, just update as usual
            asyncio.run_coroutine_threadsafe(self.update_now_playing(), loop)


        # Begin playing the song and let the user know it's being played
        try:
            voice_client.play(audio_src, after=playback_finished)
        except (discord.ClientException):
            pass


    async def handle_autoplay(self, interaction: discord.Interaction, prev_song_id: str=None):
        ''' Handles populating the queue when autoplay is enabled '''

        player = data.guild_data(interaction.guild_id).player
        autoplay_mode = data.guild_properties(interaction.guild_id).autoplay_mode
        source_id = data.guild_properties(interaction.guild_id).autoplay_source_id
        queue = player.queue

        # If queue is not empty or autoplay is disabled, don't handle autoplay
        if queue != [] or autoplay_mode is data.AutoplayMode.NONE:
            return

        # If there was no previous song provided for the similar mode, we default back to selecting a random song
        if autoplay_mode is data.AutoplayMode.SIMILAR and prev_song_id is None:
            autoplay_mode = data.AutoplayMode.RANDOM

        songs = []

        match autoplay_mode:
            case data.AutoplayMode.RANDOM:
                songs = backend.get_random_songs(size=1)
                songs[0].username = "Autoplay (Random)"
            case data.AutoplayMode.SIMILAR:
                songs = backend.get_similar_songs(song_id=prev_song_id, count=1)
                songs[0].username = "Autoplay (Similar)"
            case data.AutoplayMode.PLAYLIST:

                # If the autoplay playlist source has been exhausted, fill it again
                if player.autoplay_source is None or cast(Playlist, player.autoplay_source).songs == []:
                    player.autoplay_source = backend.get_playlist(source_id)

                # Remove a random song from the playlist source and queue it up
                autoplay_source = cast(Playlist, player.autoplay_source)
                songs.append(autoplay_source.songs.pop(random.randrange(len(autoplay_source.songs))))
                songs[0].username = f"Autoplay ({autoplay_source.name})"


        # If there's no match, throw an error
        if len(songs) == 0:
            await ui.ErrMsg.msg(interaction, "Failed to obtain a song for autoplay.")
            return
        
        self.queue.append(songs[0])

        # Fetch the cover art in advance
        backend.get_album_art_file(songs[0].cover_id, interaction.guild_id)


    async def play_audio_queue(self, interaction: discord.Interaction, voice_client: discord.VoiceClient) -> None:
        ''' Plays the audio queue '''

        # Check if the bot is connected to a voice channel; it's the caller's responsibility to open a voice channel
        if voice_client is None:
            await ui.ErrMsg.bot_not_in_voice_channel(interaction)
            return
        
        # Check if the bot is already playing something
        if voice_client.is_playing():
            return

        await self.handle_autoplay(interaction)

        # Check if the queue contains songs
        if self.queue != []:

            # Pop the first item from the queue and begin streaming it
            song = self.queue.pop(0)
            self.current_song = song

            await self.stream_track(interaction, song, voice_client)

            # Update the now-playing message if necessary
            if (self.now_playing_message is None):
                await self.update_now_playing(interaction, force_create=True)

            return

        # If the queue is empty, playback has ended; we should let the user know
        await ui.SysMsg.playback_ended(interaction)

        # Also update the current player information
        self.current_song = None


    async def skip_track(self, voice_client: discord.VoiceClient) -> None:
        ''' Skip the current track. '''

        # Stop the current song
        voice_client.stop()


    async def disconnect(self, interaction: discord.Interaction, voice_client: discord.VoiceClient) -> None:
        ''' Disconnects from the voice channel. '''

        if voice_client is None:
            await ui.ErrMsg.bot_not_in_voice_channel(interaction)
            return

        if interaction is not None:
            await ui.SysMsg.disconnected(interaction)

        await voice_client.disconnect()

        # Clean up misc. state
        self.current_song = None
        self.paused = False

        # Clean up the now-playing update coroutine
        if (self.now_playing_update_task is not None):
            self.now_playing_update_task.cancel()
            self.now_playing_update_task = None
            await self.delete_now_playing()


    async def update_now_playing(self, interaction: discord.Interaction=None, force_create=False) -> None:
        ''' Updates an existing now-playing message, or creates a new one.\n
            Forcing the creation of a message requires at least one valid interaction (ever)
            in order to determine which channel the now-playing view should be sent in.
        '''

        if (self.now_playing_message is None and self.now_playing_channel is None and interaction is None):
            logger.error("There is no message to update, and there is not enough context to create one.")
            return
        
        # Update the now-playing channel using the interaction, if one is provided
        if interaction is not None:
            self.now_playing_channel = interaction.channel

        # If there is no song currently playing, let the user know
        if self.current_song is None:
            if interaction is not None:
                await ui.SysMsg.no_track_playing(interaction)
            else:
                logger.error("There is no track currently playing, and no interaction available to let the user know.")
            return

        # If the now-playing channel is somehow not stored, but we have a message, copy it from the message
        if self.now_playing_channel is None and self.now_playing_message is not None:
            self.now_playing_channel = self.now_playing_message.channel

        view = await self.create_now_playing_view()

        # Set up the now-playing embed
        song = self.current_song
        cover_art = backend.get_album_art_file(song.cover_id, self.guild_id)
        desc = ( f"**{song.title}** - *{song.artist}*"
        f"\n{song.album}"
        f"\n\n{ui.parse_elapsed_as_bar(self.elapsed, song.duration)}"
        )

        embed = discord.Embed(color=discord.Color.orange(), title="Now Playing", description=desc)
        embed.set_thumbnail(url="attachment://image.png")
        embed.set_footer(text=(
            f"{self.elapsed_printable} / {song.duration_printable}"
            f" - added by {song.username}"
        ))

        # Set up message args (avoid re-sending data, like attachments)
        kwargs = {"embed": embed, "view": view}
        if (force_create):
            kwargs["file"] = ui.get_thumbnail(cover_art)
        elif (interaction is not None 
                or self.now_playing_last_song is None 
                or self.current_song.song_id != self.now_playing_last_song.song_id):
            kwargs["attachments"] = [ui.get_thumbnail(cover_art)]

        # We can force create a message as long as we have the channel to create it in
        if force_create:
            await self.delete_now_playing()
            self.now_playing_message = await self.now_playing_channel.send(**kwargs)

        # If an interaction was passed, assume that we want to respond to it and make it the new message to update
        elif interaction is not None:

            # Defer the interaction if it hasn't been deferred yet, and delete the last message
            if not interaction.response.is_done():
                await interaction.response.defer(thinking=False)

            # Avoid deleting a message that we're responding to
            if interaction.message is None or self.now_playing_message.id != interaction.message.id:
                await self.delete_now_playing()

            # Update the now-playing message
            self.now_playing_message = await interaction.edit_original_response(**kwargs)

        else: # Otherwise, just edit the existing message
            await self.now_playing_message.edit(**kwargs)


        # Start a task to update the now-playing message on a time interval
        async def update_loop() -> None:
            
            # Prevent more than one instance of the update loop from running
            if asyncio.current_task() is not self.now_playing_update_task:
                return
            
            while self.current_song is not None:
                await asyncio.sleep(4)
                if not self.paused:
                    await self.update_now_playing()

            self.now_playing_update_task = None


        if self.now_playing_update_task is None:
            self.now_playing_update_task = asyncio.create_task(update_loop(), name="now_playing_update_task")

        # Successful update: track the last song we updated information for
        self.now_playing_last_song = song


    async def create_now_playing_view(self) -> discord.ui.View:
        ''' Creates a now-playing view, and sets up button callbacks. '''

        # Create a view for the player, as well as the buttons
        view = discord.ui.View(timeout=3600)

        if self.paused:
            pause_button = discord.ui.Button(label="▶\u00A0\u00A0PLAY", custom_id="unpause_button")
        else:
            pause_button = discord.ui.Button(label="❚❚\u00A0\u00A0PAUSE", custom_id="pause_button")
        pause_button.style = discord.ButtonStyle.gray

        stop_button = discord.ui.Button(label="◻️\u00A0\u00A0STOP", custom_id="stop_button")
        stop_button.style = discord.ButtonStyle.gray
        skip_button = discord.ui.Button(label="SKIP\u00A0\u00A0➤❙", custom_id="skip_button")
        skip_button.style = discord.ButtonStyle.gray

        view.add_item(pause_button)
        view.add_item(stop_button)
        view.add_item(skip_button)


        # Callback to handle pausing/unpausing
        async def paused_unpaused(interaction: discord.Interaction) -> None:
            await interaction.response.defer(thinking=False)

            # Check if user is in voice channel
            if interaction.user.voice is None:
                return await ui.ErrMsg.user_not_in_voice_channel(interaction)

            # Can't pause/unpause when not in a voice channel
            voice_client: discord.VoiceClient = interaction.guild.voice_client
            if voice_client is None:
                await ui.ErrMsg.bot_not_in_voice_channel(interaction)
                return

            if (interaction.data["custom_id"] == "pause_button"):
                self.last_elapsed = self.elapsed
                self.paused = True
                voice_client.pause()
            else:
                self.last_start_time = int(time.time())
                self.paused = False
                voice_client.resume()

            await self.update_now_playing()


        # Callback to handle skipping
        async def skipped(interaction: discord.Interaction) -> None:
            # Check if user is in voice channel
            if interaction.user.voice is None:
                return await ui.ErrMsg.user_not_in_voice_channel(interaction)

            await interaction.response.defer(thinking=False)
            await self.skip_track(interaction.guild.voice_client)
            await self.update_now_playing()


        # Callback to handle stopping
        async def stopped(interaction: discord.Interaction) -> None:
            # Check if user is in voice channel
            if interaction.user.voice is None:
                return await ui.ErrMsg.user_not_in_voice_channel(interaction)

            voice_client = interaction.guild.voice_client
            await self.disconnect(interaction, voice_client)


        # Assign button callbacks
        pause_button.callback = paused_unpaused
        skip_button.callback = skipped
        stop_button.callback = stopped

        return view


    async def delete_now_playing(self):
        ''' Deletes the now playing message. '''
        
        if (self.now_playing_message is not None):
            try:
                await self.now_playing_message.delete()
                self.now_playing_message = None
            except discord.HTTPException:
                pass

