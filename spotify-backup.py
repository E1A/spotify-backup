#!/usr/bin/env python3

import argparse
import codecs
import http.client
import http.server
import json
import logging
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

logging.basicConfig(level=20, datefmt='%I:%M:%S', format='[%(asctime)s] %(message)s')


class SpotifyAPI:
    def __init__(self, auth):
        self._auth = auth

    def get(self, url, params={}, tries=3):
        if not url.startswith('https://api.spotify.com/v1/'):
            url = 'https://api.spotify.com/v1/' + url
        if params:
            url += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)

        for _ in range(tries):
            try:
                req = urllib.request.Request(url)
                req.add_header('Authorization', 'Bearer ' + self._auth)
                res = urllib.request.urlopen(req)
                reader = codecs.getreader('utf-8')
                return json.load(reader(res))
            except Exception as err:
                logging.info('Couldn\'t load URL: {} ({})'.format(url, err))
                time.sleep(2)
                logging.info('Trying again...')
        sys.exit(1)

    def list(self, url, params={}):
        last_log_time = time.time()
        response = self.get(url, params)
        items = response['items']

        while response['next']:
            if time.time() > last_log_time + 15:
                last_log_time = time.time()
                logging.info(f"Loaded {len(items)}/{response['total']} items")
            response = self.get(response['next'])
            items += response['items']
        return items

    @staticmethod
    def authorize(client_id, scope):
        url = 'https://accounts.spotify.com/authorize?' + urllib.parse.urlencode({
            'response_type': 'token',
            'client_id': client_id,
            'scope': scope,
            'redirect_uri': 'http://127.0.0.1:{}/redirect'.format(SpotifyAPI._SERVER_PORT)
        })
        logging.info(f'Logging in (click if it doesn\'t open automatically): {url}')
        webbrowser.open(url)

        server = SpotifyAPI._AuthorizationServer('127.0.0.1', SpotifyAPI._SERVER_PORT)
        try:
            while True:
                server.handle_request()
        except SpotifyAPI._Authorization as auth:
            return SpotifyAPI(auth.access_token)

    _SERVER_PORT = 43019

    class _AuthorizationServer(http.server.HTTPServer):
        def __init__(self, host, port):
            http.server.HTTPServer.__init__(self, (host, port), SpotifyAPI._AuthorizationHandler)

        def handle_error(self, request, client_address):
            raise

    class _AuthorizationHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith('/redirect'):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<script>location.replace("token?" + location.hash.slice(1));</script>')
            elif self.path.startswith('/token?'):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<script>close()</script>Thanks! You may now close this window.')
                access_token = re.search('access_token=([^&]*)', self.path).group(1)
                logging.info(f'Received access token from Spotify: {access_token}')
                raise SpotifyAPI._Authorization(access_token)
            else:
                self.send_error(404)

        def log_message(self, format, *args):
            pass

    class _Authorization(Exception):
        def __init__(self, access_token):
            self.access_token = access_token


def main():
    parser = argparse.ArgumentParser(description='Exports your Spotify playlists.')
    parser.add_argument('--token', metavar='OAUTH_TOKEN', help='use a Spotify OAuth token')
    parser.add_argument('--dump', default='playlists', choices=['liked,playlists', 'playlists,liked', 'playlists', 'liked'],
                        help='dump playlists or liked songs, or both (default: playlists)')
    parser.add_argument('--format', default='txt', choices=['json', 'txt'], help='output format (default: txt)')
    parser.add_argument('file', help='output filename', nargs='?')
    args = parser.parse_args()

    while not args.file:
        args.file = input('Enter a file name (e.g. playlists.txt): ')
        args.format = args.file.split('.')[-1]

    if args.token:
        spotify = SpotifyAPI(args.token)
    else:
        spotify = SpotifyAPI.authorize(
            client_id='5c098bcc800e45d49e476265bc9b6934',
            scope='playlist-read-private playlist-read-collaborative user-library-read'
        )

    logging.info('Loading user info...')
    me = spotify.get('me')
    logging.info('Logged in as {display_name} ({id})'.format(**me))

    playlists = []
    liked_albums = []

    if 'liked' in args.dump:
        logging.info('Loading liked albums and songs...')
        liked_tracks = spotify.list('me/tracks', {'limit': 50})
        liked_albums = spotify.list('me/albums', {'limit': 50})
        playlists += [{'name': 'Liked Songs', 'tracks': liked_tracks}]

    if 'playlists' in args.dump:
        logging.info('Loading playlists...')
        playlist_data = spotify.list('users/{user_id}/playlists'.format(user_id=me['id']), {'limit': 50})
        logging.info(f'Found {len(playlist_data)} playlists')

        for playlist in playlist_data:
            logging.info('Loading playlist: {name} ({tracks[total]} songs)'.format(**playlist))
            playlist['tracks'] = spotify.list(playlist['tracks']['href'], {'limit': 100})
        playlists += playlist_data

    logging.info('Writing files...')
    with open(args.file, 'w', encoding='utf-8') as f:
        if args.format == 'json':
            json.dump({
                'playlists': playlists,
                'albums': liked_albums
            }, f, indent=2)
        else:
            f.write('Playlists: \r\n\r\n')
            for playlist in playlists:
                f.write(playlist['name'] + '\r\n')
                for track in playlist['tracks']:
                    try:
                        t = track['track']
                        if not t:
                            continue
                        artists = ', '.join([
                            artist.get('name', 'Unknown') for artist in t.get('artists', [])
                        ])
                        album_info = t.get('album', {})
                        f.write('{name}\t{artists}\t{album}\t{uri}\t{release_date}\r\n'.format(
                            name=t.get('name', 'Unknown'),
                            artists=artists,
                            album=album_info.get('name', 'Unknown'),
                            uri=t.get('uri', 'Unknown'),
                            release_date=album_info.get('release_date', 'Unknown')
                        ))
                    except Exception as e:
                        logging.warning(f'Skipping track due to error: {e}')
                        continue
                f.write('\r\n')
            if liked_albums:
                f.write('Liked Albums: \r\n\r\n')
                for album in liked_albums:
                    a = album['album']
                    uri = a.get('uri', 'Unknown')
                    name = a.get('name', 'Unknown')
                    artists = ', '.join([artist.get('name', 'Unknown') for artist in a.get('artists', [])])
                    release_date = a.get('release_date', 'Unknown')
                    f.write(f'{name}\t{artists}\t-\t{uri}\t{release_date}\r\n')

    logging.info('Wrote file: ' + args.file)


if __name__ == '__main__':
    main()
