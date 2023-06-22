'''For playback-related operations'''

import asyncio
import discord

import data
import subsonic

async def stream_track(interaction: discord.Interaction, song_id: str) -> None:
    ''' Streams a track from the Subsonic server to a connected voice channel'''

    # Get the voice client for the current guild
    voice_client = await get_voice_client(interaction, should_connect=True)

    # Make sure the bot isn't already playing music
    if voice_client.is_playing():
        embed = discord.Embed(color=discord.Color.orange(), title="Error", description="Already playing music.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Get the stream from the Subsonic server, using the provided song ID
    ffmpeg_options = {"before_options": "", "options": "-filter:a volume=replaygain=track"}
    audio_src = discord.FFmpegOpusAudio(subsonic.stream(song_id), **ffmpeg_options)
    audio_src.read()

    # Begin playing the song
    loop = asyncio.get_event_loop()
    voice_client.play(audio_src, after=lambda error: asyncio.run_coroutine_threadsafe(play_audio_queue(interaction), loop)) # TODO: probably should handle error


async def get_voice_client(interaction: discord.Interaction, *, should_connect: bool=False) -> discord.VoiceClient:
    ''' Returns a voice client instance for the current guild '''

    # Get the voice client for the guild
    voice_client = discord.utils.get(data.sm_client.voice_clients, guild=interaction.guild)

    # Connect to a voice channel
    if voice_client is None and should_connect:
        try:
            voice_client = await interaction.user.voice.channel.connect()
        except AttributeError:
            await interaction.edit_original_response(content="Failed to connect to voice channel.")

    return voice_client


async def handle_autoplay(interaction: discord.Interaction, prev_song_id: str=None):
    ''' Handles populating the queue when autoplay is enabled '''

    autoplay_mode = data.guild_properties(interaction.guild_id).autoplay_mode

    # If there was no previous song provided, we default back to selecting a random song
    if prev_song_id is None:
        autoplay_mode = data.AutoplayMode.RANDOM

    songs = []

    match autoplay_mode:
        case data.AutoplayMode.RANDOM:
            results = subsonic.get_random_songs(size=1)
            songs = results['song']
        case data.AutoplayMode.SIMILAR:
            results = subsonic.get_similar_songs(id=prev_song_id, count=1)
            songs = results['song']
        

    if len(songs) == 0:
        embed = discord.Embed(color=discord.Color.orange(), title="Error", description=f"Autoplay failed")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    queue = data.guild_properties(interaction.guild_id).queue
    queue.append(songs[0])


async def play_audio_queue(interaction: discord.Interaction) -> None:
    queue = data.guild_properties(interaction.guild_id).queue

    # If queue is empty but autoplay is enabled, handle autoplay
    if queue == [] and data.guild_properties(interaction.guild_id).autoplay is True:
        await handle_autoplay(interaction)

    # Check if the queue contains songs
    if queue != []:

        # Pop the first item from the queue and begin streaming it
        song = queue.pop(0)
        await stream_track(interaction, song['id'])

        # If queue will be empty after playback ends, handle autoplay
        if queue == [] and data.guild_properties(interaction.guild_id).autoplay is True:
            await handle_autoplay(interaction, song['id'])

        # Display an embed that shows the song that is currently playing
        now_playing = f"**{song['title']}** - *{song['artist']}*"
        embed = discord.Embed(color=discord.Color.orange(), title="Now playing:", description=f"{now_playing}")
        await interaction.channel.send(embed=embed)
        return

    # If the queue is empty, playback has ended. Display an embed indicating that playback ended
    embed = discord.Embed(color=discord.Color.orange(), title="Playback ended.")
    await interaction.channel.send(embed=embed)