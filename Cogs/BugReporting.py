import asyncio

import discord
from discord.ext import commands

import BugBot
from Utils import Configuration, RedisListener, BugBotLogging


class BugReporting:
    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(RedisListener.initialize(bot.loop, "web_to_bot", "bot_to_web", self.process_report, BugBot.handle_exception))

    async def process_report(self, report):
        await BugBotLogging.bot_log(f"INCOMMING REPORT: {report}")

    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return
        if message.channel.id not in Configuration.list_of_bugchannels_ids():
            return
        ctx = await self.bot.get_context(message)
        if ctx.command is None:
            await message.channel.send(
                Configuration.get_master_var('STRINGS').get('NON_COMMANDS_MSG').format(user=message.author.mention),
                delete_after=5)
            await asyncio.sleep(5)
            await message.delete()


def setup(bot):
    bot.add_cog(BugReporting(bot))
