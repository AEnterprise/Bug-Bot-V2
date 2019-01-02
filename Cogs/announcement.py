import discord
from discord.ext import commands

from Utils import Configuration
from Utils import Checks


class Announcement:
    def __init__(self,bot):
        self.bot = bot
            
    @Checks.is_employee()
    @commands.bot_has_permissions(manage_roles=True)       
    @commands.command()
    async def announce(self, ctx: commands.Context, role_name, *, message):
        role = Configuration.get_role(role_name)
        channel = Configuration.get_channel(role_name)
        modschannel = Configuration.get_channel("modinator")

        if role is None:
            return await ctx.send("This role may be either deleted or not configured properly.")
        
        if ctx.message.channel != modschannel:
            return await ctx.send("This feature only works in the modinator channel. Sorry about it!")
        
        if message != None:
            await role.edit(mentionable=True)
            try:
                await channel.send(f"{role.mention}\n{message}") 
            except discord.Forbidden:
                await ctx.send("I wasn't able to send a message in the announcement channel. Please check that I am able to talk.")
            await role.edit(mentionable=False)
        else: 
            await ctx.send("I am unsure of what you are attempting to do.")

    @Checks.is_employee()
    @commands.command()
    async def update(self, ctx: commands.Context, role_name, message_id: int, *, new_message):
        channel = Configuration.get_channel(role_name)
        modschannel = Configuration.get_channel("modinator")
        try:
            message = await channel.get_message(message_id)
        except discord.Forbidden:
            return await ctx.send("Hmmm.. Seems like I no longer have READ_MESSAGES permission for that channel for some reason.")
        except discord.NotFound:
            return await ctx.send("It is possible that you gave me the wrong ID or I cannot find the message in the channel due to either the message or channel being deleted.")
        if channel is None:
            return await ctx.send("Are you sure this is in a correct channel?")
        if ctx.message.channel != modschannel:
            return await ctx.send("This feature only works in the modinator channel. Sorry about it!")
        if message != None:
            try:
                await message.edit(content=f"{new_message}")
            except discord.Forbidden:
                await ctx.send("it appears that my SEND_MESSAGES perms have been revoked and I cannot edit the message.")
        else:
            await ctx.send("I'm not really sure what you are trying to do.")

def setup(bot):
    bot.add_cog(Announcement(bot))
