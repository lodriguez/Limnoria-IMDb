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

    def __init__(self, irc):
        self.__parent = super(IMDb, self)
        self.__parent.__init__(irc)

    def createRoot(self, url):
        """opens the given url and creates the lxml.html root element"""

        # get headers from utils and create a referer
        ref = 'http://%s/%s' % (dynamic.irc.server, dynamic.irc.nick)
        headers = dict(utils.web.defaultHeaders)
        headers['Accept-Language'] = 'en-US; q=1.0, en; q=0.5'
        headers['Referer'] = ref

        # open url and create root
        pagefd = utils.web.getUrlFd(url,headers=headers)
        root = html.parse(pagefd)
        return root

    def imdbSearch(self,searchString):
        """searches the given stringh on imdb.com"""

        # create url for imdb.com search
        searchEncoded = utils.web.urlencode({'q' : searchString})
        url = 'https://www.imdb.com/find?&s=tt&' + searchEncoded

        root = self.createRoot(url)

        # parse root element for movie url
        element = root.findall('//td[@class="result_text"]/a')
        result = 'https://www.imdb.com' + element[0].attrib['href']

        # remove query string from url
        result = result[:result.find('?ref_')]

        return result

    def imdbPerson(self, persons):
        """gives a string of persons from imdb api json list or dict"""
        result = ''
        try:
            if isinstance(persons,(list,)):
                result = ', '.join([x['name'] for x in persons if x['@type'] == 'Person'])
            else:
                result = persons['name'] if persons['@type'] == 'Person' else False
        except:
            return False

        return result

    def isoTOhuman(self, duration):
        ### converts IMDb iso_8601 duration to a readable string ###
        result = ''
        for x in duration:
                 try:
                     int(x)
                     result = result + x
                 except:pass
                 if x == 'H':
                     result = result + 'hrs '
                 if x == 'M':
                     result = result + 'min'
        return result

    def imdbParse(self, url):
        """ parses given imdb site and creates a dict with usefull informations """
        root = self.createRoot(url)
        info = {}
        # create json object from "imdb api"
        imdb_jsn = root.xpath('//script[@type="application/ld+json"]')[0].text
        imdb_jsn = json.loads(imdb_jsn)

        # we can call that from outsite now, so we've to check it's actually a apge we can get usefull informatiosn from
        # maybe that should be an extra function, to make sure we got an imdb url...
        allowedTypes = [
            'TVSeries',
            'TVEpisode',
            'Movie',
            'VideoGame'
        ]

        if imdb_jsn['@type'] not in allowedTypes:
            return false

        # return function that are used with rules
        # to turn each xpath element into its final string
        def text(*args):
            def f(elem):
                elem = elem[0].text.strip()
                for s in args:
                    elem = elem.replace(s, '')
                return elem
            return f

        # Dictionary of rules for page scraping. has each xpath and a function to convert that element into its final string.
        # Each value is a tuple of tuples so that you can provide multiple sets of xpaths/functions for each piece of info.
        # They are tried In order until one works.
        #
        # Update: Removed most of it here, because the json should be a more reliable source
        # But title here is much nicer and there is no other way getting metascore ratings
        rules = {
            'title':    (('//head/title', text(' - IMDb')),),
            'metascore': (('//div[contains(@class, "metacriticScore")]//span', text()),)
        }

        # loop over the set of rules
        for title in rules:
            for xpath, f in rules[title]:
                elem = root.xpath(xpath)
                if elem:
                    info[title] = f(elem)
                    try: # this will replace some unicode characters with their equivalent ascii. makes life easier on everyone :)
                         # it's obviously only useful on unicode strings tho, so will TypeError if its a standard python2 string, or a python3 bytes
                        info[title] = unicodedata.normalize('NFKD', info[title])
                    except TypeError:
                        pass
                    break

        info['url'] = url
        # getting the data for the info dict from the json
        for key in ['name', '@type', 'contentRating', 'keywords', 'datePublished', 'duration']:
            if key in imdb_jsn: info[key] = imdb_jsn[key]
        # People lists can be a single dict or a list of dicts, that's what we use the imdbPerson function for
        for key in ['actor', 'director', 'creator']:
            if key in imdb_jsn: info[key] = self.imdbPerson(imdb_jsn[key])
        # could be a list or a string
        if 'genre' in imdb_jsn: info['genres'] = ", ".join(str(x) for x in imdb_jsn['genre']) if isinstance(imdb_jsn['genre'],(list,)) else imdb_jsn['genre']
        if 'aggregateRating' in imdb_jsn:
            info['rating'] = imdb_jsn['aggregateRating']['ratingValue']
            info['ratingCount'] = imdb_jsn['aggregateRating']['ratingCount']
        # Description also shows the actor in the first sentence, so we try to remove it. By splitting the Description after de first sentence.
        if 'description' in imdb_jsn:
            for i in reversed(imdb_jsn['actor']):
                try:
                    info['description'] = str(imdb_jsn['description']).split(str(i['name'] + ". "))[1]
                    break
                except:
                    info['description'] = str(imdb_jsn['description'])
                    continue
        if 'datePublished' in info: info['year'] = info['datePublished'][0:4]
        if 'duration' in info: info['runtime'] = self.isoTOhuman(info['duration'])
        return info

    def imdb(self, irc, msg, args, opts, text):
        """[--{short,full}] <movie>
        output info from IMDb about a movie"""

        # do a google search for movie on imdb and use first result
        query = 'site:http://www.imdb.com/title/ %s' % text
        search_plugin = irc.getCallback('google')

        if search_plugin:
            results = search_plugin.decode(search_plugin.search(query, msg.channel, irc.network))
            # use first result that ends with a / so that we know its link to main movie page
            for r in results:
                if r.link[-1] == '/':
                    imdb_url = r.link
                    break
        else:
            imdb_url = self.imdbSearch(text)

        try:
            imdb_url
        except NameError:
            irc.error('Couldn\'t find ' + ircutils.bold(text))
            return

        info = self.imdbParse(imdb_url)

        def reply(s): irc.reply(s, prefixNick=False)
        # getting optional parameter
        opts = dict(opts)
        # change orderoutput by optional parameter
        if 'short' in opts:
            outputorder = self.registryValue('shortoutputorder', msg.args[0])
        elif 'full' in opts:
            outputorder = self.registryValue('fulloutputorder', msg.args[0])
        else:
            outputorder = self.registryValue('outputorder', msg.args[0])

        # output based on order in config. lines are separated by ; and fields on a line separated by ,
        # each field has a corresponding format config
        for line in outputorder.split(';'):
            out = []
            for field in line.split(','):
                try:
                    out.append(self.registryValue('formats.'+field, msg.args[0]) % info)
                except KeyError:
                    continue
            if out:
                reply(' '.join(out))

    imdb = wrap(imdb, [getopts({'short':'','full':''}), 'text'])

Class = IMDb

# vim:set shiftwidth=4 softtabstop=4 expandtab:
