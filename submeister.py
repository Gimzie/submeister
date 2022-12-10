# Submeister - A Discord bot that streams music from your personal Subsonic server.

import discord
import os
import requests

from discord import app_commands
from dotenv import load_dotenv
from urllib import parse as urlParse

load_dotenv(os.path.relpath("data.env"))

# Get Subsonic server details
SUB_SERVER = os.getenv("SUBSONIC_SERVER")
SUB_USER = os.getenv("SUBSONIC_USER")
SUB_PASSWORD = os.getenv("SUBSONIC_PASSWORD")

# Get Discord bot details
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Get the guild id to populate commands to
if os.getenv("DISCORD_TEST_GUILD") is not None:
    DISCORD_TEST_GUILD = discord.Object(id=os.getenv("DISCORD_TEST_GUILD"))
else:
    DISCORD_TEST_GUILD = None

# Parameters for the Subsonic API
SUBSONIC_REQUEST_PARAMS = {
        "u": SUB_USER,
        "p": SUB_PASSWORD,
        "v": "1.15.0",
        "c": "submeister",
        "f": "json"
    }


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
        print(f'Successfully connected as account: {self.user}')


sm_client = submeisterClient()
command_tree = app_commands.CommandTree(sm_client)


async def get_voice_client(interaction: discord.Interaction, *, should_connect: bool=False) -> discord.VoiceClient:
    ''' Returns a voice client instance for the current guild '''
    voice_client = discord.utils.get(sm_client.voice_clients, guild=interaction.guild)

    # Connect to a voice channel
    if voice_client is None and should_connect:
        try:
            voice_client = await interaction.user.voice.channel.connect()
        except AttributeError:
            await interaction.response.send_message("Failed to connect to voice channel.")

    return voice_client


async def stream_track(interaction: discord.Interaction, song_id: str) -> None:
    ''' Streams a track from the Subsonic server '''

    # Stream from the Subsonic server, using the provided song ID
    url = f"{SUB_SERVER}/rest/stream.view?id={song_id}"

    song = requests.get(url, params=SUBSONIC_REQUEST_PARAMS, stream=True)

    audio_src = discord.FFmpegPCMAudio(song.url)

    voice_client = await get_voice_client(interaction, should_connect=True)

    if not voice_client.is_playing():
        voice_client.play(audio_src)


@command_tree.command(name="play", description='plays a specified song', guild=DISCORD_TEST_GUILD)
async def play(interaction: discord.Interaction, query: str) -> None:
    ''' Play a track matching the given title/artist query '''

    # Sanitize special characters in the user's query
    parsed_query = urlParse.quote(query, safe='')

    # Use Search2 from the Subsonic API to search by keyword
    url = f"{SUB_SERVER}/rest/search2.view?query={parsed_query}&artistCount=1&songCount=1"

    # Send a request to the server and store the response
    response = requests.get(url, params=SUBSONIC_REQUEST_PARAMS)

    # Check for a top search result
    search_data = response.json()
    songs = search_data["subsonic-response"]["searchResult2"]["song"]

    if len(songs) == 0:
        await interaction.response.send_message("No results found for **" + query + "**.")
        return

    # Stream the top-most track & inform the user
    try:
        await stream_track(interaction, songs[0]["id"])

        # Assign placeholder values if a specified tag is not present for the selected song
        title_str = songs[0]["title"] if "title" in songs[0] else "Unknown Song"
        artist_str = songs[0]["artist"] if "artist" in songs[0] else "Unknown Artist"

        await interaction.response.send_message(f"Now playing: {title_str} - *{artist_str}*")
    except AttributeError:
        await interaction.response.send_message("You have to be in a voice channel to play a song.")
        return False


@command_tree.command(name="search", description="Search for a song", guild=DISCORD_TEST_GUILD)
async def search(interaction: discord.Interaction, query: str) -> None:
    ''' Search for tracks by the given title/artist & list them '''

    # Sanitize special characters in the user's query
    parsed_query = urlParse.quote(query, safe='')

    # Use Search3 from the Subsonic API to search by keyword
    response = requests.get(f"{SUB_SERVER}/rest/search3.view?query={parsed_query}", params=SUBSONIC_REQUEST_PARAMS)
    search_data = response.json()

    # Output the list of tracks to the user
    songs = search_data["subsonic-response"]["searchResult3"]["song"]

    if len(songs) == 0:
        await interaction.response.send_message("No results found for **" + query + "**.")
    else:
        output = "Results for **" + query + "**:\n\n"
        for i, song in enumerate(songs):

            # Assign placeholder values if a specified tag is not present for the selected song
            title_str = song["title"] if "title" in song else "Unknown Song"
            artist_str = song["artist"] if "artist" in song else "Unknown Artist"
            album_str = song["album"] if "album" in song else "Unknown Album"

            output += f"**{i+1}.** {title_str} - *{artist_str}*    [from {album_str}]\n\n"
            if i == 9: # temporary
                break
        await interaction.response.send_message(output)


@command_tree.command(name="stop", description="Stop playing the current song", guild=DISCORD_TEST_GUILD)
async def stop(interaction: discord.Interaction) -> None:
    ''' Disconnect from the active voice channel '''

    voice_client = await get_voice_client(interaction)

    if voice_client == None:
        await interaction.response.send_message("Not currently connected to a voice channel.")
    else:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("Disconnected from the active voice channel.")


# Run Submeister
sm_client.run(BOT_TOKEN)
