import re
import asyncio
import operator
from functools import reduce
from datetime import datetime, timedelta

import discord
from discord.ext import commands

import BugBot
from Utils import BugBotLogging, Configuration, Utils, Checks, Emoji, RedisListener, ReportUtils, ExpUtils
from Utils.DataUtils import Storeinfo, Bug, BugInfo
from Utils.Enums import Platforms, ReportSource, ReportError, BugState, BugInfoType, TransactionEvent, BugBlockType
from Utils.ReportUtils import BugReportException
from Utils.Trello import TrelloException


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


class BugReport(commands.Converter):
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
            raise commands.BadArgument(f'Report "{argument}" not found')
        return bug


class BugReporting:
    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(self.redis_init())
        bot.lockdown = False
        bot.lockdown_message = ""

    async def redis_init(self):
        if self.bot.redis:
            BugBotLogging.info("Redis connection found, connecting and disabling dev submit command")
            self.bot.remove_command("submit")
            await self.bot.redis.subscribe('web_to_bot', self.receive_report, BugBot.handle_exception)
            await self.bot.redis.subscribe('trello', self.process_trello_event, BugBot.handle_exception)
        else:
            BugBotLogging.warn("No redis connection found, leaving dev submit command in place for testing")

    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return
        if message.channel.id not in Configuration.list_of_bugchannels_ids():
            return
        for role in message.author.roles:
            if role.id == Configuration.get_role('MODINATOR').id:
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
            try:  # Try to send a DM to the command invoker, if it fails. Log to bot log and leave a message in the channel they ran the command in and delete after a few secconds.
                await ctx.author.send(content=f"Hello there {ctx.author}! Here’s all of the information we have stored for you:", embed=e)
            except discord.Forbidden:
                await self._forbidden_msg(ctx)
                await self._forbiden_msg_log(ctx)
            if ctx.guild is not None:  # If they ran the command outside DMs, delete their message.
                await ctx.message.delete()

    @storeinfo.command()
    async def add(self, ctx, platform: platform_convert, *, information):
        """Command for adding a storeinfo!

        -------
        The syntax is !storeinfo add "-w" Windows 10 Pro 64-bit (1809)"""
        added = Storeinfo.get_or_none(userid=ctx.author.id, platform=platform[0])  # Check if it's already been added
        if added is None:  # If it has been added, add it for us.
            await self._add_storeinfo(ctx.author.id, platform, information)
            if ctx.guild is not None:
                await ctx.message.delete()
            try:
                await self._success_add_msg(ctx, platform, information)  # Attempt to DM them the success message.
            except discord.Forbidden:  # If we fail to do so, notify them and log it.
                await self._forbiden_msg_log(ctx)
                return await self._forbidden_msg(ctx)
            await self._added_log_to_botlog(ctx, platform, information)  # Log it that we added their storeinfo.
        else:  # If it has been added, notify them that they can edit it instead.
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
        added = Storeinfo.get_or_none(userid=ctx.author.id, platform=platform[0])  # Get the stored information if exists
        if added is not None:
            old_information = added.information  # Assign the previous stored info to a variable
            await self._edit_storeinfo(added, information)  # Edit the storeinfo
            try:  # Attempt to DM them about it. If not possible, notify them and log it.
                await self._succes_edit_msg(ctx, platform, old_information, information)
            except discord.Forbidden:
                await self._forbiden_msg_log(ctx)
                return await self._forbidden_msg(ctx)
            await self._edited_log_to_botlog(ctx, platform, old_information, information)
            if ctx.guild is not None:
                await ctx.message.delete()
        else:  # If it does not exist, create it for them and let them know it did not exist, but one was made for them.
            await self._add_storeinfo(ctx.author.id, platform, information)
            await self._added_log_to_botlog(ctx, platform, information)
            try:
                await self._does_not_exist(ctx, platform, information)
            except discord.Forbidden:
                await self._forbiden_msg_log(ctx)
                return await self._forbidden_msg(ctx)
            if ctx.guild is not None:
                await ctx.message.delete()

    @commands.command()
    # @Checks.dm_only()  # For easier testing
    async def submit(self, ctx: commands.Context, platform: str, title, steps, expected, actual, client, system):
        member = Configuration.get_tester(ctx.author.id)
        try:
            sections = dict(title=title, steps=steps, expected=expected, actual=actual, client=client, system=system)
            steps = sections['steps'].split(' - ')
            del steps[0]
            sections['steps'] = '\n'.join([f'{idx + 1}. {step}' for idx, step in enumerate(steps)])
            sections["platform"] = platform
            ReportUtils.validate_report(sections)
            report_id = await ReportUtils.add_report(member, sections, ReportSource.command)
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
            await BugBotLogging.bot_log(f':clipboard: {ctx.author} (`{ctx.author.id}`) submitted a new report ({report_id})')
            await ctx.send(Configuration.get_var('strings', 'REPORT_SUBMITTED').format(user=ctx.author))

    def sub_storeinfo(self, content, user_id):
        flags = list(set(re.findall(r'-[a-z]\b', content, re.IGNORECASE)))
        for i in flags:
            pf = platform_convert(i)
            if pf:
                info = Storeinfo.get_or_none(userid=user_id, platform=pf[0])
                if info is not None:
                    content = re.sub(fr'{i}\b', info.information, content, flags=re.IGNORECASE)
        return content

    async def complete_approval_flow(self, bug):
        # Get reporter (or user if not in DTesters)
        reporter = Configuration.get_tester(bug.reporter)
        if reporter is None:
            reporter = self.bot.get_user(bug.reporter)

        # Give initial XP for approval
        amount = Configuration.get_var('bugbot', 'XP').get('APPROVED_BUG', 5)
        await ExpUtils.add_xp(bug.reporter, amount, self.bot.user.id, TransactionEvent.bug_approved)
        await BugBotLogging.bot_log(f':moneybag: Gave {amount} XP to {reporter} (`{reporter.id}`) for an approved bug')

        # Build the Trello content
        content = Configuration.get_var('strings', 'TRELLO_CONTENT').format(reporter=reporter, bug=bug)

        # Get the new list ID
        list_id = Configuration.get_var('bugbot', 'BUG_PLATFORMS')[bug.platform.name.upper()]['NEW_LIST']

        # Push to Trello
        trello_id = await self.bot.trello.add_card(list_id, bug.title, content)

        # Set extra details in the DB
        bug.block_type = BugBlockType.none
        bug.trello_id = trello_id
        bug.state = BugState.approved
        bug.last_state_change = datetime.utcnow()
        bug.trello_list = list_id
        bug.save()

        # Generate a new embed
        em = ReportUtils.bug_to_embed(bug, self.bot)

        # Post the embed in the appropriate report channel
        msg = await Configuration.get_bugchannel(bug.platform.name.upper()).send(embed=em)

        # Add the new message ID to the DB
        bug.msg_id = msg.id
        bug.save()

        # Add approvals to Trello
        for i in bug.info:
            if i.type == BugInfoType.can_reproduce:
                repro = Configuration.get_var('strings', 'TRELLO_REPRO').format(stance='Can reproduce', content=i.content, user=self.bot.get_user(i.user))
                comment_id = await self.bot.trello.add_comment(trello_id, repro)
                i.trello_id = comment_id
                i.save()
                await asyncio.sleep(1)

        trello_link = f'https://trello.com/c/{trello_id}'

        await BugBotLogging.bot_log(f':incoming_envelope: Report {bug.id} has been fully approved and added to Trello under <{trello_link}>')

        # Follow new initiate flow or DM an approved message if they're already a hunter
        if hasattr(reporter, 'roles'):
            if Configuration.get_role('BUG_HUNTER') in reporter.roles:
                # Already a hunter
                try:
                    await reporter.send(Configuration.get_var('strings', 'BUG_APPROVED').format(trello_link=trello_link, report_id=bug.id))
                except discord.Forbidden:
                    # Closed DMs
                    pass
            else:
                bh_cog = self.bot.get_cog('BugHunter')
                await bh_cog.make_initiate(reporter)  # FIXME: They won't get informed if they're already an initiate

    async def complete_denial_flow(self, bug, selfdeny=False):
        # Set extra details in the DB
        bug.block_type = BugBlockType.none
        bug.state = BugState.denied
        bug.last_state_change = datetime.utcnow()
        bug.save()

        # Generate a new embed
        em = ReportUtils.bug_to_embed(bug, self.bot)

        # Post the embed in the denied bugs channel
        msg = await Configuration.get_bugchannel('DENIED').send(embed=em)

        # Add the new message ID
        bug.msg_id = msg.id
        bug.save()

        await BugBotLogging.bot_log(f':clipboard: Report {bug.id} has been fully denied')

        # Build jump link
        guild_id = Configuration.get_master_var('GUILD_ID')
        channel_id = Configuration.get_master_var('BUGCHANNELS')['DENIED']
        jumplink = f'https://discordapp.com/channels/{guild_id}/{channel_id}/{msg.id}'

        # Post a denied message in the queue
        queue_reply = Configuration.get_var('strings', 'BUG_DENIED_QUEUE').format(report_id=bug.id, jumplink=jumplink)
        await Configuration.get_bugchannel('QUEUE').send(queue_reply, delete_after=20.0)

        # DM the reporter
        reporter = self.bot.get_user(bug.reporter)
        if reporter is not None and not selfdeny:
            reasons = []
            denials = [i for i in bug.info if i.type == BugInfoType.can_not_reproduce]
            for idx, i in enumerate(denials):
                deny_user = str(self.bot.get_user(i.user))
                reasons.append(f'{idx + 1}. `{deny_user}`: `{i.content}`')
            deny_dm = Configuration.get_var('strings', 'BUG_DENIED_DM').format(title=bug.title, report_id=bug.id, reasons='\n'.join(reasons))
            try:
                await reporter.send(deny_dm)
            except discord.Forbidden:
                # Closed DMs
                pass

    async def process_stance(self, ctx, report_id, content, stance, override=False):
        err = None
        # Escape the stance content
        content = Utils.escape_markdown(content)
        # Try and get the bug
        bug = Bug.get_or_none(id=report_id)
        # Check we're in the queue
        if ctx.channel.id != Configuration.get_master_var('BUGCHANNELS')['QUEUE']:
            err = 'STANCE_WRONG_CHANNEL'
        # Check the bug is valid
        elif bug is None:
            err = 'INVALID_REPORT_ID'
        # Check the bug is queued
        elif bug.state != BugState.queued:
            err = 'BUG_NOT_QUEUED'
        # Check the bug isn't locked/in the 20s wait period
        elif bug.block_type != BugBlockType.none:
            err = 'BUG_LOCKED'
        # Check the content isn't too long
        elif len(content) > 500:
            err = 'STANCE_TOO_LONG'
        # If approving, check it's not their own bug
        elif stance == 'approve':
            if bug.reporter == ctx.author.id and not override:
                err = 'SELF_APPROVE_DISALLOWED'

        if err is None:
            # Substitute storeinfo flags
            content = self.sub_storeinfo(content, ctx.author.id)

            # Try and get an existing stance
            stance_obj = BugInfo.get_or_none(BugInfo.user == ctx.author.id, BugInfo.bug == bug, BugInfo.type << [BugInfoType.can_reproduce, BugInfoType.can_not_reproduce])

            # Set the BugInfoType
            if stance == 'approve':
                stance_type = BugInfoType.can_reproduce
                action = 'approved'
                emoji = ':thumbsup:'
            elif stance == 'deny':
                stance_type = BugInfoType.can_not_reproduce
                action = 'denied'
                emoji = ':thumbsdown:'

            log_suffix = ''

            # If they don't have a stance, create one
            if stance_obj is None:
                BugInfo.create(user=ctx.author.id, content=content, bug=bug, type=stance_type)
                reply = f'{stance.upper()}_ADDED'
                # Give XP (if eligible)
                if ctx.author.id != bug.reporter:
                    exp_cog = self.bot.get_cog('Experience')
                    await exp_cog.give_repro_xp(ctx.author.id, TransactionEvent[stance])
            # If they have an existing stance, update it
            else:
                stance_obj.type = stance_type
                stance_obj.content = content
                stance_obj.added = datetime.utcnow()
                stance_obj.save()
                reply = 'STANCE_CHANGED'
                log_suffix = ' (updated stance)'

            await BugBotLogging.bot_log(f'{emoji} {ctx.author} (`{ctx.author.id}`) {action} report {report_id}{log_suffix}')

        # Get the response string
        if err is not None:
            reply = err
        reply = Configuration.get_var('strings', reply).format(user=ctx.author)

        # Reply to the user
        await ctx.send(reply, delete_after=3.0)

        # Delete their invoke message
        await asyncio.sleep(3)
        await ctx.message.delete()

        if err is not None:
            return

        # Get users who have a stance on the bug
        users = [i.user for i in bug.info if i.type == stance_type]

        # If they denied their own bug, set the required stance override
        selfdeny = False
        if stance == 'deny' and ctx.author.id == bug.reporter:
            selfdeny = True
            override = True

        # If we're in the final approval/denial flow
        if override or len(users) >= Configuration.get_var('bugbot', 'REQUIRED_STANCES')[stance.upper()]:
            # Lock the bug
            bug.block_type = BugBlockType.flow
            bug.save()

            # Rebuild the embed
            em = ReportUtils.bug_to_embed(bug, self.bot)

            # Update queue message with the new embed
            queue_msg = await Configuration.get_bugchannel('QUEUE').get_message(bug.msg_id)
            await queue_msg.edit(embed=em)

            def revoke_check(data):
                return data['bug_id'] == bug.id and data['user_id'] in users and data['stance'] == stance

            try:
                await self.bot.wait_for('revoke', check=revoke_check, timeout=20.0)
            except asyncio.TimeoutError:
                if stance == 'approve':
                    await self.complete_approval_flow(bug)
                elif stance == 'deny':
                    await self.complete_denial_flow(bug, selfdeny)
                # Delete the queue message
                await queue_msg.delete()
            else:
                # Someone revoked
                await BugBotLogging.bot_log(f':clipboard: Report {report_id} received a revoke during final {stance} flow')

                # Unlock the bug
                bug.block_type = BugBlockType.none
                bug.save()

                # Rebuild the embed
                em = ReportUtils.bug_to_embed(bug, self.bot)

                # Update queue message with the new embed
                queue_msg = await Configuration.get_bugchannel('QUEUE').get_message(bug.msg_id)
                await queue_msg.edit(embed=em)
        else:
            # Rebuild the embed
            em = ReportUtils.bug_to_embed(bug, self.bot)

            # Update queue message with the new embed
            queue_msg = await Configuration.get_bugchannel('QUEUE').get_message(bug.msg_id)
            await queue_msg.edit(embed=em)

    @commands.command()
    @commands.guild_only()
    async def approve(self, ctx, report_id: int, *, content: str):
        await self.process_stance(ctx, report_id, content, 'approve')

    @commands.command()
    @commands.guild_only()
    async def deny(self, ctx, report_id: int, *, content: str):
        await self.process_stance(ctx, report_id, content, 'deny')

    @commands.command()
    @commands.guild_only()
    @Checks.is_employee()
    async def dapprove(self, ctx, report_id: int, * content: str):
        await self.process_stance(ctx, report_id, content, 'approve', override=True)

    @commands.command()
    @commands.guild_only()
    @Checks.is_employee()
    async def ddeny(self, ctx, report_id: int, * content: str):
        await self.process_stance(ctx, report_id, content, 'deny', override=True)

    @commands.command()
    @commands.guild_only()
    async def revoke(self, ctx, report_id: int):
        # Try and get their stance
        clauses = [
            (BugInfo.user == ctx.author.id),
            (BugInfo.bug.id == report_id),
            (BugInfo.type << [BugInfoType.can_reproduce, BugInfoType.can_not_reproduce])
        ]
        try:
            stance = (BugInfo
                      .select()
                      .join(Bug)
                      .where(reduce(operator.and_, clauses))
                      .get())
        except BugInfo.DoesNotExist:
            stance = None

        # Check we're in the bug approval queue
        if ctx.channel.id != Configuration.get_master_var('BUGCHANNELS').get('QUEUE'):
            reply = 'STANCE_WRONG_CHANNEL'
        # Check if the stance exists
        elif stance is None:
            reply = 'NO_STANCE'
        # Check if the bug is queued
        elif stance.bug.state != BugState.queued:
            reply = 'BUG_NOT_QUEUED'
        else:
            # Get the stance type
            stance_type = 'approve' if stance.type == BugInfoType.can_reproduce else 'deny'
            bug = stance.bug

            # Delete the stance
            stance.delete_instance()

            # Remove XP
            if bug.reporter != ctx.author.id:
                amount = Configuration.get_var('bugbot', 'XP').get('QUEUE_REPRO', 0)
                ExpUtils.remove_lifetime_xp(ctx.author.id, amount)
                balance = ExpUtils.get_xp(ctx.author.id)[0]
                revoke_type = TransactionEvent.revoke
                if amount > balance:
                    revoke_type = TransactionEvent.revoke_spent_xp
                    amount = balance
                ExpUtils.remove_xp(ctx.author.id, amount, self.bot.user.id, revoke_type)

            reply = 'REVOKED_STANCE'
            await BugBotLogging.bot_log(f':wastebasket: {ctx.author} (`{ctx.author.id}`) revoked their stance on report {report_id}')

            # Rebuild the embed
            em = ReportUtils.bug_to_embed(bug, self.bot)

            # Update queue message with the new embed
            queue_msg = await Configuration.get_bugchannel('QUEUE').get_message(bug.msg_id)
            await queue_msg.edit(embed=em)

            # Dispatch revoke event (to cancel final approval flows)
            data = {
                'bug_id': bug.id,
                'user_id': ctx.author.id,
                'stance': stance_type
            }
            self.bot.dispatch('revoke', data)

        await ctx.send(Configuration.get_var('strings', reply).format(user=ctx.author, report_id=report_id), delete_after=3.0)
        await asyncio.sleep(3)
        await ctx.message.delete()

    async def process_trello_repro(self, ctx, bug, content, stance):

        # Check we're in a bug reporting channel
        if ctx.channel.id not in Configuration.get_master_var('BUGCHANNELS').values():
            reply = 'REPRO_WRONG_CHANNEL'

        # Check if the bug is approved
        elif bug.state != BugState.approved:
            reply = 'BUG_NOT_APPROVED'

        # Check the bug is not dead
        elif bug.trello_list in Configuration.get_var('bugbot', 'TRELLO')['DEAD_BUG_LISTS']:
            reply = 'REPRO_DEAD_BUG'

        # Check if the word 'latest' is in the repro content
        elif 'latest' in content.lower():
            reply = 'REPRO_BLACKLISTED'

        else:
            # Remove markdown from the content
            content = Utils.escape_markdown(content)

            # Set stance vars
            if stance == 'canrepro':
                stance_type = BugInfoType.can_reproduce
                xp_event = TransactionEvent.can_repro
                trello_stance = 'Can reproduce'
                emoji = ':thumbsup:'
            elif stance == 'cannotrepro':
                stance_type = BugInfoType.can_not_reproduce
                xp_event = TransactionEvent.cannot_repro
                trello_stance = 'Cannot reproduce'
                emoji = ':thumbsdown:'

            # Add/edit their stance and push to Trello
            repro = Configuration.get_var('strings', 'TRELLO_REPRO').format(stance=trello_stance, content=content, user=ctx.author)
            stance_obj = BugInfo.get_or_none(BugInfo.user == ctx.author.id, BugInfo.bug == bug, BugInfo.type << [BugInfoType.can_reproduce, BugInfoType.can_not_reproduce])
            if stance_obj is not None and datetime.utcnow() < (stance_obj.added + timedelta(days=1)):
                # Has a stance that can be edited
                stance_obj.content = content
                stance_obj.type = stance_type
                stance_obj.added = datetime.utcnow()
                stance_obj.save()
                await self.bot.trello.edit_comment(bug.trello_id, stance_obj.trello_id, repro)
            else:
                # Add a new stance
                comment_id = await self.bot.trello.add_comment(bug.trello_id, repro)
                BugInfo.create(user=ctx.author.id, content=content, bug=bug, type=stance_type, trello_id=comment_id)

            await BugBotLogging.bot_log(f'{emoji} {ctx.author} (`{ctx.author.id}`) added a {stance} to report `{bug.trello_id}` ({bug.id})')

            # Unarchive the card (if it isn't already on the board)
            # await self.bot.trello.unarchive_card(bug.trello_id)  # TODO: Only unarchive if auto-archived

            # Regenerate the embed
            em = ReportUtils.bug_to_embed(bug, self.bot)

            # Update message with the new embed
            msg = await Configuration.get_bugchannel(bug.platform.name).get_message(bug.msg_id)
            try:
                await msg.edit(embed=em)
            except discord.HTTPException:
                pass

            # Give them some XP (if eligible)
            if Configuration.get_role('BUG_HUNTER') in ctx.author.roles and ctx.author.id != bug.reporter and stance_obj is None:
                exp_cog = self.bot.get_cog('Experience')
                await exp_cog.give_repro_xp(ctx.author.id, xp_event)

            reply = 'REPRO_ADDED'

        # Respond to the user
        await ctx.send(Configuration.get_var('strings', reply).format(user=ctx.author), delete_after=3.0)
        await asyncio.sleep(3)
        await ctx.message.delete()

    @commands.command(aliases=['cr'])
    @commands.guild_only()
    async def canrepro(self, ctx, bug: BugReport, *, content: str):
        await self.process_trello_repro(ctx, bug, content, 'canrepro')

    @commands.command(aliases=['cnr', 'cantrepro'])
    @commands.guild_only()
    async def cannotrepro(self, ctx, bug: BugReport, *, content: str):
        await self.process_trello_repro(ctx, bug, content, 'cannotrepro')

    async def receive_report(self, report):
        # validation has already been done by the webserver so we don't need to bother doing that again here

        # no reporting during lockdown
        if self.bot.lockdown:
            reply = dict(submitted=False, lockdown=True, message=self.bot.lockdown_message)
            await self.bot.redis.send('bot_to_web', reply)
        else:
            user = self.bot.get_user(int(report['user_id']))
            try:
                # try to send report
                id = await ReportUtils.add_report(user, report, ReportSource.form)
                reply = dict(UUID=report["UUID"], submitted=True, lockdown=False,
                             message=f"Your report ID is {id}")
                await self.bot.redis.send('bot_to_web', reply)
            except Exception as ex:
                # something went wrong, notify the other side
                reply = dict(UUID=report["UUID"], submitted=False, lockdown=False, message="Something went very wrong. Mods have been notified, please try again later")
                await self.bot.redis.send('bot_to_web', reply)
                raise ex

    async def process_trello_event(self, data):
        card_events = ['addAttachmentToCard', 'addLabelToCard', 'addMemberToCard', 'commentCard', 'deleteAttachmentFromCard', 'removeLabelFromCard', 'removeMemberFromCard', 'updateCard']
        if data['type'] in card_events:
            bug = Bug.get_or_none(Bug.trello_id == data['data']['card']['shortLink'])
            if bug is not None:
                bug.last_activity = datetime.utcnow()
                if 'listAfter' in data['data']:
                    bug.trello_list = data['data']['listAfter']['id']
                elif 'list' in data['data']:
                    bug.trello_list = data['data']['list']['id']
                bug.save()
                if data['type'] == 'commentCard':
                    pass
                    # If a dev/engineer commented on the card (backlog feature)
                    # if data['idMemberCreator'] in Configuration.get_var('bugbot', 'dev_trello_ids'):
                    #    pass
                if not bug.xp_awarded:
                    if data['type'] == 'updateCard':
                        await ExpUtils.award_bug_xp(self.bot, bug.trello_id, bug.trello_list, archived=data['data']['card'].get('closed', False))
                    elif data['type'] == 'addLabelToCard':
                        await ExpUtils.award_bug_xp(self.bot, bug.trello_id, label_ids=[data['data']['label']['id']], archived=data['data']['card'].get('closed', False))

    @commands.command(name='bug')
    @Checks.is_modinator()
    async def _bugcommand(self, ctx: commands.Context, bugID: int):
        try:
            bug = Bug.get_by_id(bugID)
        except:
            await ctx.message.delete()
            await BugBotLogging.bot_log(f"{Emoji.get_emoji('WARNING')} {ctx.author} (`{ctx.author.id}`) attempted to run !bug {bugID} but the bug ID specified does not even exist.")
            return await ctx.send(f"{ctx.author.mention} I was unable to find any bug with the ID `{bugID}`.", delete_after=3.0)
        platform = Configuration.get_var('bugbot', 'BUG_PLATFORMS').get(bug.platform.name.upper(), None)
        bug_embed = ReportUtils.bug_to_embed(bug, ctx.bot)
        try:
            await ctx.author.send(embed=bug_embed)
        except discord.Forbidden:
            await ctx.message.delete()
            await BugBotLogging.bot_log(f"{ctx.author} (`{ctx.author.id}`) attempted to run !bug {bugID} but their privacy settings are turned off.")
            return await ctx.send(f"{Emoji.get_emoji('WARNING')} {ctx.author.mention} Your DM settings does not allow me to DM you.", delete_after=3.0)
        await ctx.message.delete()
        await BugBotLogging.bot_log(f"{Emoji.get_emoji('MEOWBUGHUNTER')} {ctx.author} (`{ctx.author.id}`) looked up bug ID {bugID}.")


def setup(bot):
    bot.add_cog(BugReporting(bot))
