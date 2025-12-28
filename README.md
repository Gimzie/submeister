# Submeister
A powerful Discord bot that streams music from your personal Subsonic server.

##  Features
- Full playback support for any Subsonic API-compatible server (Navidrome, Nextcloud Music, etc.)
- Dynamically updating now-playing widget which prevents getting buried by messages
- Searching for and queuing albums (soon) & playlists from the server
- Autoplay support, supporting random & similar modes, as well as sourcing from albums or playlists

## Usage
Clone the repository and rename `data.env.example` to `data.env`, filling out each field as necessary. If you do not have a Discord application created already, you must create one on the [developer portal](https://discord.com/developers/applications) first. Currently, only password authentication is supported for connecting to a Subsonic server.

A Dockerfile (WIP) is provided for easy usage. For manual use, a command such as `nohup python3 submeister.py > output.log 2>&1 &` may be used instead.

## Commands
A list of supported commands. More accurate information may be available through the bot itself.
| Command | Description |
|----------|----------|
| **/play**  | Joins a voice channel and starts playing from the queue or autoplay. Optionally allows specifying a track to search and play. |
| **/stop**    | Stops playback and disconnects from the voice channel.     |
| **/skip**    | Skips the current track.     |
| **/now-playing**    | Sends a message displaying the now-playing widget. This widget is automatically updated without needing to use this command.     |
| **/show-queue**    | Displays the playback queue. The queue is always played first, falling back to Autoplay when it is empty (if enabled).  |
| **/clear-queue**    | Clears the playback queue. Autoplay will not be disabled if in-use.     |
| **/search**    | Performs a search for a specified track. Searches title, artist, and album fields.     |
| **/playlists** | Displays a paged list of playlists found on the server. Allows selecting a playlist to either queue or use as an Autoplay source.     |
| **/autoplay**    | Selects the Autoplay mode (None, Similar, or Random).     |

## Roadmap
Additional features are planned, including:
- Searching for and queuing up albums
- Searching for specific playlists
- Automatically disconnecting from the voice channel after a period of inactivity
- Clearing album cover cache periodically based on specified count or timeframe
- Uploading your own audio files to queue
- Queuing audio from YouTube, Soundcloud, etc.
