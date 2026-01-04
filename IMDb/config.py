###
# Copyright (c) 2026, lod
# All rights reserved.
#
#
###

import supybot.conf as conf
import supybot.registry as registry
import supybot.ircutils as ircutils

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('IMDb', True)


IMDb = conf.registerPlugin('IMDb')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(IMDb, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))

conf.registerGroup(IMDb, 'formats')

conf.registerChannelValue(IMDb, 'enableFetcher',
        registry.Boolean(True, """Enable or disable the IMDB URL fetcher."""))

conf.registerChannelValue(IMDb, 'shortoutputorder',
        registry.String('title,type,year,runtime,contentrating,rating,ratingcount,metascore,url',
            'Order that parts will be output. ; is line separator and , is field separator'))

conf.registerChannelValue(IMDb, 'outputorder',
        registry.String('title,type,year,runtime,contentrating,rating,ratingcount,metascore,url;description,genres,keywords',
            'Order that parts will be output. ; is line separator and , is field separator'))

conf.registerChannelValue(IMDb, 'fulloutputorder',
        registry.String('title,type,year,url;runtime,contentrating,rating,ratingcount,metascore;description;director,writer,actor;genres,keywords',
            'Order that parts will be output. ; is line separator and , is field separator'))

conf.registerChannelValue(IMDb, 'snarfoutputorder',
        registry.String('title,type,year,runtime,rating,ratingcount,genres,actor,description',
            'Order that parts will be output. ; is line separator and , is field separator'))

conf.registerChannelValue(IMDb.formats, 'url',
        registry.String('%(url)s', 'Format for the output of imdb command'))

conf.registerChannelValue(IMDb.formats, 'title',
        registry.String(ircutils.bold('%(title)s'), 'Format for the output of imdb command'))

conf.registerChannelValue(IMDb.formats, 'year',
        registry.String('%(year)s', 'Format for the output of imdb command'))

conf.registerChannelValue(IMDb.formats, 'type',
        registry.String('(%(type)s)', 'Format for the output of imdb command'))

conf.registerChannelValue(IMDb.formats, 'description',
        registry.String(ircutils.bold('Description:') + ' %(description)s', 'Format for the output of imdb command'))

conf.registerChannelValue(IMDb.formats, 'writer',
        registry.String(ircutils.bold('Writer:') + ' %(writer)s', 'Format for the output of imdb command'))

conf.registerChannelValue(IMDb.formats, 'director',
        registry.String(ircutils.bold('Director:') + ' %(director)s', 'Format for the output of imdb command'))

conf.registerChannelValue(IMDb.formats, 'actor',
        registry.String(ircutils.bold('Actors:') + ' %(actor)s', 'Format for the output of imdb command'))

conf.registerChannelValue(IMDb.formats, 'genres',
        registry.String(ircutils.bold('Genres:') + ' %(genres)s', 'Format for the output of imdb command'))

conf.registerChannelValue(IMDb.formats, 'keywords',
        registry.String(ircutils.bold('Keywords:') + ' %(keywords)s', 'Format for the output of imdb command'))

conf.registerChannelValue(IMDb.formats, 'runtime',
        registry.String(ircutils.bold('Runtime:') + ' %(runtime)s', 'Format for the output of imdb command'))

conf.registerChannelValue(IMDb.formats, 'language',
        registry.String(ircutils.bold('Language:') + ' %(language)s', 'Format for the output of imdb command'))

conf.registerChannelValue(IMDb.formats, 'contentrating',
        registry.String(ircutils.bold('Content Rating:') + ' %(contentRating)s', 'Format for the output of imdb command'))

conf.registerChannelValue(IMDb.formats, 'rating',
        registry.String(ircutils.bold('IMDb:') + ' %(rating)s/10', 'Format for the output of imdb command'))

conf.registerChannelValue(IMDb.formats, 'ratingcount',
        registry.String('(%(ratingCount)s votes)', 'Format for the output of imdb command'))

conf.registerChannelValue(IMDb.formats, 'metascore',
        registry.String(ircutils.bold('Metacritic:') + ' %(metascore)s/100', 'Format for the output of imdb command'))

