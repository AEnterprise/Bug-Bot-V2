import asyncio
import os
import sys
import time
import traceback
from argparse import ArgumentParser
from datetime import datetime

import aiohttp
from discord import Activity, Embed, Colour
from discord.abc import PrivateChannel
from discord.ext import commands

import Utils
from Utils import BugBotLogging, Configuration, Emoji, Pages, Utils, Trello, DataUtils, RedisMessager, Checks

bugbot = commands.Bot(command_prefix="!", case_insensitive=True)
bugbot.STARTUP_COMPLETE = False


async def restart_cleanup():
    for key in Configuration.get_master_var("BUGCHANNELS").items():
        channel = Configuration.get_bugchannel(key[0])
        async for message in channel.history(limit=1):
            if message.author.id == bugbot.user.id:
                if message.content == Configuration.get_var("strings", "LOCKDOWN_MESSAGE"):
                    await message.delete()
        g = bugbot.get_guild(Configuration.get_master_var("GUILD_ID"))
        r = g.get_role(Configuration.get_master_var("GUILD_ID"))
        overwrites_everyone = channel.overwrites_for(r)
        overwrites_bh = channel.overwrites_for(Configuration.get_role("BUG_HUNTER"))
        if channel.id == Configuration.get_master_var("BUGCHANNELS").get("QUEUE"):
            overwrites_bh.send_messages = True
            await channel.set_permissions(Configuration.get_role("BUG_HUNTER"), overwrite=overwrites_bh, reason="Bot unlock after previous restart..")
        else:
            overwrites_everyone.send_messages = True
            await channel.set_permissions(r, overwrite=overwrites_everyone, reason="Bot unlock after previous restart..")


@bugbot.event
async def on_ready():
    # load cogs upon startup
    if not bugbot.STARTUP_COMPLETE:
        Pages.initialize()
        Emoji.initialize(bugbot)
        Configuration.initialize(bugbot)
        DataUtils.init()
        await BugBotLogging.initialize(bugbot)
        bugbot.aiosession = aiohttp.ClientSession()
        BugBotLogging.info("Loading cogs...")
        for extension in Configuration.get_master_var("COGS"):
            try:
                bugbot.load_extension("Cogs." + extension)
            except Exception as e:
                BugBotLogging.exception(f"Failed to load extention {extension}", e)
        BugBotLogging.info("Cogs loaded")
        bugbot.trello = Trello.TrelloUtils(bugbot)
        bugbot.loop.create_task(keepDBalive())  # ping DB every hour so it doesn't disconnect
        await restart_cleanup()
        await BugBotLogging.bot_log("Here we go!")
        bugbot.STARTUP_COMPLETE = True
    # we got the ready event, usually means we resumed, make sure the status is still there
    await bugbot.change_presence(activity=Activity(type=3, name='over the bug boards'))


async def keepDBalive():
    while not bugbot.is_closed():
        DataUtils.connection.connection().ping(True)
        await asyncio.sleep(3600)


@bugbot.event
async def on_command_error(ctx: commands.Context, error):
    # lots of things can go wrong with commands, let's make sure we handle them nicely where appropriate
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send("This command cannot be used in private messages.", delete_after=10)
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(error, delete_after=10)
    elif isinstance(error, Checks.DMOnly):
        await ctx.send("This command can only be used in DMs", delete_after=10)
    elif isinstance(error, commands.CheckFailure):
        await ctx.send(":lock: You do not have the required permissions to run this command", delete_after=10)
    elif isinstance(error, commands.CommandOnCooldown):
        # not sure if we're even gona have cooldowns, just here just in case
        await ctx.send(error)
    elif isinstance(error, commands.MissingRequiredArgument):
        param = list(ctx.command.params.values())[min(len(ctx.args) + len(ctx.kwargs), len(ctx.command.params))]
        await ctx.send(f"{Emoji.get_chat_emoji('NO')} You are missing a required command argument: `{param.name}`\n{Emoji.get_chat_emoji('WRENCH')} Command usage: `{ctx.prefix.replace(ctx.me.mention,f'@{ctx.me.name}') + ctx.command.signature}`", delete_after=10)
    elif isinstance(error, commands.BadArgument):
        param = list(ctx.command.params.values())[min(len(ctx.args) + len(ctx.kwargs), len(ctx.command.params))]
        await ctx.send(f"{Emoji.get_chat_emoji('NO')} Failed to parse the ``{param.name}`` param: ``{error}``\n{Emoji.get_chat_emoji('WRENCH')} Command usage: `{ctx.prefix.replace(ctx.me.mention,f'@{ctx.me.name}') + ctx.command.signature}`", delete_after=10)
    elif isinstance(error, commands.CommandNotFound):
        return

    else:
        await handle_exception("Command execution failed", error.original, ctx=ctx)
        # notify caller
        await ctx.send(":rotating_light: Something went wrong while executing that command :rotating_light:", delete_after=10)

    await asyncio.sleep(10)
    await ctx.message.delete()


