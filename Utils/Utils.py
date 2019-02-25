import json
from collections import namedtuple, OrderedDict
from datetime import datetime

from discord import NotFound

from Utils import BugBotLogging, Configuration
BOT = None


def initialize(bot):
    global BOT
    BOT = bot


def fetch_from_disk(filename, alternative=None):
    try:
        with open(f"{filename}.json") as file:
            return json.load(file)
    except FileNotFoundError:
        if alternative is not None:
            fetch_from_disk(alternative)
        return dict()


def save_to_disk(filename, dict):
    with open(f"{filename}.json", "w") as file:
        json.dump(dict, file, indent=4, skipkeys=True, sort_keys=True)


def escape_markdown(text):
    text = str(text)
    for c in ["\\", "`", "*", "_", "~", "|", "{"]:
        text = text.replace(c, f"\\{c}")
    return text.replace("@", "@\u200b")


async def lockdown_shutdown(bot):
    for key in Configuration.get_master_var("BUGCHANNELS").items():
        channel = Configuration.get_bugchannel(key[0])
        await channel.send(Configuration.get_var("strings", "LOCKDOWN_MESSAGE"))
        g = bot.get_guild(Configuration.get_master_var("GUILD_ID"))
        r = g.get_role(Configuration.get_master_var("GUILD_ID"))
        overwrites_everyone = channel.overwrites_for(r)
        overwrites_bh = channel.overwrites_for(Configuration.get_role("BUG_HUNTER"))
        if channel.id == Configuration.get_master_var("BUGCHANNELS").get("QUEUE"):
            overwrites_bh.send_messages = False
            await channel.set_permissions(Configuration.get_role("BUG_HUNTER"), overwrite=overwrites_bh, reason="Bot restart triggered.")
        else:
            overwrites_everyone.send_messages = False
            await channel.set_permissions(r, overwrite=overwrites_everyone, reason="Bot restart triggered.")


async def cleanExit(bot, trigger):
    await BugBotLogging.bot_log(f"Shutdown triggered by {trigger}.")
    if hasattr(bot, 'redis_link'):
        await bot.redis_link.terminate()
    await bot.aiosession.close()
    await bot.close()


def trim_message(message, limit):
    if len(message) < limit - 3:
        return message
    return f"{message[:limit-3]}..."


async def username(uid, fetch=True, clean=True):
    user = await get_user(uid, fetch)
    if user is None:
        return "UNKNOWN USER"
    if clean:
        return escape_markdown(str(user))
    else:
        return str(user)

known_invalid_users = []
user_cache = OrderedDict()


async def get_user(uid, fetch=True):
    UserClass = namedtuple("UserClass", "name id discriminator bot avatar_url created_at is_avatar_animated mention")
    user = BOT.get_user(uid)
    if user is None:
        if uid in known_invalid_users:
            return None

        if BOT.redis_link is not None:
            userCacheInfo = await BOT.redis_link.hgetall(uid)

            if len(userCacheInfo) == 8:
                userFormed = UserClass(
                    userCacheInfo["name"],
                    userCacheInfo["id"],
                    userCacheInfo["discriminator"],
                    userCacheInfo["bot"] == "1",
                    userCacheInfo["avatar_url"],
                    datetime.fromtimestamp(float(userCacheInfo["created_at"])),
                    bool(userCacheInfo["is_avatar_animated"]) == "1",
                    userCacheInfo["mention"]
                )

                return userFormed
            if fetch:
                try:
                    user = await BOT.get_user_info(uid)
                    pipeline = BOT.redis_link.pipeline()
                    pipeline.hmset_dict(uid,
                                        name=user.name,
                                        id=user.id,
                                        discriminator=user.discriminator,
                                        bot=int(user.bot),
                                        avatar_url=user.avatar_url,
                                        created_at=user.created_at.timestamp(),
                                        is_avatar_animated=int(user.is_avatar_animated()),
                                        mention=user.mention
                                        )

                    pipeline.expire(uid, 300)  # 5 minute cache life

                    BOT.loop.create_task(pipeline.execute())

                except NotFound:
                    known_invalid_users.append(uid)
                    return None
        else:  # No Redis, using the dict method instead
            if uid in user_cache:
                return user_cache[uid]
            if fetch:
                try:
                    user = await BOT.get_user_info(uid)
                    if len(user_cache) >= 10:  # Limit the cache size to the most recent 10
                        user_cache.popitem()
                    user_cache[uid] = user
                except NotFound:
                    known_invalid_users.append(uid)
                    return None
    return user
