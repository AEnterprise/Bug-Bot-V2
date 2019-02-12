import re

from discord.ext.commands import Converter, BadArgument

from Utils.DataUtils import Bug

URL_MATCHER = re.compile(r'^((?:https?://)[a-z0-9]+(?:[-.][a-z0-9]+)*\.[a-z]{2,5}(?::[0-9]{1,5})?(?:/[^ \n<>()]*)?)$',
                         re.IGNORECASE)


class Link(Converter):
    async def convert(self, ctx, argument):
        match = URL_MATCHER.match(argument)
        if match is None:
            raise BadArgument("Not A Link")
        return argument


class BugReport(Converter):
    async def convert(self, ctx, argument):
        if argument.isnumeric():
            bug = Bug.get_or_none(id=argument)
        else:
            search = re.search(r'https?://trello\.com/c/(\w+)', argument)
            if search:
                shortlink = search.group(1)
            else:
                shortlink = argument
            bug = Bug.get_or_none(trello_id=shortlink)
        if bug is None:
            raise BadArgument(f'Report "{argument}" not found')
        return bug