def extract_info(o):
    info = ""
    if hasattr(o, "__dict__"):
        info += str(o.__dict__)
    elif hasattr(o, "__slots__"):
        items = dict()
        for slot in o.__slots__:
            try:
                items[slot] = getattr(o, slot)
            except AttributeError:
                pass
        info += str(items)
    else:
        info += str(o) + " "
    return info


@bugbot.event
async def on_error(event, *args, **kwargs):
    t, exception, info = sys.exc_info()
    await handle_exception("Event handler failure", exception, event, None, None, *args, **kwargs)


async def handle_exception(exception_type, exception, event=None, message=None, ctx=None, *args, **kwargs):
    embed = Embed(colour=Colour(0xff0000),
                  timestamp=datetime.utcfromtimestamp(time.time()))

    # something went wrong and it might have been in on_command_error, make sure we log to the log file first
    lines = [
        "\n===========================================EXCEPTION CAUGHT, DUMPING ALL AVAILABLE INFO===========================================",
        f"Type: {exception_type}"
    ]

    arg_info = ""
    for arg in list(args):
        arg_info += extract_info(arg) + "\n"
    if arg_info == "":
        arg_info = "No arguments"

    kwarg_info = ""
    for name, arg in kwargs.items():
        kwarg_info += "{}: {}\n".format(name, extract_info(arg))
    if kwarg_info == "":
        kwarg_info = "No keyword arguments"

    lines.append("======================Exception======================")
    lines.append(f"{str(exception)} ({type(exception)})")

    lines.append("======================ARG INFO======================")
    lines.append(arg_info)

    lines.append("======================KWARG INFO======================")
    lines.append(kwarg_info)

    lines.append("======================STACKTRACE======================")
    tb = "".join(traceback.format_tb(exception.__traceback__))
    lines.append(tb)

    if message is None and event is not None and hasattr(event, "message"):
        message = event.message

    if message is None and ctx is not None:
        message = ctx.message

    if message is not None and hasattr(message, "content"):
        lines.append("======================ORIGINAL MESSAGE======================")
        lines.append(message.content)
        if message.content is None or message.content == "":
            content = "<no content>"
        else:
            content = message.content
        embed.add_field(name="Original message", value=Utils.trim_message(content, 1000), inline=False)

        lines.append("======================ORIGINAL MESSAGE (DETAILED)======================")
        lines.append(extract_info(message))

    if event is not None:
        lines.append("======================EVENT NAME======================")
        lines.append(event)
        embed.add_field(name="Event", value=event)

    if ctx is not None:
        lines.append("======================COMMAND INFO======================")

        lines.append(f"Command: {ctx.command}")
        embed.add_field(name="Command", value=ctx.command)

        channel_name = 'Private Message' if isinstance(ctx.channel,
                                                       PrivateChannel) else f"{ctx.channel.name} (`{ctx.channel.id}`)"
        lines.append(f"Channel: {channel_name}")
        embed.add_field(name="Channel", value=channel_name, inline=False)

        sender = f"{ctx.author.name}#{ctx.author.discriminator} (`{ctx.author.id}`)"
        lines.append(f"Sender: {sender}")
        embed.add_field(name="Sender", value=sender, inline=False)

    lines.append(
        "===========================================DATA DUMP COMPLETE===========================================")
    BugBotLogging.error("\n".join(lines))

    # nice embed for info on discord

    embed.set_author(name=exception_type)
    embed.add_field(name="Exception", value=f"{str(exception)} (`{type(exception)}`)", inline=False)
    parts = Pages.paginate(tb, max_chars=1024)
    num = 1
    for part in parts:
        embed.add_field(name=f"Traceback {num}/{len(parts)}", value=part)
        num += 1

    # try logging to botlog, wrapped in an try catch as there is no higher lvl catching to prevent taking down the bot (and if we ended here it might have even been due to trying to log to botlog
    try:
        await BugBotLogging.bot_log(embed=embed)
    except Exception as ex:
        BugBotLogging.error(
            f"Failed to log to botlog, either Discord broke or something is seriously wrong!\n{ex}")
        BugBotLogging.error(traceback.format_exc())


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--token", help="Specify your Discord token")

    BugBotLogging.init_logger()

    clargs = parser.parse_args()
    if 'bugbotlogin' in os.environ:
        token = os.environ['bugbotlogin']
    elif clargs.token:
        token = clargs.token
    elif not Configuration.get_master_var("LOGIN_TOKEN", "0") is "0":
        token = Configuration.get_master_var("LOGIN_TOKEN")
    else:
        token = input("Please enter your Discord token: ")
    BugBotLogging.info("BugBot taking off to collect the bugs!")
    bugbot.run(token)
    BugBotLogging.info("Time for a nap, bugs will still be here later")
