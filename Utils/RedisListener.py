import json
import asyncio
import aioredis
from aioredis.pubsub import Receiver

from Utils import Configuration


class Listener:

    def __init__(self, loop):
        self.loop = loop
        self.conn = None
        self.inbound = {}

    async def initialize(self):
        redis_info = Configuration.get_master_var("REDIS", dict(host="localhost", port=6379))
        self.conn = await aioredis.create_redis_pool((redis_info["host"], redis_info["port"]), encoding="utf-8", maxsize=2)
        self.receiver = Receiver(loop=self.loop)
        self.task = self.loop.create_task(self.fetcher())
        # await BugBotLogging.bot_log('Redis connection established')  # FIXME - won't work for the webserver

    async def subscribe(self, channel, handler, err_handler):
        await self.conn.subscribe(self.receiver.channel(channel))
        self.inbound[channel] = (handler, err_handler)
        # await BugBotLogging.bot_log(f'Redis receiver is now subscribed to the {channel} channel')  # FIXME - won't work for the webserver

    async def terminate(self):
        # terminate channels and disconnect from redis
        for c in self.receiver.channels.values():
            self.conn.unsubscribe(c)
        self.task.cancel()
        self.receiver.stop()
        self.conn.close()
        await self.conn.wait_closed()

    async def fetcher(self):
        async for sender, message in self.receiver.iter(encoding='utf-8', decoder=json.loads):
            channel = sender.name.decode()
            if channel in self.inbound:
                try:
                    await self.inbound[channel][0](message)
                except Exception as e:
                    await self.inbound[channel][1]('Receiver failure!', e)

    async def send(self, channel, data):
        subs = await self.conn.pubsub_numsub(channel)
        if channel in subs and int(subs[channel]) > 0:
            await self.conn.publish_json(channel, data)
