'''For complex UI-related tasks'''

import discord

import data

from subsonic import Song

# For sending generic system messages
class SysMsg():
    async def msg(interaction: discord.Interaction, header: str, message: str=None) -> None:
        embed = discord.Embed(color=discord.Color.orange(), title=header, description=message)
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

    async def playing(cls, interaction: discord.Interaction) -> None:
        song = data.GuildData.current_song
        await cls.msg(interaction, "Playing", f"**{song.title}** - *{song.artist}*")

    @classmethod
    async def playback_ended(cls, interaction: discord.Interaction) -> None:
        await cls.msg(interaction, "Playback ended")
    
    @classmethod
    async def disconnected(cls, interaction: discord.Interaction) -> None:
        await cls.msg(interaction, "Disconnected from voice channel")

    @classmethod
    async def starting_queue_playback(cls, interaction: discord.Interaction) -> None:
        await cls.msg(interaction, "Started queue playback")

    @classmethod
    async def added_to_queue(cls, interaction: discord.Interaction, song: Song) -> None:
        desc = f"**{song.title}** - *{song.artist}*\n{song.album} ({song.duration_printable})"
        await cls.msg(interaction, f"{interaction.user.display_name} added track to queue", desc)
    
    @classmethod
    async def queue_cleared(cls, interaction: discord.Interaction) -> None:
        await cls.msg(interaction, f"{interaction.user.display_name} cleared the queue")
    
    @classmethod
    async def skipping(cls, interaction: discord.Interaction) -> None:
        await cls.msg(interaction, "Skipped track")


# For sending standard error messages
class ErrMsg():
    async def msg(interaction: discord.Interaction, message: str) -> None:
        embed = discord.Embed(color=discord.Color.orange(), title="Error", description=message)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @classmethod
    async def user_not_in_voice_channel(cls, interaction: discord.Interaction) -> None:
        await cls.msg(interaction, "You are not connected to a voice channel.")

    @classmethod
    async def bot_not_in_voice_channel(cls, interaction: discord.Interaction) -> None:
        await cls.msg(interaction, "Not currently connected to a voice channel.")

    @classmethod
    async def cannot_connect_to_voice_channel(cls, interaction: discord.Interaction) -> None:
        await cls.msg(interaction, "Cannot connect to voice channel.")

    @classmethod
    async def queue_is_empty(cls, interaction: discord.Interaction) -> None:
        await cls.msg(interaction, "Queue is empty.")

    @classmethod
    async def already_playing(cls, interaction: discord.Interaction) -> None:
        await cls.msg(interaction, "Already playing.")
    
    @classmethod
    async def not_playing(cls, interaction: discord.Interaction) -> None:
        await cls.msg(interaction, "No track is playing.")



# Methods for parsing data to an embed
def parse_search_as_track_selection_embed(results: list[Song], query: str, page_num: int) -> discord.Embed:
    ''' Takes search results obtained from the Subsonic API and parses them into a Discord embed suitable for track selection'''

    options_str = ""

    # Loop over the provided search results
    for song in results:

        # Trim displayed tags to fit neatly within the embed
        tr_title = song.title
        tr_artist = song.artist
        tr_album = (song.album[:68] + '...') if len(song.album) > 68 else song.album

        # Only trim the longest tag on the first line
        top_str_length = len(song.title + ' - ' + song.artist)
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


def parse_search_as_track_selection_options(results: list[Song]) -> list[discord.SelectOption]:
    ''' Takes search results obtained from the Subsonic API and parses them into a Discord selection list for tracks'''

    select_options = []
    for i, song in enumerate(results):
        select_option = discord.SelectOption(label=f"{song.title}", description=f"by {song.artist}", value=i)
        select_options.append(select_option)

    return select_options
