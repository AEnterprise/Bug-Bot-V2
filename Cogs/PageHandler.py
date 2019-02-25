import discord
from discord.ext import commands

from Utils import Emoji, Pages


class PageHandler(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        user = None
        if guild is not None:
            user = guild.get_member(payload.user_id)
        if self.bot.user.id == payload.user_id:
            return
        try:
            message = await self.bot.get_channel(payload.channel_id).get_message(payload.message_id)
        except discord.NotFound:
            pass
        else:
            if str(payload.emoji) == str(Emoji.get_emoji('LEFT')):
                if await Pages.update(self.bot, message, "PREV", payload.user_id) and user is not None:
                    try:
                        await message.remove_reaction(Emoji.get_emoji('LEFT'), user)
                    except discord.Forbidden:
                        pass
            elif str(payload.emoji) == str(Emoji.get_emoji('RIGHT')):
                if await Pages.update(self.bot, message, "NEXT", payload.user_id) and user is not None:
                    try:
                        await message.remove_reaction(Emoji.get_emoji('RIGHT'), user)
                    except discord.Forbidden:
                        pass


def setup(bot):
    bot.add_cog(PageHandler(bot))
