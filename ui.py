''' For complex UI-related tasks '''

import discord

import asyncio
import data
import subsonic
import logging

logger = logging.getLogger(__name__)


class SysMsg:
    ''' A class for sending system messages '''

    @staticmethod
    async def msg(interaction: discord.Interaction, header: str, message: str=None,
                   thumbnail: str=None, standalone: bool=False) -> None:
        ''' Generic message function. Creates and sends message formatted as an embed '''

        embed = discord.Embed(color=discord.Color.orange(), title=header, description=message)
        embed.set_thumbnail(url="attachment://image.png")

        def get_thumbnail() -> discord.File:
            # Attach a thumbnail if one was provided (as a local file)
            if thumbnail is not None:
                return discord.File(thumbnail, filename="image.png")
            else:
                return discord.utils.MISSING
            
        # Handle standalone messages
        if (standalone):
            await interaction.channel.send(file=get_thumbnail(), embed=embed)
            return

        # Send the system message (accounting for race conditions/timeout)
        try:
            # Try an immediate send, but timeout if it's too slow so we can attempt to defer in time
            await asyncio.wait_for((
                interaction.response.send_message(file=get_thumbnail(), embed=embed) if not interaction.response.is_done()
                else interaction.followup.send(file=get_thumbnail(), embed=embed)), timeout=1.5
            )
        except (asyncio.TimeoutError, discord.InteractionResponded, discord.NotFound, discord.HTTPException):
            # Defer if possible and then send a proper followup
            if not interaction.response.is_done():
                try:
                    await interaction.response.defer()
                except (discord.NotFound, discord.InteractionResponded):
                    pass

            # Finally try to send the message again
            try:
                await interaction.followup.send(file=get_thumbnail(), embed=embed)
            except (discord.NotFound, discord.InteractionResponded):
                logger.warning("Follow-up message could not be properly sent, sending as a standalone message instead.")
                await interaction.channel.send(file=get_thumbnail(), embed=embed)


    @staticmethod
    async def playing(interaction: discord.Interaction, standalone: bool=True) -> None:
        ''' Sends a message containing the currently playing song '''
        player = data.guild_data(interaction.guild_id).player
        song = player.current_song
        cover_art = subsonic.get_album_art_file(song.cover_id)
        desc = f"**{song.title}** - *{song.artist}*\n{song.album} ({song.duration_printable})"
        await __class__.msg(interaction, header="Playing:", message=desc, thumbnail=cover_art, standalone=standalone)


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
    async def added_to_queue(interaction: discord.Interaction, song: subsonic.Song) -> None:
        ''' Sends a message indicating the selected song was added to queue '''
        desc = f"**{song.title}** - *{song.artist}*\n{song.album} ({song.duration_printable})"
        await __class__.msg(interaction, f"{interaction.user.display_name} added track to queue", desc)


    @staticmethod
    async def queue_cleared(interaction: discord.Interaction) -> None:
        ''' Sends a message indicating a user cleared the queue '''
        await __class__.msg(interaction, f"{interaction.user.display_name} cleared the queue")


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



# Methods for parsing data to Discord structures
def parse_search_as_track_selection_embed(results: list[subsonic.Song], query: str, page_num: int) -> discord.Embed:
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

    # Add the current page number to our results
    options_str += f"Current page: {page_num}"

    # Return an embed that displays our output string
    return discord.Embed(color=discord.Color.orange(), title=f"Results for: {query}", description=options_str)


def parse_search_as_track_selection_options(results: list[subsonic.Song]) -> list[discord.SelectOption]:
    ''' Takes search results obtained from the Subsonic API and parses them into a Discord selection list for tracks '''

    select_options = []
    for i, song in enumerate(results):
        select_option = discord.SelectOption(label=f"{song.title}", description=f"by {song.artist}", value=i)
        select_options.append(select_option)

    return select_options
