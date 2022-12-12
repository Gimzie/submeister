# Submeister - A Discord bot that streams music from your personal Subsonic server.

import discord
import os
import subsonic
import asyncio

from discord import app_commands
from dotenv import load_dotenv

load_dotenv(os.path.relpath("data.env"))

# Get Discord bot details
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Get the guild id to populate commands to
if os.getenv("DISCORD_TEST_GUILD") is not None:
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

sm_client = submeisterClient()
command_tree = app_commands.CommandTree(sm_client)

# Dictionary to store audio queues
audio_queues = {}


def get_audio_queue(guild_id: discord.Interaction.guild_id) -> list:
    ''' Returns the audio queue for the specified guild '''

    # Return the current audio queue for the guild if one exists
    if guild_id in audio_queues:
        return audio_queues[guild_id]

    # Create an audio queue for the guild if one doesn't exist
    queue = []
    audio_queues[guild_id] = queue
    return queue


async def play_audio_queue(interaction: discord.Interaction) -> None:
    queue = get_audio_queue(interaction.guild_id)

    # Check if the queue is empty
    if queue != []:
        # Pop the first item from the queue and begin streaming it
        song = queue.pop(0)
        await stream_track(interaction, song['id'])

        # Display an embed that shows the song that is currently playing
        now_playing = f"{song['title']} - *{song['artist']}*"
        embed = discord.Embed(color=discord.Color.orange(), title="Now playing:", description=f"{now_playing}")
        await interaction.followup.send(embed=embed)
        return

    # If the queue is empty, playback has ended. Display an embed indicating that playback ended
    embed = discord.Embed(color=discord.Color.orange(), title="Playback ended.")
    await interaction.followup.send(embed=embed)


def ensure_song_has_tags(song: dict) -> dict:
    ''' Takes a song object that was returned from the subsonic API and ensures all necessary tag keys are present on the object '''

    # Ensure title tag is present
    if 'title' not in song:
        song['title'] = "Unknown Track"

    # Ensure artist tag is present
    if 'artist' not in song:
        song['artist'] = "Unknown Artist"

    # Ensure album tag is present
    if 'album' not in song:
        song['album'] = "Unknown Album"

    return song


async def get_voice_client(interaction: discord.Interaction, *, should_connect: bool=False) -> discord.VoiceClient:
    ''' Returns a voice client instance for the current guild '''

    # Get the voice client for the guild
    voice_client = discord.utils.get(sm_client.voice_clients, guild=interaction.guild)

    # Connect to a voice channel
    if voice_client is None and should_connect:
        try:
            voice_client = await interaction.user.voice.channel.connect()
        except AttributeError:
            await interaction.edit_original_response(content="Failed to connect to voice channel.")

    return voice_client


