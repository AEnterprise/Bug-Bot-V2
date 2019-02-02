import json

import aioredis
from aioredis.pubsub import Receiver

import BugBot
from Utils import Configuration, BugBotLogging, ReportUtils
from Utils.Enums import ReportSource


class WebLink:

    def __init__(self, bot) -> None:
        self.bot = bot
        bot.loop.create_task(self.init())
        self.redis_link = None
        self.receiver = Receiver(loop=bot.loop)
        # add handlers here
        self.handlers = dict(
            bug_submission=self.submit
        )
        self.task = self._receiver()

    def __unload(self):
        self.bot.loop.create_task(self._unload())

    async def _unload(self):
        # cog terminted, clean up
        for c in self.receiver.channels.values():
            self.redis_link.unsubscribe(c)
        self.receiver.stop()
        self.redis_link.close()
        await self.redis_link.wait_closed()

    async def init(self):
        try:
            redis_info = Configuration.get_master_var("REDIS", dict(host="localhost", port=6379))
            self.redis_link = await aioredis.create_redis_pool(
                (redis_info["host"], redis_info["port"]),
                encoding="utf-8", db=0, maxsize=2)  # size 2: one send, one receive
            self.bot.loop.create_task(self._receiver())
            await self.redis_link.subscribe(self.receiver.channel("web-bot-messages"))
        except OSError:
            await BugBotLogging.bot_log("Failed to connect to the web api!")

    async def _receiver(self):
        async for sender, message in self.receiver.iter(encoding='utf-8', decoder=json.loads):
            try:
                reply = dict(reply=await self.handlers[message["type"]](message), uid=message["uid"])
                await self.redis_link.publish_json("bot-web-messages", reply)
            except Exception as e:
                await BugBot.handle_exception("Dash message handling", self.bot, e, None, None, None, message)

    async def submit(self, data):
        # validation has already been done by the webserver so we don't need to bother doing that again here

        # no reporting during lockdown
        if self.bot.lockdown:
            reply = dict(submitted=False, lockdown=True, message=self.bot.lockdown_message)
            await self.bot.redis.send('bot_to_web', reply)
        else:
            user = self.bot.get_user(int(data['user_id']))
            try:
                # try to send report
                id = await ReportUtils.add_report(user, data, ReportSource.form)
                reply = dict(submitted=True, lockdown=False,
                             message=f"Your report ID is {id}")
                return reply
            except Exception as ex:
                # something went wrong, notify the other side
                reply = dict(submitted=False, lockdown=False,
                             message="Something went very wrong. Mods have been notified, please try again later")
                await BugBot.handle_exception("submit processing", ex)
                return reply


def setup(bot):
    bot.add_cog(WebLink(bot))
