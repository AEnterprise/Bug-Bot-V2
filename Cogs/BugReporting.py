import asyncio

import discord
from discord.ext import commands

from Utils import Configuration

class BugReporting:
    def __init__(self, bot):
        self.bot = bot

    
    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return
        if message.channel.id not in Configuration.list_of_bugchannels_ids():
            return
        ctx = await self.bot.get_context(message)
        if ctx.command is None:
            await message.channel.send(Configuration.get_master_var('STRINGS').get('NON_COMMANDS_MSG').format(user=message.author.mention), delete_after=5)
            await asyncio.sleep(5)
            await message.delete()

def setup(bot):
    bot.add_cog(BugReporting(bot))