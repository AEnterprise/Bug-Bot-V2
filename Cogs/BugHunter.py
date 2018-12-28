import time

import discord
from discord.ext import commands

from Utils import Checks, BugBotLogging, Configuration


class BugHunter:

    def __init__(self, bot):
        self.bot = bot

    # TODO: Call this when a bug is approved and it'll handle making the reporter an initiate (if eligible)
    async def initiate(self, member):
        # Check they're not already a BH/initiate
        role_ids = [Configuration.get_master_var('ROLES')[r] for r in ['BUG_HUNTER', 'INITIATE']]
        if any([r for r in member.roles if r.id in role_ids]):
            return

        # Add the initiate role
        initiate_role = discord.utils.get(member.guild.roles, id=Configuration.get_master_var('ROLES')['INITIATE'])
        try:
            await member.add_roles(initiate_role)
        except (discord.Forbidden, discord.HTTPException) as e:
            await BugBotLogging.bot_log(f'Failed to add the initiate role to {member}')
            return

        # Send DM
        try:
            await member.send(Configuration.get_master_var('STRINGS')['NEW_INITIATE'])
        except discord.Forbidden:
            # Closed DMs
            pass

        # TODO: Record the time to the DB
        dm_sent = time.time()

    async def on_message(self, message):
        if not isinstance(message.channel, discord.DMChannel):
            return

        # Check if they're an initiate
        dt = self.bot.get_guild(Configuration.get_master_var('DTESTERS_ID'))
        tester = dt.get_member(message.author.id)
        if tester is not None:
            initiate_role = discord.utils.get(tester.roles, id=Configuration.get_master_var('ROLES')['INITIATE'])
            if initiate_role:
                # They're an initiate. Check for the phrase
                if message.clean_content.lower() == Configuration.get_master_var('INITIATE_PHRASE').lower():
                    # Phrase matches
                    phrase_received = time.time()

                    # Remove the initiate role and add BH
                    roles = tester.roles
                    roles.remove(initiate_role)
                    bh_role = discord.utils.get(dt.roles, id=Configuration.get_master_var('ROLES')['BUG_HUNTER'])
                    roles.append(bh_role)
                    try:
                        await tester.edit(roles=roles, reason='Became a Bug Hunter')
                    except (discord.Forbidden, discord.HTTPException) as e:
                        await BugBotLogging.bot_log(f'Failed to alter roles for new Bug Hunter, {tester}')
                    else:
                        # Post in log channel how long it took
                        # TODO: Pull the DM sent timestamp from the DB. Using a placeholder for now
                        dm_sent = 1546030800.0
                        time_taken = phrase_received - dm_sent
                        hours, rem = divmod(time_taken, 3600)
                        mins, secs = divmod(rem, 60)
                        tstr = f'{int(hours)}h {int(mins)}m {int(secs)}s'
                        await BugBotLogging.bot_log(Configuration.get_master_var('STRINGS')['INITIATE_TIME_TAKEN'].format(tester=tester, time=tstr))

                        # Welcome them in BHGC
                        bhgc = Configuration.get_channel(self, 'BUG_HUNTER')
                        await bhgc.send(Configuration.get_master_var('STRINGS')['BH_WELCOME'].format(tester=tester))
                else:
                    # Wrong phrase
                    await message.channel.send(Configuration.get_master_var('STRINGS')['WRONG_PHRASE'])


def setup(bot):
    bot.add_cog(BugHunter(bot))
