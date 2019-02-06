from datetime import datetime

import discord
from discord.ext import commands

from Utils import Checks, BugBotLogging, Configuration
from Utils.DataUtils import BugHunter as Hunter


class BugHunter:

    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @Checks.is_modinator()
    async def initiate(self, ctx: commands.Context, member: discord.Member):
        if await self.make_initiate(member):
            await BugBotLogging.bot_log(f':mortar_board: {ctx.author} triggered the initiate flow on {member}')
            await ctx.send(f'Manually triggered the initiate flow on {member}')
        else:
            await ctx.send(f'{member} is not eligible to become an initiate')

    async def make_initiate(self, member):
        # Check they're not already a BH/initiate
        role_ids = [Configuration.get_master_var('ROLES')[r] for r in ['BUG_HUNTER', 'INITIATE']]
        if any([r for r in member.roles if r.id in role_ids]):
            return False
        # Add the initiate role
        initiate_role = Configuration.get_role('INITIATE')
        try:
            await member.add_roles(initiate_role)
        except (discord.Forbidden, discord.HTTPException):
            await BugBotLogging.bot_log(f'Failed to add the initiate role to {member}')
            raise
        else:
            await BugBotLogging.bot_log(f':mortar_board: Added the initiate role to {member} due to an approved bug')
            # Send DM
            try:
                await member.send(Configuration.get_var('strings', 'NEW_INITIATE'))
            except discord.Forbidden:
                # Closed DMs
                pass
            (Hunter.insert(id=member.id, initiate_at=datetime.utcnow())
                   .on_conflict(update={
                       Hunter.initiate_at: datetime.utcnow(),
                       Hunter.hunter_at: None})
                   .execute())
            return True

    async def on_message(self, message):
        if not isinstance(message.channel, discord.DMChannel):
            return
        if message.content.startswith(self.bot.command_prefix):
            return
        # Check if they're an initiate
        dt = self.bot.get_guild(Configuration.get_master_var('GUILD_ID'))
        tester = dt.get_member(message.author.id)
        if tester is not None:
            initiate_role = discord.utils.get(tester.roles, id=Configuration.get_master_var('ROLES')['INITIATE'])
            if initiate_role:
                # They're an initiate. Check for the phrase
                if message.clean_content.lower() == Configuration.get_var('bugbot', 'INITIATE_PHRASE').lower():
                    # Phrase matches
                    phrase_received = datetime.utcnow()
                    # Remove the initiate role and add BH
                    roles = tester.roles
                    roles.remove(initiate_role)
                    bh_role = Configuration.get_role('BUG_HUNTER')
                    roles.append(bh_role)
                    try:
                        await tester.edit(roles=roles, reason='Became a Bug Hunter')
                    except (discord.Forbidden, discord.HTTPException):
                        await BugBotLogging.bot_log(f'Failed to alter roles for new Bug Hunter, {tester}')
                        raise
                    else:
                        # Update hunter time in database
                        hunter = Hunter.get_by_id(tester.id)
                        dm_sent = hunter.initiate_at
                        hunter.hunter_at = phrase_received
                        hunter.save()
                        # Post in log channel how long it took
                        time_taken = int((phrase_received - dm_sent).total_seconds())
                        hours, rem = divmod(time_taken, 3600)
                        mins, secs = divmod(rem, 60)
                        tstr = f'{int(hours)}h {int(mins)}m {int(secs)}s'
                        await BugBotLogging.bot_log(Configuration.get_var('strings', 'INITIATE_TIME_TAKEN').format(tester=tester, time=tstr))
                        # Welcome them in BHGC
                        bhgc = Configuration.get_channel('BUG_HUNTER')
                        await bhgc.send(Configuration.get_var('strings', 'BH_WELCOME').format(tester=tester))
                else:
                    # Wrong phrase
                    await message.channel.send(Configuration.get_var('strings', 'WRONG_PHRASE'))


def setup(bot):
    bot.add_cog(BugHunter(bot))
