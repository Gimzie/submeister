'''For complex UI-related tasks'''

import discord

def ensure_song_has_displayable_tags(song: dict) -> dict:
    ''' Takes a song object that was returned from the Subsonic API and ensures all necessary tag keys are present on the object '''

    # Ensure title tag is present
    if 'title' not in song:
        song['title'] = "Unknown Track"

    # Ensure artist tag is present, and trim it to fit
    if 'artist' not in song:
        song['artist'] = "Unknown Artist"

    # Ensure album tag is present, and trim it to fit
    if 'album' not in song:
        song['album'] = "Unknown Album"

    # Ensure duration is present, and format it properly (minutes:seconds)
    if 'duration' not in song:
        song['duration'] = "00:00"
    else:
        song['duration'] = f"{(song['duration'] // 60):02d}:{(song['duration'] % 60):02d}"

    return song


def parse_search_as_track_selection_embed(results: list, query: str, page_num: int) -> discord.Embed:
    ''' Takes search results obtained from the Subsonic API and parses them into a Discord embed suitable for track selection'''

    options_str = ""

    # Loop over the provided search results
    for song in results:

        # Ensure required tags are present for all songs
        song = ensure_song_has_displayable_tags(song)

        # Trim displayed tags to fit neatly within the embed
        tr_title = song["title"]
        tr_artist = song["artist"]
        tr_album = (song["album"][:68] + '...') if len(song["album"]) > 68 else song["album"]

        # Only trim the longest tag on the first line
        top_str_length = len(song['title'] + ' - ' + song["artist"])
        if top_str_length > 71:

            if tr_title > tr_artist:
                tr_title = song["title"][:(68 - top_str_length)] + '...'
            else:
                tr_artist = song["artist"][:(68 - top_str_length)] + '...'

        # Add each of the results to our output string
        options_str += f"**{tr_title}** - *{tr_artist}* \n*{tr_album}* ({song['duration']})\n\n"

    # Add the current page number to our results
    options_str += f"Current page: {page_num}"

    # Return an embed that displays our output string
    return discord.Embed(color=discord.Color.orange(), title=f"Results for: {query}", description=options_str)


def parse_search_as_track_selection_options(results: dict) -> list:
    ''' Takes search results obtained from the Subsonic API and parses them into a Discord selection list for tracks'''

    select_options = []
    for i, song in enumerate(results):
        select_option = discord.SelectOption(label=f"{song['title']}", description=f"by {song['artist']}", value=i)
        select_options.append(select_option)

    return select_options
