spotify-backup
==============

> [!NOTE]  
> Forked it bc i got some erros with an normal (non-json) dump due to deleted songs, probably won't maintain any further. Love 2 the spotify API <3 (still missing 2fa tho)

A Python script that exports all of your Spotify playlists, useful for paranoid Spotify users like me, afraid that one day Spotify will go under and take all of our playlists with it!

To run the script, [save it from here](https://github.com/E1A/spotify-backup/raw/refs/heads/master/spotify-backup.py) and double-click it. It'll ask you for a filename and then pop open a web page so you can authorize access to the Spotify API. Then the script will load your playlists and save a tab-separated file with your playlists that you can open in Excel. You can even copy-paste the rows from Excel into a Spotify playlist.

You can run the script from the command line:

    python3 spotify-backup.py playlists.txt

or, to get a JSON dump, use:

    python3 spotify-backup.py playlists.json --format=json

By default, it includes your playlists. To include your Liked Songs, you can use:

    python3 spotify-backup.py playlists.txt --dump=liked,playlists


If for some reason the browser-based authorization flow doesn't work, you can also [generate an OAuth token](https://developer.spotify.com/web-api/console/get-playlists/) on the developer site (with the `playlist-read-private` permission) and pass it with the `--token` option.

Collaborative playlists and playlist folders don't show up in the API, sadly.
