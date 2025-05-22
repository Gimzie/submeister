''' A player object that handles playback and data for its respective guild '''

import asyncio
import discord
import logging
import random
import time

import data
import subsonic
import ui
import util.discord

from subsonic import Song

logger = logging.getLogger(__name__)

# Default player data
_default_data: dict[str, any] = {
    "guild-id": 0,
    "current-song": None,
    "last-elapsed": 0,
    "last-start-time": 0,
    "paused": False,
    "now-playing-message": None,
    "queue": [],
}

class Player():
    ''' Class that represents an audio player '''

    def __init__(self, guild_id: int) -> None:
        self._data = _default_data
        self._data["guild-id"] = guild_id
        self._now_playing_update_task = None


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
    def queue(self, value: list) -> None:
        self._data["queue"] = value


    @property
    def now_playing_update_task(self) -> asyncio.Task:
        ''' An update task that updates the now-playing message on an interval. '''
        return self._now_playing_update_task
    

    @now_playing_update_task.setter
    def now_playing_update_task(self, task: asyncio.Task) -> None:
        self._now_playing_update_task = task



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
                           "options": "-filter:a volume=replaygain=track"}
        audio_src = discord.FFmpegOpusAudio(subsonic.stream(song.song_id), **ffmpeg_options)
        # audio_src.read()

        # Update the currently playing song's data
        self.current_song = song
        self.last_start_time = int(time.time())
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
                    and asyncio.run_coroutine_threadsafe(util.discord.visually_has_n_messages_after(32, self.now_playing_message), loop).result()):
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

        autoplay_mode = data.guild_properties(interaction.guild_id).autoplay_mode
        queue = data.guild_data(interaction.guild_id).player.queue

        # If queue is notempty or autoplay is disabled, don't handle autoplay
        if queue != [] or autoplay_mode is data.AutoplayMode.NONE:
            return

        # If there was no previous song provided, we default back to selecting a random song
        if prev_song_id is None:
            autoplay_mode = data.AutoplayMode.RANDOM

        songs = []

        match autoplay_mode:
            case data.AutoplayMode.RANDOM:
                songs = subsonic.get_random_songs(size=1)
            case data.AutoplayMode.SIMILAR:
                songs = subsonic.get_similar_songs(song_id=prev_song_id, count=1)

        # If there's no match, throw an error
        if len(songs) == 0:
            await ui.ErrMsg.msg(interaction, "Failed to obtain a song for autoplay.")
            return
        
        songs[0].username = "Autoplay"
        self.queue.append(songs[0])

        # Fetch the cover art in advance
        subsonic.get_album_art_file(songs[0].cover_id, interaction.guild_id)


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

            # Reset the last elapsed time, since we are starting a song from scratch
            self.last_elapsed = 0
            return
            
        # If the queue is empty, playback has ended; we should let the user know
        await ui.SysMsg.playback_ended(interaction)


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
            Forcing the creation of a message requires a valid interaction in order
            to determine which channel the now-playing view should be sent in.
        '''

        if (self.now_playing_message is None and interaction is None):
            logger.error("There is no message to update, and there is not enough context to create one.")
            return

        view = await self.create_now_playing_view()

        # Set up the now-playing embed
        song = self.current_song
        cover_art = subsonic.get_album_art_file(song.cover_id, self.guild_id)
        desc = ( f"**{song.title}** - *{song.artist}*"
        f"\n{song.album}"
        f"\n\n{ui.parse_elapsed_as_bar(self.elapsed, song.duration)}"
        )

        embed = discord.Embed(color=discord.Color.orange(), title="Now Playing", description=desc,)
        embed.set_thumbnail(url="attachment://image.png")
        embed.set_footer(text=(
            f"{self.elapsed_printable} / {song.duration_printable}"
            f" - added by {song.username}"
        ))

        # Set up message args (avoid re-sending data, like attachments)
        kwargs = {"embed": embed, "view": view}
        if (force_create and interaction is not None):
            kwargs["file"] = ui.get_thumbnail(cover_art)
        elif (interaction is not None or self.elapsed == 0):
            kwargs["attachments"] = [ui.get_thumbnail(cover_art)]

        # If an interaction was passed, assume that we want to respond to it and make it the new message to edit
        if interaction is not None:
            await self.delete_now_playing()
            if (force_create):
                self.now_playing_message = await interaction.channel.send(**kwargs)
            else:
                self.now_playing_message = await interaction.edit_original_response(**kwargs)

        else: # Otherwise, just edit the existing message (TODO: Check how "buried" the last message is)
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

