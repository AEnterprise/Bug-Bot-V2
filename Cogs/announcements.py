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
            
    @Checks.is_employee
    @commands.bot_has_permission(manage_roles=True)       
    @commands.command()
    async def BugHunter(self, ctx: commands.Context, *, BH):
        BugHunters = Configuration.get_role("BUG_HUNTER")
        channel = Configuration.get_channel("BUG_HUNTER")
        modschannel = ctx.guild.get_channel("MODINATOR")

        if BugHunters is None:
            return await ctx.send("Are you sure that you have the role working?")
        
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