async def stream_track(interaction: discord.Interaction, song_id: str) -> None:
    ''' Streams a track from the Subsonic server '''

    # Get the stream from the Subsonic server, using the provided song ID
    ffmpeg_options = {"before_options": "", "options": "-filter:a volume=replaygain=track"}
    audio_src = discord.FFmpegPCMAudio(subsonic.stream(song_id), **ffmpeg_options)

    # Get the voice client for the current guild
    voice_client = await get_voice_client(interaction, should_connect=True)

    # Begin playing the song
    if not voice_client.is_playing():
        loop = asyncio.get_event_loop()
        voice_client.play(audio_src, after=lambda error: asyncio.run_coroutine_threadsafe(play_audio_queue(interaction), loop)) # TODO: probably should handle error


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
        if get_audio_queue(interaction.guild_id) == []:
            embed = discord.Embed(color=discord.Color.orange(), title="Error", description="Queue is empty.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Begin playback of queue
        embed = discord.Embed(color=discord.Color.orange(), title="Starting queue playback")
        await interaction.response.send_message(embed=embed)
        await play_audio_queue(interaction)
        return

    # Send our query to the subsonic API and retrieve a list of 1 songs
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
    song = ensure_song_has_tags(song)

    # Stream the top-most track & inform the user
    await stream_track(interaction, song['id'])

    # Create an embed that shows the selected song has been added to queue
    now_playing = f"{song['title']} - *{song['artist']}*"

    embed = discord.Embed(color=discord.Color.orange(), title="Now playing:", description=f"{now_playing}")
    await interaction.response.send_message(embed=embed)


@command_tree.command(name="search", description="Search for a track", guild=DISCORD_TEST_GUILD)
@app_commands.describe(query="Enter a search query")
@app_commands.rename(page_num="page-number")
@app_commands.describe(page_num="Enter a page number to fetch")
async def search(interaction: discord.Interaction, query: str, page_num: int=0) -> None:
    ''' Search for tracks by the given title/artist & list them '''

    # The number of songs to retrieve and the offset to begin at
    song_count = 10
    song_offset = 0

    # Increment the song offset if the current page > 0
    if page_num > 0:
        page_num = page_num - 1
        song_offset = song_count * page_num

    # Send our query to the subsonic API and retrieve a list of songs
    results = subsonic.search(query, artist_count=0, album_count=0, song_count=song_count, song_offset=song_offset)
    songs = results['song']

    # Check if we received any results
    if len(songs) == 0:
        # Display an error if the query returned no results
        embed = discord.Embed(color=discord.Color.orange(), title="Error", description=f"No results found for **{query}**.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    options_str = ""
    select_options = []

    # Loop over our results
    for i, song in enumerate(songs):

        # Ensure required tags are present for all songs
        song = ensure_song_has_tags(song)

        # Add each of the results to our output string
        options_str += f"**{i+1}.** {song['title']} - *{song['artist']}*    [from {song['album']}]\n\n"

        # Create a select menu option for each of our results
        select_option = discord.SelectOption(label=f"{i+1}. {song['title']}", description=f"by {song['artist']}", value=i)
        select_options.append(select_option)

    # Add the current page number to our results
    options_str += f"Current page: {page_num + 1}"

    # Create embed that displays our output string
    song_list = discord.Embed(color=discord.Color.orange(), title=f"Showing Results for: {query}", description=options_str)

    # Create a select menu, populated with our options
    song_selector = discord.ui.Select(placeholder="Select a track", options=select_options)
    view = discord.ui.View()
    view.add_item(song_selector)

    # Create a callback to handle interaction with a select item
    async def song_selected(interaction: discord.Interaction) -> None:
        # Get the song selected by the user
        selected_song = songs[int(song_selector.values[0])]

        # Add the selected song to the queue
        queue = get_audio_queue(interaction.guild_id)
        queue.append(selected_song)
        
        # Create a confirmation embed
        selection_str = f"{selected_song['title']} - *{selected_song['artist']}*    [from {selected_song['album']}]\n\n"
        selection_embed = discord.Embed(color=discord.Color.orange(), title="Added selection to queue", description=f"{selection_str}")

        # Update the message to show the confirmation embed
        await interaction.response.edit_message(embed=selection_embed, view=None)

    # Assign the song_selected callback to the select menu
    song_selector.callback = song_selected

    # Show our song selection menu
    await interaction.response.send_message(embed=song_list, view=view)


@command_tree.command(name="stop", description="Stop playing the current track", guild=DISCORD_TEST_GUILD)
async def stop(interaction: discord.Interaction) -> None:
    ''' Disconnect from the active voice channel '''

    # Get the voice client instance for the current guild
    voice_client = await get_voice_client(interaction)

    # Check if our voice client is connected
    if voice_client == None:
        # Display error message if our client is not connected
        embed = discord.Embed(color=discord.Color.orange(), title="Error", description="Not currently connected to a voice channel.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Disconnect the voice client
    await interaction.guild.voice_client.disconnect()

    # Display disconnect confirmation
    embed = discord.Embed(color=discord.Color.orange(), title="Error", description="Disconnected from the active voice channel.")
    await interaction.response.send_message(embed=embed)


@command_tree.command(name="show-queue", description="View the current queue", guild=DISCORD_TEST_GUILD)
async def show_queue(interaction: discord.Interaction) -> None:
    ''' Show the current queue '''

    # Get the audio queue for the current guild
    queue = get_audio_queue(interaction.guild_id)

    # Create a string to store the output of our queue
    output = ""

    # Loop over our queue, adding each song into our output string
    for i, song in enumerate(queue):
        output += f"**{i+1}.** {song['title']} - *{song['artist']}*    [from {song['album']}]\n\n"

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
    voice_client = await get_voice_client(interaction)

    # Check if audio is currently playing
    if not voice_client.is_playing():
        # Display error message if nothing is currently playing
        embed = discord.Embed(color=discord.Color.orange(), title="Error", description=f"Could not skip. No track currently playing.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Stop the current song
    voice_client.stop()

    # Display confirmation message
    queue_embed = discord.Embed(color=discord.Color.orange(), title="Skipping")
    await interaction.response.send_message(embed=queue_embed)


# Run Submeister
sm_client.run(BOT_TOKEN)
