# Submeister - A Discord bot that streams music from your personal Subsonic server.

import discord
import os

import data
import playback
import subsonic
import ui

from discord import app_commands
from dotenv import load_dotenv

load_dotenv(os.path.relpath("data.env"))

# Get Discord bot details
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Get the guild id to populate commands to, if specified
if os.getenv("DISCORD_TEST_GUILD") not in (None, ""):
    DISCORD_TEST_GUILD = discord.Object(id=os.getenv("DISCORD_TEST_GUILD"))
else:
    DISCORD_TEST_GUILD = None

# Create the bot instance (TODO: Clean up intents)
class submeisterClient(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=discord.Intents.all())
        self.synced = False

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            await command_tree.sync(guild=DISCORD_TEST_GUILD)
            self.synced = True
        print(f"Successfully connected as account: {self.user}")

data.sm_client = submeisterClient()
command_tree = app_commands.CommandTree(data.sm_client)


# -------------------------------- Commands -------------------------------- #


@command_tree.command(name="play", description="Plays a specified track", guild=DISCORD_TEST_GUILD)
@app_commands.describe(query="Enter a search query")
async def play(interaction: discord.Interaction, query: str=None) -> None:
    ''' Play a track matching the given title/artist query '''

    # Check if user is in voice channel
    if interaction.user.voice is None:

        # Display error if user is not in voice channel
        embed = discord.Embed(color=discord.Color.orange(), title="Error", description="Please connect to a voice channel and try again.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Check queue if no query is provided
    if query is None:

        # Display error if queue is empty
        if playback.get_audio_queue(interaction.guild_id) == []:
            embed = discord.Embed(color=discord.Color.orange(), title="Error", description="Queue is empty.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Begin playback of queue
        embed = discord.Embed(color=discord.Color.orange(), title="Starting queue playback")
        await interaction.response.send_message(embed=embed)
        await playback.play_audio_queue(interaction)
        return

    # Send our query to the subsonic API and retrieve a list of 1 song
    results = subsonic.search(query, artist_count=0, album_count=0, song_count=1)
    songs = results['song']

    # Check if we received any results
    if len(songs) == 0:
        
        # Display an error if the query returned no results
        embed = discord.Embed(color=discord.Color.orange(), title="Error", description=f"No results found for **{query}**.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Take the first result
    song = songs[0]

    # Ensure our result has valid tags
    song = ui.ensure_song_has_displayable_tags(song)

    # Stream the top-most track & inform the user
    await playback.stream_track(interaction, song['id'])

    # Create an embed that shows the selected song has been added to queue
    now_playing = f"**{song['title']}** - *{song['artist']}*"

    embed = discord.Embed(color=discord.Color.orange(), title="Now playing:", description=f"{now_playing}")
    await interaction.response.send_message(embed=embed)


@command_tree.command(name="search", description="Search for a track", guild=DISCORD_TEST_GUILD)
@app_commands.describe(query="Enter a search query")
async def search(interaction: discord.Interaction, query: str) -> None:
    ''' Search for tracks by the given title/artist & list them '''

    # The number of songs to retrieve and the offset to start at
    song_count = 10 # TODO: Make this user-adjustable
    song_offset = 0

    # Send our query to the subsonic API and retrieve a list of songs
    results = subsonic.search(query, artist_count=0, album_count=0, song_count=song_count, song_offset=song_offset)
    songs = results['song']

    # Display an error if the query returned no results
    if len(songs) == 0:
        embed = discord.Embed(color=discord.Color.orange(), title="Error", description=f"No results found for **{query}**.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
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
        # Get the song selected by the user
        selected_song = songs[int(song_selector.values[0])]

        # Add the selected song to the queue
        queue = playback.get_audio_queue(interaction.guild_id)
        queue.append(selected_song)
        
        # Create a confirmation embed
        selection_str = f"**{selected_song['title']}** - *{selected_song['artist']}*\n{selected_song['album']} ({selected_song['duration']})"
        selection_embed = discord.Embed(color=discord.Color.orange(), title=f"{interaction.user.display_name} added selection to queue", description=f"{selection_str}")

        # Update the message to show the confirmation embed
        await interaction.response.send_message(embed=selection_embed)


    # Assign the song_selected callback to the select menu
    song_selector.callback = song_selected

    # Create page navigation buttons
    prev_button = discord.ui.Button(label="<", custom_id="prev_button")
    next_button = discord.ui.Button(label=">", custom_id="next_button")
    view.add_item(prev_button)
    view.add_item(next_button)


    # Callback to handle interactions with page navigator buttons
    async def page_changed(interaction: discord.Interaction) -> None:
        nonlocal song_count, song_offset, song_selector, song_selected, songs, results
        
        # Adjust the search offset according to the button pressed
        if interaction.data['custom_id'] == "prev_button":
            song_offset = max(song_offset - song_count, 0)
        elif interaction.data['custom_id'] == "next_button":
            song_offset += song_count

        # Send our query to the Subsonic API and retrieve a list of songs, backing up the previous page's songs first
        results = subsonic.search(query, artist_count=0, album_count=0, song_count=song_count, song_offset=song_offset)
        songs_lastpage = songs
        songs = results['song']

        # If there are no results on this page, go back one page and don't update the response
        if len(songs) == 0:
            song_offset -= song_count
            songs = songs_lastpage
            await interaction.response.defer()
            return

        # Generate a new embed containing this page's search results
        song_list = ui.parse_search_as_track_selection_embed(songs, query, song_offset // song_count)

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
    song_list = ui.parse_search_as_track_selection_embed(songs, query, song_offset // song_count)

    # Show our song selection menu
    await interaction.response.send_message(embed=song_list, view=view, ephemeral=True)


@command_tree.command(name="stop", description="Stop playing the current track", guild=DISCORD_TEST_GUILD)
async def stop(interaction: discord.Interaction) -> None:
    ''' Disconnect from the active voice channel '''

    # Get the voice client instance for the current guild
    voice_client = await playback.get_voice_client(interaction)

    # Check if our voice client is connected
    if voice_client == None:
        # Display error message if our client is not connected
        embed = discord.Embed(color=discord.Color.orange(), title="Error", description="Not currently connected to a voice channel.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Disconnect the voice client
    await interaction.guild.voice_client.disconnect()

    # Display disconnect confirmation
    embed = discord.Embed(color=discord.Color.orange(), title="Disconnected from the active voice channel.")
    await interaction.response.send_message(embed=embed)


@command_tree.command(name="show-queue", description="View the current queue", guild=DISCORD_TEST_GUILD)
async def show_queue(interaction: discord.Interaction) -> None:
    ''' Show the current queue '''

    # Get the audio queue for the current guild
    queue = playback.get_audio_queue(interaction.guild_id)

    # Create a string to store the output of our queue
    output = ""

    # Loop over our queue, adding each song into our output string
    for i, song in enumerate(queue):
        output += f"{i+1}. **{song['title']}** - *{song['artist']}*\n{song['album']} ({song['duration']})"

    # Check if our output string is empty & update it 
    if output == "":
        output = "Queue is empty!"
    
    # Create an embed that displays our output string
    queue_embed = discord.Embed(color=discord.Color.orange(), title="Current queue:", description=output)
    await interaction.response.send_message(embed=queue_embed)


@command_tree.command(name="skip", description="Skip the current track", guild=DISCORD_TEST_GUILD)
async def skip(interaction: discord.Interaction) -> None:
    ''' Skip the current track '''

    # Get the voice client instance
    voice_client = await playback.get_voice_client(interaction)

    # Check if audio is currently playing
    if not voice_client.is_playing():
        # Display error message if nothing is currently playing
        embed = discord.Embed(color=discord.Color.orange(), title="Error", description="Could not skip. No track currently playing.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Stop the current song
    voice_client.stop()

    # Display confirmation message
    queue_embed = discord.Embed(color=discord.Color.orange(), title="Skipping...")
    await interaction.response.send_message(embed=queue_embed)


# Run Submeister
data.sm_client.run(BOT_TOKEN)
