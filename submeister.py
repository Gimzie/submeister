# Submeister - A Discord bot that streams music from your personal Subsonic server.

import discord
import os
import requests

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv(os.path.relpath("data.env"))

# Get Subsonic server details
SUB_SERVER = os.getenv("SUBSONIC_SERVER")
SUB_USER = os.getenv("SUBSONIC_USER")
SUB_PASSWORD = os.getenv("SUBSONIC_PASSWORD")

# Get Discord bot details
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
BOT_PREFIX = ";"

# Parameters for the Subsonic API
SUBSONIC_REQUEST_PARAMS = {
        "u": SUB_USER,
        "p": SUB_PASSWORD,
        "v": "1.15.0",
        "c": "submeister",
        "f": "json"
    }

# Create the bot instance (TODO: Clean up intents)
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=discord.Intents.all())



async def stream_track(ctx, song_id: str) -> None:
    ''' Streams a track from the Subsonic server '''

    # Get the relevant voice channel & voice client
    channel = ctx.message.author.voice.channel
    client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    print(client)

    # If not already in a voice channel, join the user's
    if client == None:
        client = await channel.connect()

    # Stream from the Subsonic server, using the provided song ID
    url = f"{SUB_SERVER}/rest/stream.view?id={song_id}"

    song = requests.get(url, params=SUBSONIC_REQUEST_PARAMS, stream=True)
    client.stop()
    client.play(discord.FFmpegPCMAudio(song.url))



@bot.command()
async def play(ctx, query: str) -> None:
    ''' Play a track matching the given title/artist query '''

    # Use Search2 from the Subsonic API to search by keyword
    url = f"{SUB_SERVER}/rest/search2.view?query={query}&artistCount=1&songCount=1"

    # Send a request to the server and store the response
    response = requests.get(url, params=SUBSONIC_REQUEST_PARAMS)

    # Check for a top search result
    song_list = response.json()["subsonic-response"]["searchResult2"]["song"]

    if len(song_list) == 0:
        await ctx.send("No results found for **" + query + "**.")
        return

    # Stream the top-most track & inform the user
    await stream_track(ctx, song_list[0]["id"]);
    await ctx.send("Now playing: " + song_list[0]["title"] + " - *" + song_list[0]["artist"] + "*")


@bot.command()
async def search(ctx, query: str) -> None:
    ''' Search for tracks by the given title/artist & list them '''

    # Use Search3 from the Subsonic API to search by keyword
    response = requests.get(f"{SUB_SERVER}/rest/search3.view?query={query}", params=SUBSONIC_REQUEST_PARAMS)
    search_data = response.json()

    # Output the list of tracks to the user
    songs = search_data["subsonic-response"]["searchResult3"]["song"]

    if len(songs) == 0:
        await ctx.send("No results found for **" + query + "**.")
    else:
        output = "Results for **" + query + "**:\n\n"
        for i, song in enumerate(songs):
            output += f"**{i+1}.** {song['title']} - *{song['artist']}*\n"
        await ctx.send(output)


@bot.command()
async def stop(ctx) -> None:
    ''' Disconnect from the active voice channel '''

    if ctx.voice_client == None:
        await ctx.send("Not currently connected to a voice channel.")
    else:
        await ctx.voice_client.disconnect()
        await ctx.send("Disconected from the active voice channel.")



# Run Submeister
bot.run(BOT_TOKEN)
