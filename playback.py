'''For playback-related operations'''

import asyncio
import discord

import data
import subsonic
import ui

from subsonic import Song

async def stream_track(interaction: discord.Interaction, song: Song, voice_client: discord.VoiceClient) -> None:
    ''' Streams a track from the Subsonic server to a connected voice channel, and updates guild data accordingly'''

    # Make sure the voice client is available
    if voice_client is None:
        await ui.ErrMsg.bot_not_in_voice_channel(interaction)
        return

    # Make sure the bot isn't already playing music
    if voice_client.is_playing():
        await ui.ErrMsg.already_playing(interaction)
        return

    # Get the stream from the Subsonic server, using the provided song's ID
    ffmpeg_options = {"before_options": "", "options": "-filter:a volume=replaygain=track"}
    audio_src = discord.FFmpegOpusAudio(subsonic.stream(song.id), **ffmpeg_options)
    audio_src.read()

    # Update the currently playing song, and reset the duration
    data.guild_data(interaction.guild_id).current_song = song
    data.guild_data(interaction.guild_id).current_position = 0

    # Let the user know the track will play
    await ui.SysMsg.playing(interaction)

    # TODO: Start a duration timer

    # Begin playing the song
    loop = asyncio.get_event_loop()
    voice_client.play(audio_src, after=lambda error: asyncio.run_coroutine_threadsafe(play_audio_queue(interaction, voice_client), loop)) # TODO: probably should handle error


async def get_voice_client(interaction: discord.Interaction, *, should_connect: bool=False) -> discord.VoiceClient:
    ''' Returns a voice client instance for the current guild '''

    # Get the voice client for the guild
    voice_client = discord.utils.get(data.sm_client.voice_clients, guild=interaction.guild)

    # Connect to a voice channel
    if voice_client is None and should_connect:
        try:
            voice_client = await interaction.user.voice.channel.connect()
        except AttributeError:
            await ui.ErrMsg.cannot_connect_to_voice_channel(interaction)

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
            songs = subsonic.get_random_songs(size=1)
        case data.AutoplayMode.SIMILAR:
            songs = subsonic.get_similar_songs(id=prev_song_id, count=1)        

    # If there's no match, throw an error
    if len(songs) == 0:
        await ui.ErrMsg.msg(interaction, "Failed to obtain a song for autoplay.")
        return

    queue = data.guild_properties(interaction.guild_id).queue
    queue.append(songs[0])

    # Fetch the cover art in advance
    subsonic.get_album_art_file(songs[0].cover_id)


async def play_audio_queue(interaction: discord.Interaction, voice_client: discord.VoiceClient) -> None:

    # Check if the bot is connected to a voice channel; it's the caller's responsibility to open a voice channel
    if voice_client is None:
        await ui.ErrMsg.bot_not_in_voice_channel(interaction);
        return

    queue = data.guild_properties(interaction.guild_id).queue

    # If queue is empty but autoplay is enabled, handle autoplay
    if queue == [] and data.guild_properties(interaction.guild_id).autoplay_mode is not data.AutoplayMode.NONE:
        await handle_autoplay(interaction)

    # Check if the queue contains songs
    if queue != []:

        # Pop the first item from the queue and begin streaming it
        song = queue.pop(0)
        await stream_track(interaction, song, voice_client)

        # If queue will be empty after playback ends, handle autoplay
        if queue == [] and data.guild_properties(interaction.guild_id).autoplay_mode is not data.AutoplayMode.NONE:
            await handle_autoplay(interaction, song.id)
        return

    # If the queue is empty, playback has ended; we should let the user know
    await ui.SysMsg.playback_ended(interaction)
