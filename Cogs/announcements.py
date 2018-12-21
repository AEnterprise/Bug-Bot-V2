import asyncio
import traceback
import discord
from discord import utils
from discord.ext import commands

from Utils import Pages, Utils, Emoji, Configuration
from Utils import Checks


class announcement:
    def __init__(self,bot):
        self.bot = bot
        self._last_result = None 

    @commands.group()
    @commands.guild_only()
    async def announce(self, ctx:commands.Context):
        """Allows variety of roles to be pinged."""
        if ctx.subcommand_passed is None:
            await ctx.invoke(self.bot.get_command('help'), 'announce')
            
    @Checks.is_employee       
    @announce.command()
    async def BugHunter(self, ctx: commands.Context, *, BH):
        BugHunters = Configuration.get_role("BUG_HUNTER")
        channel = Configuration.get_channel("BUG_HUNTER")
        modschannel = ctx.guild.get_channel(524352505446924288)

        if BugHunters is None:
            return await ctx.send("I think <@298618155281154058> accidentally deleted this role.")

        if 524406898565316619 not in [role.id for role in ctx.author.roles]:
            reply = await ctx.send("Sorry, I'm afraid that you don't have permission to use this command.")
            await asyncio.sleep(5)
            await reply.delete()
            await ctx.message.delete()
            return
        
        if ctx.message.channel != modschannel:
            return
        
        if BH != None:
            try:
                await BugHunters.edit(mentionable=True)
                await channel.send(f"{BugHunters.mention}\n{BH}")
                await BugHunters.edit(mentionable=False)      
            except discord.Forbidden:
                await ctx.send("I wasn't able to send a message in the announcement channel. Please check that I am able to talk.")
        else: 
            await ctx.send("I am unsure of what you are attempting to do.")

def setup(bot):
    bot.add_cog(announcement(bot))
