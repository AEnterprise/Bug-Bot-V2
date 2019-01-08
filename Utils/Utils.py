import json
import discord
from Utils import BugBotLogging, Configuration

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
    for c in ("\\", "`", "*", "_", "~", "<"):
        text = text.replace(c, f"\{c}\u200b")
    return text.replace("@", "@\u200b")


async def lockdown_shutdown(bot):
    for key in Configuration.get_master_var("BUGCHANNELS").items():
        for x in range(1):
            channel = Configuration.get_bugchannel(key[0])
            await channel.send(Configuration.get_master_var("STRINGS").get("LOCKDOWN_MESSAGE"))
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
    await bot.aiosession.close()
    await bot.logout()
    await bot.close()

def trim_message(message, limit):
    if len(message) < limit - 3:
        return message
    return f"{message[:limit-3]}..."
