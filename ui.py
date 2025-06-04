''' For complex UI-related tasks '''

import discord

import asyncio
import data
import logging
import math

from subsonic.song import Song
from subsonic.playlist import Playlist
import subsonic.backend as backend

logger = logging.getLogger(__name__)


class SysMsg:
    ''' A class for sending system messages '''

    @staticmethod
    async def msg(interaction: discord.Interaction, header: str, message: str=None,
                   thumbnail: str=None, standalone: bool=False) -> None:
        ''' Generic message function. Creates and sends message formatted as an embed '''

        embed = discord.Embed(color=discord.Color.orange(), title=header, description=message)
        embed.set_thumbnail(url="attachment://image.png")
            
        # Handle standalone messages
        if (standalone):
            await interaction.channel.send(file=get_thumbnail(thumbnail), embed=embed)
            return

        # Send the system message (accounting for race conditions/timeout)
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(thinking=False)
                
            await interaction.followup.send(file=get_thumbnail(thumbnail), embed=embed)
        except:
            logger.warning("Follow-up message could not be properly sent, sending as a standalone message instead.")
            await interaction.channel.send(file=get_thumbnail(thumbnail), embed=embed)


    @staticmethod
    async def playback_ended(interaction: discord.Interaction) -> None:
        ''' Sends a message indicating playback has ended '''
        await __class__.msg(interaction, "Playback ended")


    @staticmethod
    async def disconnected(interaction: discord.Interaction) -> None:
        ''' Sends a message indicating the bot disconnected from voice channel '''
        await __class__.msg(interaction, "Disconnected from voice channel")


    @staticmethod
    async def starting_queue_playback(interaction: discord.Interaction) -> None:
        ''' Sends a message indicating queue playback has started '''
        await __class__.msg(interaction, "Started queue playback")


    @staticmethod
    async def added_to_queue(interaction: discord.Interaction, song: Song) -> None:
        ''' Sends a message indicating the selected song was added to queue '''
        desc = f"**{song.title}** - *{song.artist}*\n{song.album} ({song.duration_printable})"
        await __class__.msg(interaction, f"{interaction.user.display_name} added track to queue", desc)


    @staticmethod
    async def added_playlist_to_queue(interaction: discord.Interaction, playlist: Playlist) -> None:
        ''' Sends a message indicating the selected playlist was added to the queue '''
        desc = f"Source: **{playlist.name} ({playlist.song_count} tracks)**"
        await __class__.msg(interaction, f"{interaction.user.display_name} added playlist to queue", desc)


    @staticmethod
    async def set_autoplay_to_playlist(interaction: discord.Interaction, playlist: Playlist) -> None:
        ''' Sends a message indicating Autoplay was set to the selected playlist '''
        desc = f"**{playlist.name} ({playlist.song_count} tracks)**"
        await __class__.msg(interaction, f"{interaction.user.display_name} set the Autoplay mode to Playlist", desc)


    @staticmethod
    async def queue_cleared(interaction: discord.Interaction) -> None:
        ''' Sends a message indicating a user cleared the queue '''
        await __class__.msg(interaction, f"{interaction.user.display_name} cleared the queue")


    @staticmethod
    async def queue_empty(interaction: discord.Interaction) -> None:
        ''' Sends a message indicating that the queue is empty '''
        await __class__.msg(interaction, "Queue is empty!")


    @staticmethod
    async def skipping(interaction: discord.Interaction) -> None:
        ''' Sends a message indicating the current song was skipped '''
        await __class__.msg(interaction, "Skipped track")



class ErrMsg:
    ''' A class for sending error messages '''

    @staticmethod
    async def msg(interaction: discord.Interaction, message: str) -> None:
        ''' Generic message function. Creates an error message formatted as an embed '''
        embed = discord.Embed(color=discord.Color.orange(), title="Error", description=message)

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)


    @staticmethod
    async def user_not_in_voice_channel(interaction: discord.Interaction) -> None:
        ''' Sends an error message indicating user is not in a voice channel '''
        await __class__.msg(interaction, "You are not connected to a voice channel.")


    @staticmethod
    async def bot_not_in_voice_channel(interaction: discord.Interaction) -> None:
        ''' Sends an error message indicating bot is connect to a voice channel '''
        await __class__.msg(interaction, "Not currently connected to a voice channel.")


    @staticmethod
    async def cannot_connect_to_voice_channel(interaction: discord.Interaction) -> None:
        ''' Sends an error message indicating bot is unable to connect to a voice channel '''
        await __class__.msg(interaction, "Cannot connect to voice channel.")


    @staticmethod
    async def queue_is_empty(interaction: discord.Interaction) -> None:
        ''' Sends an error message indicating the queue is empty '''
        await __class__.msg(interaction, "Queue is empty.")


    @staticmethod
    async def already_playing(interaction: discord.Interaction) -> None:
        ''' Sends an error message indicating that music is already playing '''
        await __class__.msg(interaction, "Already playing.")


    @staticmethod
    async def not_playing(interaction: discord.Interaction) -> None:
        ''' Sends an error message indicating nothing is playing '''
        await __class__.msg(interaction, "No track is playing.")



