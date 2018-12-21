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
            
    @Checks.is_employee()
    @commands.bot_has_permissions(manage_roles=True)       
    @commands.command()
    async def announce(self, ctx: commands.Context, role, *, message):
        role = Configuration.get_role(ctx, "ROLES")
        channel = Configuration.get_channel(ctx, "CHANNELS")
        modschannel = Configuration.get_channel(ctx, "MODINATOR")

        if role is None:
            return await ctx.send("Are you sure that you have the role working?")
        
        if ctx.message.channel != modschannel:
            return
        
        if message != None:
            try:
                await role.edit(mentionable=True)
                await channel.send(f"{role.mention}\n{message}")
                await role.edit(mentionable=False)      
            except discord.Forbidden:
                await ctx.send("I wasn't able to send a message in the announcement channel. Please check that I am able to talk.")
        else: 
            await ctx.send("I am unsure of what you are attempting to do.")

def setup(bot):
    bot.add_cog(announcement(bot))
