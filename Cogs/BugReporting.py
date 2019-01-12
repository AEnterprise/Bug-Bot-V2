import asyncio

import discord
from discord.ext import commands

from Utils import BugBotLogging, Configuration, Utils
from Utils.DataUtils import Storeinfo
from Utils.Enums import Platforms


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

def setup(bot):
    bot.add_cog(BugReporting(bot))
