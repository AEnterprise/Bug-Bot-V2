import aioredis

from Utils import Configuration

redis_connection = None
inbound = None
outbound = None


def has_redis():
    return redis_connection is not None


async def initialize(loop, input, out, receiver, error_handler):
    # get ready
    global redis_connection, inbound, outbound
    #connect to redis
    redis_info = Configuration.get_master_var("REDIS", dict(host="localhost", port=6379))
    redis_connection = await aioredis.create_redis_pool((redis_info["host"], redis_info["port"]), encoding="utf-8", maxsize=2)
    # create channels
    inbound = (await redis_connection.psubscribe(input))[0]
    outbound = (await redis_connection.psubscribe(out))[0]
    # throw the receiver on the loop
    loop.create_task(fetcher(receiver, error_handler))
    print(f"Redis connection established, listening on {input}, sending to {out}")


def terminate():
    # terminate channels and disconnect from redis
    global redis_connection
    redis_connection.unsubscribe(inbound, outbound)
    redis_connection.close()


async def fetcher(receiver, error_handler):
    # keep listening as long as we didn't terminate the channel yet
    while inbound.is_active:
        try:
            channel, data = await inbound.get_json()
            await receiver(data)
        except Exception as ex:
            await error_handler("Receiver failure!", ex)


async def send(object):
    # just a helper to send something to the other side
    await redis_connection.publish_json(outbound.name, object)
