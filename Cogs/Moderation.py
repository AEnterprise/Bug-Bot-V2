
import discord
from discord.ext import commands

from Utils import BugBotLogging, Checks, Configuration, Emoji


class Moderation:

    def __init__(self, bot):
        self.bot = bot
        self.lockdown_running = False
        self.lockdown_message = ""
        self.locked_channels = []

    async def lockdown_edit_message(self, ctx, new_message):
        if self.lockdown_running is False:
            return await ctx.send("There is no lockdown running.")
        for channels in self.locked_channels:
            bugreportchannel = ctx.guild.get_channel(channels)
            async for message in bugreportchannel.history(limit=5):
                if message.content == self.lockdown_message:
                    await message.edit(content=new_message)
        await ctx.send(f"{Emoji.get_chat_emoji('YES')} Successfully edited your lockdown message.")
        self.lockdown_message = new_message

    async def lockdown_trigger_all(self, ctx, reason):
        for key in Configuration.get_master_var("BUGCHANNELS").items():
            bugreportchannel = ctx.guild.get_channel(key[1])
            self.locked_channels.append(bugreportchannel.id)
            await bugreportchannel.send(reason)
            g = self.bot.get_guild(Configuration.get_master_var("GUILD_ID"))
            r = g.get_role(Configuration.get_master_var("GUILD_ID"))
            overwrites_everyone = bugreportchannel.overwrites_for(r)
            overwrites_bh = bugreportchannel.overwrites_for(Configuration.get_role("BUG_HUNTER"))
            if bugreportchannel.id == Configuration.get_master_var("BUGCHANNELS").get("QUEUE"):
                overwrites_bh.send_messages = False
                await bugreportchannel.set_permissions(Configuration.get_role("BUG_HUNTER"), overwrite=overwrites_bh, reason=f"Lockdown initiated by {ctx.author} for reason: {reason}")
            else:
                overwrites_everyone.send_messages = False
                await bugreportchannel.set_permissions(r, overwrite=overwrites_everyone, reason=f"Lockdown initiated by {ctx.author} for reason: {reason}")
        await ctx.send(f"{Emoji.get_chat_emoji('YES')} Successfully put all specified channels on lockdown.")
        self.lockdown_message = reason
        self.lockdown_running = True

    async def lockdown_trigger(self, ctx, channel, reason):
        for key in Configuration.get_master_var("BUGCHANNELS").items():
            for channels in channel:
                if channels.id != key[1]:
                    continue
                self.locked_channels.append(channels.id)
                await channels.send(reason)
                g = self.bot.get_guild(Configuration.get_master_var("GUILD_ID"))
                r = g.get_role(Configuration.get_master_var("GUILD_ID"))
                overwrites_everyone = channels.overwrites_for(r)
                overwrites_bh = channels.overwrites_for(Configuration.get_role("BUG_HUNTER"))
                if channels.id == Configuration.get_master_var("BUGCHANNELS").get("QUEUE"):
                    overwrites_bh.send_messages = False
                    await channels.set_permissions(Configuration.get_role("BUG_HUNTER"), overwrite=overwrites_bh, reason=f"Lockdown initiated by {ctx.author} for reason: {reason}")
                else:
                    overwrites_everyone.send_messages = False
                    await channels.set_permissions(r, overwrite=overwrites_everyone, reason=f"Lockdown initiated by {ctx.author} for reason: {reason}")
        await ctx.send(f"{Emoji.get_chat_emoji('YES')} Successfully put all specified channels on lockdown.")
        self.lockdown_message = reason
        self.lockdown_running = True

    async def unlock_trigger(self, ctx):
        if self.lockdown_running is False:
            return await ctx.send("There is no lockdown running.")
        for channels in self.locked_channels:
            locked_channel = ctx.guild.get_channel(channels)
            g = self.bot.get_guild(Configuration.get_master_var("GUILD_ID"))
            r = g.get_role(Configuration.get_master_var("GUILD_ID"))
            overwrites_everyone = locked_channel.overwrites_for(r)
            overwrites_bh = locked_channel.overwrites_for(Configuration.get_role("BUG_HUNTER"))
            if locked_channel.id == Configuration.get_master_var("BUGCHANNELS").get("QUEUE"):
                overwrites_bh.send_messages = True
                await locked_channel.set_permissions(Configuration.get_role("BUG_HUNTER"), overwrite=overwrites_bh, reason=f"Unlock initiated by {ctx.author}.")
            else:
                overwrites_everyone.send_messages = True
                await locked_channel.set_permissions(r, overwrite=overwrites_everyone, reason=f"Lockdown initiated by {ctx.author}.")
            async for message in locked_channel.history(limit=5):
                if message.content == self.lockdown_message:
                    await message.delete()
        await ctx.send(f"{Emoji.get_chat_emoji('YES')} Successfully unlocked all channels from lockdown.")
        self.lockdown_running = False

    @commands.command()
    @Checks.is_modinator()
    async def lockdown(self, ctx: commands.Context, channel: commands.Greedy[discord.TextChannel], reason: str):
        await self.lockdown_trigger(ctx, channel, reason)
    
    @commands.command()
    @Checks.is_modinator()
    async def lockdown_edit(self, ctx, new_message: str):
        await self.lockdown_edit_message(ctx, new_message)
    
    @commands.command()
    @Checks.is_modinator()
    async def lockdown_all(self, ctx, reason: str):
        await self.lockdown_trigger_all(ctx, reason)
    
    @commands.command()
    @Checks.is_modinator()
    async def unlock(self, ctx):
        await self.unlock_trigger(ctx)

    @commands.command()
    @Checks.is_modinator()
    async def slowmode(self, ctx: commands.Context, channel: discord.TextChannel, interval: int):
        if interval > 120:
            return await ctx.send('You can only set the slowmode interval up to 120 seconds')
        if channel.slowmode_delay == interval:
            return await ctx.send(f'The slowmode interval is already set to `{interval} seconds` on {channel}')
        try:
            await channel.edit(slowmode_delay=interval)
        except (discord.Forbidden, discord.HTTPException):
            await ctx.send(f'Failed to apply slowmode on {channel}')
            raise
        else:
            await BugBotLogging.bot_log(f':timer: {ctx.author} set the slowmode interval to `{interval} seconds` on {channel}')
            await ctx.send(f'Successfully set the slowmode interval to `{interval} seconds` on {channel}')

    @commands.command()
    @Checks.is_modinator()
    async def verification(self, ctx: commands.Context, level: str, *, reason: str = None):
        vl = discord.VerificationLevel.__members__.get(level.lower())
        if vl is not None:
            if ctx.guild.verification_level != vl:
                try:
                    await ctx.guild.edit(verification_level=vl, reason=reason)
                except discord.Forbidden:
                    await ctx.send('Not allowed to change the verification level')
                except discord.HTTPException:
                    await ctx.send('An error occurred when changing the verification level')
                    raise
                else:
                    if reason is None:
                        reason = ''
                    else:
                        reason = f' with reason `{reason}`'
                    await BugBotLogging.bot_log(f':vertical_traffic_light: {ctx.author} changed the server verification level to `{level}`{reason}')
                    await ctx.send(f'Server verification level successfully changed to `{level}`')
            else:
                await ctx.send(f'The server verification level is already set to `{level}`')
        else:
            av = ', '.join(discord.VerificationLevel.__members__.keys())
            await ctx.send(f'That level name doesn\'t seem to be valid. Acceptable values include: `{av}`')


def setup(bot):
    bot.add_cog(Moderation(bot))
