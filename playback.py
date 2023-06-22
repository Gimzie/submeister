'''For playback-related operations'''

import asyncio
import discord

import data
import subsonic

async def stream_track(interaction: discord.Interaction, song_id: str) -> None:
    ''' Streams a track from the Subsonic server to a connected voice channel'''

    # Get the stream from the Subsonic server, using the provided song ID
    ffmpeg_options = {"before_options": "", "options": "-filter:a volume=replaygain=track"}
    audio_src = discord.FFmpegPCMAudio(subsonic.stream(song_id), **ffmpeg_options)

    # Get the voice client for the current guild
    voice_client = await get_voice_client(interaction, should_connect=True)

    # Begin playing the song
    if not voice_client.is_playing():
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


def get_audio_queue(guild_id: discord.Interaction.guild_id) -> list:
    ''' Returns the audio queue for the specified guild '''

    # Return the current audio queue for the guild if one exists
    if guild_id in data.audio_queues:
        return data.audio_queues[guild_id]

    # Create an audio queue for the guild if one doesn't exist
    queue = []
    data.audio_queues[guild_id] = queue
    return queue


async def play_audio_queue(interaction: discord.Interaction) -> None:
    queue = get_audio_queue(interaction.guild_id)

    # Check if the queue is empty
    if queue != []:
        # Pop the first item from the queue and begin streaming it
        song = queue.pop(0)
        await stream_track(interaction, song['id'])

        # Display an embed that shows the song that is currently playing
        now_playing = f"{song['title']} - *{song['artist']}* ({song['duration']})"
        embed = discord.Embed(color=discord.Color.orange(), title="Now playing:", description=f"{now_playing}")
        await interaction.followup.send(embed=embed)
        return

    # If the queue is empty, playback has ended. Display an embed indicating that playback ended
    embed = discord.Embed(color=discord.Color.orange(), title="Playback ended.")
    await interaction.followup.send(embed=embed)