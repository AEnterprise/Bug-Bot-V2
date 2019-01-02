import discord
from discord.ext import commands

from Utils import Checks, BugBotLogging


class Moderation:

    def __init__(self, bot):
        self.bot = bot

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
