''' An extention allowing for music playback functionality '''

import logging
import discord

from discord import app_commands
from discord.ext import commands

import data
import player
import subsonic
import ui

from submeister import SubmeisterClient

logger = logging.getLogger(__name__)


class MusicCog(commands.Cog):
    ''' A Cog containing music playback commands '''

    bot : SubmeisterClient


    def __init__(self, bot: SubmeisterClient):
        self.bot = bot


    async def get_voice_client(self, interaction: discord.Interaction, *, should_connect: bool=False) -> discord.VoiceClient:
        ''' Returns a voice client instance for the current guild '''

        # Get the voice client for the guild
        voice_client = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)

        # Connect to a voice channel
        if voice_client is None and should_connect:
            try:
                voice_client = await interaction.user.voice.channel.connect()
            except AttributeError:
                await ui.ErrMsg.cannot_connect_to_voice_channel(interaction)

        return voice_client


    @app_commands.command(name="play", description="Play a specific track.")
    @app_commands.describe(query="Enter a search query")
    async def play(self, interaction: discord.Interaction, query: str=None) -> None:
        ''' Play a track matching the given title/artist query '''

        # Check if user is in voice channel
        if interaction.user.voice is None:
            return await ui.ErrMsg.user_not_in_voice_channel(interaction)

        # Get a valid voice channel connection
        voice_client = await self.get_voice_client(interaction, should_connect=True)

        # Don't attempt playback if the bot is already playing
        if voice_client.is_playing() and query is None:
            return await ui.ErrMsg.already_playing(interaction)

        # Get the guild's player
        player = data.guild_data(interaction.guild_id).player

        # Check queue if no query is provided
        if query is None:

            # Display error if queue is empty & autoplay is disabled
            if player.queue == [] and data.guild_properties(interaction.guild_id).autoplay_mode == data.AutoplayMode.NONE:
                return await ui.ErrMsg.queue_is_empty(interaction)

            # Begin playback of queue
            await ui.SysMsg.starting_queue_playback(interaction)
            await player.play_audio_queue(interaction, voice_client)

        else:
            # Send our query to the subsonic API and retrieve a list of 1 song
            songs = subsonic.search(query, artist_count=0, album_count=0, song_count=1)

            # Display an error if the query returned no results
            if len(songs) == 0:
                await ui.ErrMsg.msg(interaction, f"No result found for **{query}**.")
                return
            
            # Add the first result to the queue and handle queue playback
            songs[0].username = interaction.user.display_name
            player.queue.append(songs[0])

            await ui.SysMsg.added_to_queue(interaction, songs[0])
            await player.play_audio_queue(interaction, voice_client)

        if (player.now_playing_message is None):
                await player.update_now_playing(interaction, force_create=True)


    @app_commands.command(name="search", description="Search for a track.")
    @app_commands.describe(query="Enter a search query")
    async def search(self, interaction: discord.Interaction, query: str) -> None:
        ''' Search for tracks by the given title/artist & list them '''

        # The number of songs to retrieve and the offset to start at
        song_count = 10 # TODO: Make this user-adjustable
        song_offset = 0

        # Send our query to the subsonic API and retrieve a list of songs
        songs = subsonic.search(query, artist_count=0, album_count=0, song_count=song_count, song_offset=song_offset)

        # Display an error if the query returned no results
        if len(songs) == 0:
            await ui.ErrMsg.msg(interaction, f"No results found for **{query}**.")
            return

        # Create a view for our response
        view = discord.ui.View()

        # Create a select menu option for each of our results
        select_options = ui.parse_search_as_track_selection_options(songs)

        # Create a select menu, populated with our options
        song_selector = discord.ui.Select(placeholder="Select a track", options=select_options)
        view.add_item(song_selector)


        # Callback to handle interaction with a select item
        async def song_selected(interaction: discord.Interaction) -> None:
            voice_client = await self.get_voice_client(interaction)

            # Don't allow users who aren't in a voice channel with the bot to queue tracks
            if voice_client is not None and interaction.user.status is None:
                return await ui.ErrMsg.user_not_in_voice_channel(interaction)

            # Get the song selected by the user
            selected_song = songs[int(song_selector.values[0])]
            selected_song.username = interaction.user.display_name

            # Get the guild's player
            player = data.guild_data(interaction.guild_id).player

            # Add the selected song to the queue
            player.queue.append(selected_song)

            # Let the user know a track has been added to the queue
            await ui.SysMsg.added_to_queue(interaction, selected_song)

            # Fetch the cover art in advance
            subsonic.get_album_art_file(selected_song.cover_id, interaction.guild_id)

            # Attempt to play the audio queue, if the bot is in the voice channel
            if voice_client is not None:
                await player.play_audio_queue(interaction, voice_client)


        # Assign the song_selected callback to the select menu
        song_selector.callback = song_selected

        # Create page navigation buttons
        prev_button = discord.ui.Button(label="<", custom_id="prev_button")
        next_button = discord.ui.Button(label=">", custom_id="next_button")
        view.add_item(prev_button)
        view.add_item(next_button)


        # Callback to handle interactions with page navigator buttons
        async def page_changed(interaction: discord.Interaction) -> None:
            nonlocal song_count, song_offset, song_selector, song_selected, songs

            # Adjust the search offset according to the button pressed
            if interaction.data["custom_id"] == "prev_button":
                song_offset -= song_count
                if song_offset < 0:
                    song_offset = 0
                    await interaction.response.defer()
                    return
            elif interaction.data["custom_id"] == "next_button":
                song_offset += song_count

            # Send our query to the Subsonic API and retrieve a list of songs, backing up the previous page's songs first
            songs_lastpage = songs
            songs = subsonic.search(query, artist_count=0, album_count=0, song_count=song_count, song_offset=song_offset)

            # If there are no results on this page, go back one page and don't update the response
            if len(songs) == 0:
                song_offset -= song_count
                songs = songs_lastpage
                await interaction.response.defer()
                return

            # Generate a new embed containing this page's search results
            song_list = ui.parse_search_as_track_selection_embed(songs, query, (song_offset // song_count) + 1)

            # Create a selection menu, populated with our new options
            select_options = ui.parse_search_as_track_selection_options(songs)

            # Update the selector in the existing view
            view.remove_item(song_selector)
            song_selector = discord.ui.Select(placeholder="Select a track", options=select_options)
            song_selector.callback = song_selected
            view.add_item(song_selector)

            # Update the message to show the new search results
            await interaction.response.edit_message(embed=song_list, view=view)


        # Assign the page_changed callback to the page navigation buttons
        prev_button.callback = page_changed
        next_button.callback = page_changed

        # Generate a formatted embed for the current search results
        song_list = ui.parse_search_as_track_selection_embed(songs, query, (song_offset // song_count) + 1)

        # Show our song selection menu
        await interaction.response.send_message(embed=song_list, view=view, ephemeral=True)


    @app_commands.command(name="stop", description="Stop playing the current track.")
    async def stop(self, interaction: discord.Interaction) -> None:
        ''' Disconnect from the active voice channel '''

        voice_client = await self.get_voice_client(interaction)
        player = data.guild_data(interaction.guild_id).player

        await player.disconnect(interaction, voice_client)


    @app_commands.command(name="show-queue", description="View the current queue.")
    async def show_queue(self, interaction: discord.Interaction) -> None:
        ''' Show the current queue '''

        # Get the audio queue for the current guild
        queue = data.guild_data(interaction.guild_id).player.queue

        # Create a string to store the output of our queue
        output = ""

        # Loop over our queue, adding each song into our output string
        for i, song in enumerate(queue):
            output += f"{i+1}. **{song.title}** - *{song.artist}*\n{song.album} ({song.duration_printable})\n\n"

        # Check if our output string is empty & update it accordingly
        if output == "":
            output = "Queue is empty!"

        # Show the user their queue
        await ui.SysMsg.msg(interaction, "Queue", output)


    @app_commands.command(name="clear-queue", description="Clear the queue.")
    async def clear_queue(self, interaction: discord.Interaction) -> None:
        '''Clear the queue'''
        queue = data.guild_data(interaction.guild_id).player.queue
        queue.clear()

        # Let the user know that the queue has been cleared
        await ui.SysMsg.queue_cleared(interaction)


    @app_commands.command(name="skip", description="Skip the current track.")
    async def skip(self, interaction: discord.Interaction) -> None:
        ''' Skip the current track '''

        voice_client = await self.get_voice_client(interaction)

        # Check if the bot is connected to a voice channel
        if voice_client is None:
            await ui.ErrMsg.bot_not_in_voice_channel(interaction)
            return
        
        # Check if the bot is playing music
        if not voice_client.is_playing():
            await ui.ErrMsg.not_playing(interaction)
            return

        player = data.guild_data(interaction.guild_id).player
        await player.skip_track(voice_client)

        # Display confirmation message
        await ui.SysMsg.skipping(interaction)


    @app_commands.command(name="now-playing", description="Show the currently playing track.")
    async def now_playing(self, interaction: discord.Interaction) -> None:
        ''' Display the player controls & details for the currently playing song. '''

        # Check if our voice client is connected
        voice_client = await self.get_voice_client(interaction)
        if voice_client is None:
            await ui.ErrMsg.bot_not_in_voice_channel(interaction)
            return

        player = data.guild_data(interaction.guild_id).player
        await interaction.response.defer(thinking=False)
        await player.update_now_playing(interaction)


    @app_commands.command(name="autoplay", description="Toggles autoplay")
    @app_commands.describe(mode="Determines the method to use when autoplaying")
    @app_commands.choices(mode=[
        app_commands.Choice(name="None", value="none"),
        app_commands.Choice(name="Random", value="random"),
        app_commands.Choice(name="Similar", value="similar"),
    ])
    async def autoplay(self, interaction: discord.Interaction, mode: app_commands.Choice[str]) -> None:
        ''' Toggles autoplay '''

        # Update the autoplay properties
        match mode.value:
            case "none":
                data.guild_properties(interaction.guild_id).autoplay_mode = data.AutoplayMode.NONE
            case "random":
                data.guild_properties(interaction.guild_id).autoplay_mode = data.AutoplayMode.RANDOM
            case "similar":
                data.guild_properties(interaction.guild_id).autoplay_mode = data.AutoplayMode.SIMILAR

        # Display message indicating new status of autoplay
        if mode.value == "none":
            await ui.SysMsg.msg(interaction, f"Autoplay disabled by {interaction.user.display_name}")
        else:
            await ui.SysMsg.msg(interaction, f"Autoplay enabled by {interaction.user.display_name}", f"Autoplay mode: **{mode.name}**")

        # If the bot is connected to a voice channel and autoplay is enabled, start queue playback
        voice_client = await self.get_voice_client(interaction)
        if voice_client is not None and not voice_client.is_playing():
            player = data.guild_data(interaction.guild_id).player
            await player.play_audio_queue(interaction, voice_client)


async def setup(bot: SubmeisterClient):
    ''' Setup function for the music.py cog '''

    await bot.add_cog(MusicCog(bot))
