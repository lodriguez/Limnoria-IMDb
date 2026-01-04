###
# Copyright (c) 2026, lod
# All rights reserved.
#
#
###

import re
import json
from lxml import html

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

class IMDb(callbacks.Plugin):
    threaded = True
    regexps = ['imdbSnarfer']

    FILTER_MAP = {
        'movie': 'ft', 'tv': 'tv', 'game': 'vg',
        'episode': 'ep', 'music': 'mu', 'podcast': 'ps'
    }

    def _get_root(self, url):
        headers = dict(utils.web.defaultHeaders)
        headers.update({'Accept-Language': 'en-US, en;q=0.5', 'Referer': url})
        try:
            return html.parse(utils.web.getUrlFd(url, headers=headers))
        except Exception as e:
            self.log.error(f"IMDb fetch error: {e}")
            return None

    def _reply(self, irc, channel, info, mode):
        """Unified reply function."""
        outputorder = self.registryValue(mode, channel)

        for line in outputorder.split(';'):
            out = []
            for field in line.split(','):
                if info.get(field):
                    try:
                        out.append(self.registryValue(f'formats.{field}', channel) % info)
                    except (KeyError, ValueError):
                        continue
            if out:
                irc.reply(' '.join(out), prefixNick=False)

    def imdbSearch(self, query, search_filter=None):
        """searches the given stringh on imdb.com/find """
        params = {'q': query, 's': 'tt'}
        if search_filter in self.FILTER_MAP:
            params['ttype'] = self.FILTER_MAP[search_filter]

        url = f"https://www.imdb.com/find?{utils.web.urlencode(params)}"

        root = self._get_root(url)

        try:
            href = root.xpath('.//a[contains(@class, "ipc-lockup-overlay")]/@href')[0]
            return f"https://www.imdb.com{href}".split('?')[0]
        except (IndexError, AttributeError):
            return None

    def imdbParse(self, url):
        """ parses given imdb site and creates a dict with usefull informations """
        root = self._get_root(url)
        info = {}

        imdb_json = root.xpath('//script[@id="__NEXT_DATA__"]/text()')
        if not imdb_json:
            return False

        try:
            data = json.loads(imdb_json[0])
            entry = data['props']['pageProps']['aboveTheFoldData']
        except (json.JSONDecodeError, KeyError):
            return None

        def sg(obj, path):
            """Safe-get helper for nested dicts."""
            for key in path:
                obj = obj.get(key) if isinstance(obj, dict) else None
            return obj

        info['url'] = url
        info['title'] = sg(entry, ['titleText', 'text'])
        info['type'] = sg(entry, ['titleType', 'text'])
        info['year'] = sg(entry, ['releaseYear', 'year'])
        info['description'] = sg(entry, ['plot', 'plotText', 'plainText'])
        info['rating'] = sg(entry, ['ratingsSummary', 'aggregateRating'])
        info['ratingCount'] = sg(entry, ['ratingsSummary', 'voteCount'])
        info['contentRating'] = sg(entry, ['certificate', 'rating'])
        info['metascore'] = sg(entry, ['metacritic', 'metascore', 'score'])

        genres = sg(entry, ['genres', 'genres'])
        if genres:
            info['genres'] = ", ".join([g['text'] for g in genres if g.get('text')])

        keywords = sg(entry, ['keywords', 'edges'])
        if keywords:
            info['keywords'] = ", ".join([sg(k, ['node', 'text']) for k in keywords if sg(k, ['node', 'text'])])

        seconds = sg(entry, ['runtime', 'seconds'])
        if seconds:
            h, m = divmod(seconds, 3600)
            info['runtime'] = f"{h}h {m//60}m" if h else f"{m//60}m"

        for group in entry.get('principalCreditsV2', []):
            label = sg(group, ['grouping', 'text']).lower()
            names = [c.get('name', {}).get('nameText', {}).get('text') for c in group.get('credits', [])]
            names = [c['name']['nameText']['text'] for c in group.get('credits', []) if sg(c, ['name', 'nameText', 'text'])]
            names = ", ".join(filter(None, names))

            if 'director' in label: info['director'] = names
            elif 'writer' in label: info['writer'] = names
            elif 'star' in label or 'actor' in label: info['actor'] = names

        return info

    def doPrivmsg(self, irc, msg):
        channel = msg.args[0]
        if not self.registryValue('enableFetcher', channel):
            return

        match = re.search(r'(?:www\.)?imdb\.com/(?:[a-z]{2}/)?title/(tt\d+)/?', msg.args[1], re.I)
        if match:
            info = self.imdbParse(f"https://www.imdb.com/title/{match.group(1)}/")
            if info:
                self._reply(irc, channel, info, 'snarfoutputorder')

    def imdb(self, irc, msg, args, opts, text):
        """[--short|--full] [--tv|--movie|--game|--episode|--music|--podcast] <title>
        output info from IMDb about a entry"""
        mode = 'outputorder'
        search_filter = None

        for (opt, _) in opts:
            if opt == 'short': mode = 'shortoutputorder'
            elif opt == 'full': mode = 'fulloutputorder'
            elif opt in self.FILTER_MAP: search_filter = opt

        imdb_url = self.imdbSearch(text, search_filter)
        if not imdb_url::
            irc.error(f"No results found for {text}")
            return

        info = self.imdbParse(imdb_url)
        if info:
            self._reply(irc, msg.args[0], info, mode)
        else:
            irc.error("Error parsing IMDb data.")

    imdb = wrap(imdb, [getopts({
        'short':'', 'full':'', 'tv':'', 'movie':'', 
        'game':'', 'episode':'', 'music':'', 'podcast':''
    }), 'text'])

Class = IMDb

# vim:set shiftwidth=4 softtabstop=4 expandtab:
