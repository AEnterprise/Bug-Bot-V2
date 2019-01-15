import re
import asyncio

import discord
from discord.ext import commands

import BugBot
from Utils import Configuration, RedisListener, BugBotLogging

from Utils import BugBotLogging, Configuration, Utils, Checks, Emoji
from Utils.DataUtils import Storeinfo, Bug
from Utils.Enums import Platforms, ReportSource, ReportError


def platform_convert(platform):
    if platform.lower() == '-w':
        return [Platforms.desktop, '-w']
    elif platform.lower() == '-m':
        return [Platforms.mac, '-m']
    elif platform.lower() == '-i':
        return [Platforms.ios, '-i']
    elif platform.upper() == '-L':
        return [Platforms.linux, '-L']
    elif platform.lower() == '-a':
        return [Platforms.android, '-a']


class BugReportException(Exception):
    def __init__(self, code, msg=''):
        super().__init__(msg)
        self.code = code
        self.msg = msg


class BugReporting:
    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(RedisListener.initialize(bot.loop, "web_to_bot", "bot_to_web", self.process_report, BugBot.handle_exception))

    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return
        if message.channel.id not in Configuration.list_of_bugchannels_ids():
            return
        ctx = await self.bot.get_context(message)
        if ctx.command is None:
            await message.channel.send(Configuration.get_var('strings', 'NON_COMMANDS_MSG').format(user=message.author.mention), delete_after=5)
            await asyncio.sleep(5)
            await message.delete()

    async def _forbiden_msg_log(self, ctx):
        await BugBotLogging.bot_log(f":warning: {ctx.author} (`{ctx.author.id}`) tried to execute {ctx.prefix}{ctx.command} in {ctx.channel.mention} but I was unable to DM them their stored information because of their privacy settings!")

    async def _forbidden_msg(self, ctx):
        await ctx.send(f"{ctx.author.mention}, hey your privacy settings seems to disallow me from direct messaging you, mind enabling direct messages in this server so I can send you your stored info?", delete_after=10)

    async def _already_added(self, ctx, platform):
        await ctx.author.send(f"It seems like you've already added `{platform[1]}` as storeinfo, if you want to edit it. Please check out ``{ctx.prefix}storinfo edit``.")

    async def _does_not_exist(self, ctx, platform, information):
        await ctx.author.send(f"Hey, {ctx.author}! It appears you don't even have a stored info for `{platform[1]}`. But don't you worry, I've added it for you, with your specified information. (`{Utils.escape_markdown(information)}`).")

    async def _edited_log_to_botlog(self, ctx, platform, old_information, information):
        await BugBotLogging.bot_log(f"💾 {ctx.author} (`{ctx.author.id}`) has edited their (`{platform[1]}`) trigger to `{Utils.escape_markdown(information)}` (previously `{Utils.escape_markdown(old_information)}`).")

    async def _added_log_to_botlog(self, ctx, platform, information):
        await BugBotLogging.bot_log(f"💾 {ctx.author} (`{ctx.author.id}`) has added their `{platform[1]}` storeinfo as: (`{Utils.escape_markdown(information)}`)")

    async def _success_add_msg(self, ctx, platform, information):
        await ctx.author.send(f"<:greenTick:312314752711786497> Successfully set your `{platform[1]}` trigger as `{information}`")

    async def _succes_edit_msg(self, ctx, platform, old_information, information):
        await ctx.author.send(f"<:greenTick:312314752711786497> Successfully edited your `{platform[1]}` trigger to `{Utils.escape_markdown(information)}` (previously `{Utils.escape_markdown(old_information)}`).")

    async def _edit_storeinfo(self, added, information):
        added.information = information
        added.save()

    async def _add_storeinfo(self, uid, platform, information):
        Storeinfo.create(
            userid=uid, platform=platform[0], information=information
        )

    @commands.group()
    async def storeinfo(self, ctx):
        """Command for managing storeinfo"""
        if ctx.invoked_subcommand is None:
            # Get all the stored information from the command invoker
            Windows = Storeinfo.get_or_none(userid=ctx.author.id, platform=Platforms.desktop)
            Mac = Storeinfo.get_or_none(userid=ctx.author.id, platform=Platforms.mac)
            Linux = Storeinfo.get_or_none(userid=ctx.author.id, platform=Platforms.linux)
            Android = Storeinfo.get_or_none(userid=ctx.author.id, platform=Platforms.android)
            iOS = Storeinfo.get_or_none(userid=ctx.author.id, platform=Platforms.ios)
            description = """
            **HOW TO CHANGE AND ADD STOREINFO:**\n
            You can add a storeinfo by doing\n`!storeinfo add "-w" Windows 10 Pro 64-bit (1809)`.
            
            You can edit a storeinfo by doing\n`!storeinfo edit "-w" Windows 7 64-bit Ultimate Edition`
            
            The character limit for the information paratemeter is 50.
            This is all experimental, the character limit might change in the future.
            """
            # Embed building
            e = discord.Embed(color=15158332, description=description, timestamp=ctx.message.created_at)
            e.add_field(name="🖥 Windows -w:", value=Windows.information if Windows is not None else "None")
            e.add_field(name="🖥 Mac -m:", value=Mac.information if Mac is not None else "None")
            e.add_field(name="🐧Linux -L:", value=Linux.information if Linux is not None else "None")
            e.add_field(name="🤖 Android -a:", value=Android.information if Android is not None else "None")
            e.add_field(name="📱 iOS -i:", value=iOS.information if iOS is not None else "None")
            e.set_thumbnail(url=ctx.author.avatar_url)
            e.set_author(name=f"{ctx.author}'s storeinfo!")
            try: # Try to send a DM to the command invoker, if it fails. Log to bot log and leave a message in the channel they ran the command in and delete after a few secconds.
                await ctx.author.send(content=f"Hello there {ctx.author}! Here’s all of the information we have stored for you:", embed=e)
            except discord.Forbidden:
                await self._forbidden_msg(ctx)
                await self._forbiden_msg_log(ctx)
            if ctx.guild is not None: #If they ran the command outside DMs, delete their message.
                await ctx.message.delete()

    @storeinfo.command()
    async def add(self, ctx, platform: platform_convert, *, information):
        """Command for adding a storeinfo!

        -------
        The syntax is !storeinfo add "-w" Windows 10 Pro 64-bit (1809)"""
        added = Storeinfo.get_or_none(userid=ctx.author.id, platform=platform[0]) # Check if it's already been added
        if added is None: # If it has been added, add it for us.
            await self._add_storeinfo(ctx.author.id, platform, information)
            if ctx.guild is not None:
                await ctx.message.delete()
            try:
                await self._success_add_msg(ctx, platform, information) # Attempt to DM them the success message.
            except discord.Forbidden: # If we fail to do so, notify them and log it.
                await self._forbiden_msg_log(ctx)
                return await self._forbidden_msg(ctx)
            await self._added_log_to_botlog(ctx, platform, information) # Log it that we added their storeinfo.
        else: # If it has been added, notify them that they can edit it instead.
            if ctx.guild is not None:
                await ctx.message.delete()
            try:
                await self._already_added(ctx, platform)
            except discord.Forbidden:
                await self._forbiden_msg_log(ctx)
                return await self._forbidden_msg(ctx)

    @storeinfo.command()
    async def edit(self, ctx, platform: platform_convert, *, information):
        """Command for editing a storeinfo!

        --------
        The syntax is !storeinfo edit "-w" Windows 7 64-bit Ultimate Edition"""
        added = Storeinfo.get_or_none(userid=ctx.author.id, platform=platform[0]) # Get the stored information if exists
        if added is not None:
            old_information = added.information # Assign the previous stored info to a variable
            await self._edit_storeinfo(added, information) # Edit the storeinfo
            try: # Attempt to DM them about it. If not possible, notify them and log it.
                await self._succes_edit_msg(ctx, platform, old_information, information)
            except discord.Forbidden:
                await self._forbiden_msg_log(ctx)
                return await self._forbidden_msg(ctx)
            await self._edited_log_to_botlog(ctx, platform, old_information, information)
            if ctx.guild is not None:
                await ctx.message.delete()
        else: # If it does not exist, create it for them and let them know it did not exist, but one was made for them.
            await self._add_storeinfo(ctx.author.id, platform, information)
            await self._added_log_to_botlog(ctx, platform, information)
            try:
                await self._does_not_exist(ctx, platform, information)
            except discord.Forbidden:
                await self._forbiden_msg_log(ctx)
                return await self._forbidden_msg(ctx)
            if ctx.guild is not None:
                await ctx.message.delete()

    async def process_web_report(self, data):
        pass

    def build_report_embed(self, data):
        em = discord.Embed(colour=data['platform']['colour'])
        if 'lock' in data:
            mod = data['lock']['username']
            reason = data['lock']['reason']
            em.description = f':lock: This report has been temporarily locked by {mod} and cannot be interacted with (`{reason}`)'
        em.add_field(name='Submitter', value=f'{data["submitter"]["username"]} (`{data["submitter"]["id"]}`) {data["submitter"]["emoji"]}', inline=False)
        em.add_field(name='Platform', value=f'{data["platform"]["name"]} {data["platform"]["emoji"]}', inline=False)
        em.add_field(name='Short Description', value=data['title'], inline=False)
        em.add_field(name='Steps to Reproduce', value=data['steps'], inline=False)
        em.add_field(name='Expected Result', value=data['expected'], inline=False)
        em.add_field(name='Actual Result', value=data['actual'], inline=False)
        em.add_field(name='Client Info', value=data['client'], inline=True)
        em.add_field(name='Device/System Info', value=data['system'], inline=True)
        em.add_field(name='Report ID', value=f'**{data["id"]}**', inline=False)

        interactions = []
        for x in reversed(data['repros']):
            if x['type'] == 'approve':
                emoji = Emoji.get_chat_emoji('APPROVE')
            elif x['type'] == 'deny':
                emoji = Emoji.get_chat_emoji('DENY')
            elif x['type'] == 'note':
                emoji = ':pencil:'
            interactions.append(f'{emoji} **{x["username"]}** (`{x["id"]}`): `{x["details"]}`')
        for x in data['attachments']:
            interactions.append(f':paperclip: **{x["username"]}** (`{x["id"]}`): {x["link"]}')

        if len(interactions) > 0:
            em.add_field(name='---', value='\n'.join(interactions), inline=False)

        return em

        '''
        EXAMPLE FORMAT:
        {
            "platform": {
                "name": "iOS",
                "colour": 10460830,
                "emoji": ":iphone:"
            },
            "submitter": {
                "username": "Test#1234",
                "id": 258274103935369219,
                "emoji": "<:meowbughunter:533815499541184532>"
            },
            "id": 13883,
            "title": "",
            "steps": "1. This is a step\n2. Another step",
            "expected": "",
            "actual": "",
            "client": "",
            "system": "",
            "repros": [
                {
                    "username": "Test#1234",
                    "id": 258274103935369219,
                    "type": "approve",
                    "details": "Can repro..."
                }
            ],
            "lock": {
                "username": "Test#1234",
                "reason": "Checking with devs"
            },
            "attachments": [
                {
                    "username": "Test#1234",
                    "id": 258274103935369219,
                    "link": ""
                }
            ]
        }
        '''

    async def add_report(self, user, platform, report, source):

        # Check the platform is valid (or can be aliased)
        platforms = Configuration.get_var('bugbot', 'BUG_PLATFORMS')
        platform_data = platforms.get(platform.upper(), None)
        if platform_data is None:
            for p, pd in platforms.items():  # TODO: Squash this
                if platform.lower() in pd['ALIASES']:
                    platform = p
                    platform_data = pd
                    break
        if platform_data is None:
            raise BugReportException(ReportError.unknown_platform)

        # Escape markdown in report text
        report = Utils.escape_markdown(report)

        # Check for links/invites in the report (exclude trello.com)
        if re.search(r'(discordapp\.com/invite|discord\.gg|(ftp|https?)://(?!trello\.com)\S+)', report, re.IGNORECASE):
            raise BugReportException(ReportError.links_detected)

        # Check all required fields are present
        groups = re.match(r'(?P<title>.*)\s\|\sSteps\sto\sReproduce:(?P<steps>.*)\sExpected\sResult:\s(?P<expected>.*)\sActual\sResult:\s(?P<actual>.*)\sClient\sSettings:\s(?P<client>.*)\sSystem\sSettings:\s(?P<system>.*)', report, re.IGNORECASE)
        if not groups:
            raise BugReportException(ReportError.missing_fields)

        # Split text into fields and parse where necessary (e.g. steps)
        sections = groups.groupdict()
        steps = sections['steps'].split(' - ')
        if len(steps) < 2:
            raise BugReportException(ReportError.missing_steps)
        del steps[0]
        sections['steps'] = '\n'.join([f'{idx + 1}. {step}' for idx, step in enumerate(steps)])

        # Check for blacklisted words in title/actual result
        blacklist = [x for x in Configuration.get_var('bugbot', 'BUG_TEXT_BLACKLIST') if x in sections['title'].lower() or x in sections['actual'].lower()]  # FIXME: This matches within words so will catch 'buggy'...etc
        if len(blacklist) > 0:
            raise BugReportException(ReportError.blacklisted_words, ', '.join(blacklist))

        # Check length of each section doesn't exceed field length
        if any([x for x in sections.values() if len(x) >= 2000]):
            raise BugReportException(ReportError.length_exceeded)

        # Add report to database and get report ID
        bug = Bug.create(
            reporter=user.id,
            title=sections['title'],
            steps=sections['steps'],
            expected=sections['expected'],
            client_info=sections['client'],
            device_info=sections['system'],
            platform=Platforms[platform.lower()],
            source=source
        )

        # Build embed
        report = {'id': bug.id, 'repros': [], 'attachments': []}
        report.update(sections)
        report['submitter'] = {'username': str(user), 'id': user.id, 'emoji': ''}
        if hasattr(user, 'roles'):
            if Configuration.get_role('BUG_HUNTER') in user.roles:
                report['submitter']['emoji'] = Emoji.get_chat_emoji('MEOWBUGHUNTER')
        if not platform_data['EMOJI'].startswith(':'):
            platform_data['EMOJI'] = Emoji.get_chat_emoji(platform_data['EMOJI'])
        report['platform'] = {'name': platform_data['DISPLAY'], 'colour': platform_data['COLOUR'], 'emoji': platform_data['EMOJI']}
        em = self.build_report_embed(report)

        # Post embed in queue and get message ID
        queue = self.bot.get_channel(Configuration.get_master_var('BUGCHANNELS')['QUEUE'])
        msg = await queue.send(embed=em)

        # Update database entry with message ID
        bug.msg_id = msg.id
        bug.save()

        # Return the report ID
        return bug.id

    @commands.command()
    #@Checks.dm_only()  # For easier testing
    async def submit(self, ctx: commands.Context, platform: str, *, report_str: str):
        dt = self.bot.get_guild(Configuration.get_master_var('GUILD_ID'))
        member = dt.get_member(ctx.author.id)
        try:
            report_id = await self.add_report(member, platform, report_str, ReportSource.command)
        except BugReportException as e:
            response = Configuration.get_var('strings', e.code.name.upper())
            if response is not None:
                if e.code == ReportError.blacklisted_words:
                    response = response.format(terms=e.msg)
                response = f'{ctx.author.mention}, {response}'
            else:
                response = e.code.name
            await ctx.send(response)
        else:
            await BugBotLogging.bot_log(f':clipboard: {ctx.author} ({ctx.author.id}) submitted a new report ({report_id})')
            await ctx.send(Configuration.get_var('strings', 'REPORT_SUBMITTED').format(user=ctx.author))



def setup(bot):
    bot.add_cog(BugReporting(bot))