# Misc UI methods
def get_thumbnail(thumbnail_path: str) -> discord.File:
        if thumbnail_path is not None:
            return discord.File(thumbnail_path, filename="image.png")
        else:
            return discord.utils.MISSING



# Methods for parsing data to Discord structures
def parse_search_as_track_selection_embed(results: list[Song], query: str, page_num: int) -> discord.Embed:
    ''' Takes search results obtained from the Subsonic API and parses them into a Discord embed suitable for track selection '''

    options_str = ""

    # Loop over the provided search results
    for song in results:

        # Trim displayed tags to fit neatly within the embed
        tr_title = song.title
        tr_artist = song.artist
        tr_album = (song.album[:68] + "...") if len(song.album) > 68 else song.album

        # Only trim the longest tag on the first line
        top_str_length = len(song.title + " - " + song.artist)
        if top_str_length > 71:
            
            if tr_title > tr_artist:
                tr_title = song.title[:(68 - top_str_length)] + '...'
            else:
                tr_artist = song.artist[:(68 - top_str_length)] + '...'

        # Add each of the results to our output string
        options_str += f"**{tr_title}** - *{tr_artist}* \n*{tr_album}* ({song.duration_printable})\n\n"

    # Return an embed that displays our output string
    embed = discord.Embed(color=discord.Color.orange(), title=f"Results for: {query}", description=options_str)
    embed.set_footer(text=f"Current page: {page_num}")
    return embed


def parse_search_as_track_selection_options(results: list[Song]) -> list[discord.SelectOption]:
    ''' Takes search results obtained from the Subsonic API and parses them into a Discord selection list for tracks '''

    select_options = []
    for i, song in enumerate(results):
        select_option = discord.SelectOption(label=f"{song.title}", description=f"by {song.artist}", value=i)
        select_options.append(select_option)

    return select_options


def parse_playlists_as_playlist_selection_embed(results: list[Playlist], page_num: int) -> discord.Embed:
    ''' Takes a playlist list obtained from the Subsonic API and parses them into a Discord embed suitable for playlist selection '''

    options_str = ""

    # Loop over the provided playlist list
    for playlist in results:

        # Trim displayed fields to fit neatly within the embed
        pl_name = (playlist.name[:68] + "...") if len(playlist.name) > 68 else playlist.name

        # Add each result to our output string
        options_str += f"**{pl_name}** ({playlist.duration_printable})\n{playlist.song_count} tracks\n\n"

    # Return an embed that displays our output string
    embed = discord.Embed(color=discord.Color.orange(), title=f"Available playlists:", description=options_str)
    embed.set_footer(text=f"Current page: {page_num}")
    return embed


def parse_playlists_as_playlist_selection_options(results: list[Playlist]) -> list[discord.SelectOption]:
    ''' Takes a playlist list obtained from the Subsonic API and parses them into a Discord selection list for tracks '''

    select_options = []
    for i, playlist in enumerate(results):
        select_option = discord.SelectOption(label=f"{playlist.name}", description=f"{playlist.song_count} tracks", value=i)
        select_options.append(select_option)

    return select_options


def parse_queue_as_embed(queue: list[Song], page_num: int, num_per_page: int) -> discord.Embed:
    ''' Takes part of a queue and parses it into a Discord embed suitable for playlist selection '''

    desc = ""

    for i, song in enumerate(queue):
        desc += f"{i+1+((page_num-1)*num_per_page)}. **{song.title}** - *{song.artist}*\n{song.album} ({song.duration_printable})\n\n"

    embed = discord.Embed(color=discord.Color.orange(), title="Queue", description=desc)
    embed.set_footer(text=f"Current page: {page_num}")

    return embed



def parse_elapsed_as_bar(elapsed: int, duration: int) -> str:
    ''' Parses track time information into a displayable bar. '''

    LENGTH = 17
    num_filled = max(int(math.ceil(min(elapsed, duration) / duration * LENGTH)) - 1, 0)

    return str("▰" * num_filled + "⚪" + "▱" * (LENGTH - num_filled - 1))
