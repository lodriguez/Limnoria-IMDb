###
# Copyright (c) 2020, lod
# All rights reserved.
#
#
###
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

import re
import sys
import json
import unicodedata
import datetime
from lxml import html

if sys.version_info[0] >= 3:
    def u(s):
        return s
else:
    def u(s):
        return unicode(s, "unicode_escape")

class IMDb(callbacks.Plugin):
    """Add the help for "@plugin help IMDb" here
    This should describe *how* to use this plugin."""
    threaded = True
    regexps = ['imdbSnarfer']

    def __init__(self, irc):
        self.__parent = super(IMDb, self)
        self.__parent.__init__(irc)

    def _reply(self, irc, channel, info, mode):
        """
        Unified reply function. 
        """
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

        
    def doPrivmsg(self, irc, msg):
        channel = msg.args[0]
        # Only fetch if enableFetcher is True and the bot wasn't directly addressed
        if not self.registryValue('enableFetcher', channel) or callbacks.addressed(irc.nick, msg):
            return
        
        match = re.search(r'(?:www\.)?imdb\.com/(?:[a-z]{2}/)?title/(tt\d+)/?', msg.args[1], re.I)
        if match:
            info = self.imdbParse(f"https://www.imdb.com/title/{match.group(1)}/")
            if info:
                self._reply(irc, channel, info, 'snarfoutputorder')

    def createRoot(self, url):
        """opens the given url and creates the lxml.html root element"""

        ref = 'http://%s/%s' % (dynamic.irc.server, dynamic.irc.nick)
        headers = dict(utils.web.defaultHeaders)
        headers['Accept-Language'] = 'en-US; q=1.0, en; q=0.5'
        headers['Referer'] = ref

        pagefd = utils.web.getUrlFd(url,headers=headers)
        root = html.parse(pagefd)
        return root

    def imdbSearch(self,searchString):
        """searches the given stringh on imdb.com"""

        searchEncoded = utils.web.urlencode({'q' : searchString})
        url = 'https://www.imdb.com/find?&s=tt&' + searchEncoded

        root = self.createRoot(url)

        element = root.xpath('.//a[contains(@class, "ipc-lockup-overlay")]')[0]
        result = "https://www.imdb.com" + element.attrib["href"]

        result = result.split("?")[0]

        return result

    def imdbPerson(self, persons):
        """gives a string of persons from imdb ap;i json list or dict"""
        result = ''
        try:
            if isinstance(persons,(list,)):
                result = ', '.join([x['name'] for x in persons if x['@type'] == 'Person'])
            else:
                result = persons['name'] if persons['@type'] == 'Person' else False
        except:
            return False

        return result

    def imdbParse(self, url):
        """ parses given imdb site and creates a dict with usefull informations """
        root = self.createRoot(url)
        info = {}

        imdb_jsn_raw = root.xpath('//script[@id="__NEXT_DATA__"]/text()')
        if not imdb_jsn_raw:
            return False

        imdb_jsn = json.loads(imdb_jsn_raw[0])

        movie = imdb_jsn.get('props', {}).get('pageProps', {}).get('aboveTheFoldData', {})
        if not movie:
            return False

        info['url'] = url
        info['title'] = movie.get('titleText', {}).get('text') 
        info['@type'] = movie.get('titleType', {}).get('text')
        info['contentRating'] = (movie.get('certificate') or {}).get('rating')
        info['metascore'] = (movie.get('metacritic') or {}).get('metascore', {}).get('score')
        info['rating'] = movie.get('ratingsSummary', {}).get('aggregateRating')
        info['ratingCount'] = movie.get('ratingsSummary', {}).get('voteCount')
        info['description'] = movie.get('plot', {}).get('plotText', {}).get('plainText')
        info['genres'] = ", ".join([g.get('text') for g in movie.get('genres', {}).get('genres', [])])
        info['keywords'] = ", ".join([k.get('node', {}).get('text') for k in movie.get('keywords', {}).get('edges', [])])
        info['year'] = movie.get('releaseYear', {}).get('year')

        duration = movie.get('runtime', {}) or {}
        duration = duration.get('seconds')
        if duration:
            hours =  duration // 3600
            minutes = (duration % 3600) // 60
            if hours > 0:
                info['runtime'] = f"{hours}h {minutes}m"
            else:
                info['runtime'] = f"{minutes}m"

        credits = movie.get('principalCreditsV2', [])
        for group in credits:
            label = group.get('grouping', {}).get('text', '').lower()
            names = [c.get('name', {}).get('nameText', {}).get('text') for c in group.get('credits', [])]

            names = ", ".join(filter(None, names))

            if 'director' in label:
                info['director'] = names
            elif 'writer' in label:
                info['writer'] = names
            elif 'star' in label:
                info['actor'] = names

        return info

    def imdb(self, irc, msg, args, opts, text):
        """[--{short,full}] <movie>
        output info from IMDb about a movie"""
        mode = 'outputorder'
        
        for (opt, _) in opts:
            if opt == 'short': mode = 'shortoutputorder'
            elif opt == 'full': mode = 'fulloutputorder'
        
        try:
            imdb_url = self.imdbSearch(text)
        except NameError:
            irc.error('Couldn\'t find ' + ircutils.bold(text))
            return

        info = self.imdbParse(imdb_url)
        if info:
            self._reply(irc, msg.args[0], info, mode)
        else:
            irc.error("Error parsing IMDb data.")

    imdb = wrap(imdb, [getopts({'short':'','full':''}), 'text'])

Class = IMDb
