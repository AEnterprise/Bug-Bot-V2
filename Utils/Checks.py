import discord
from discord.ext import commands
from discord.ext.commands import CheckFailure

from Utils import Configuration


def is_employee():
    async def predicate(ctx):
        if hasattr(ctx.author, 'roles'):
            user = ctx.author
        else:
            user = Configuration.get_tester(ctx.author.id)
        return is_admin(user)

    return commands.check(predicate)


def is_modinator():
    async def predicate(ctx):
        if hasattr(ctx.author, 'roles'):
            user = ctx.author
        else:
            user = Configuration.get_tester(ctx.author.id)
        return is_mod(user)

    return commands.check(predicate)


def is_hunter(user):
    return [r for r in user.roles if r == Configuration.get_role("BUG_HUNTER")]


def is_mod(user):
    if user is None:
        return False
    return [r for r in user.roles if r == Configuration.get_role("MODINATOR")] or is_admin(user)


def is_admin(user):
    if user is None:
        return False
    return [r for r in user.roles if (r == Configuration.get_role("EMPLOYEE") or r == Configuration.get_role("ADMINS"))]


def is_bug_hunter():
    async def predicate(ctx):
        if hasattr(ctx.author, 'roles'):
            user = ctx.author
        else:
            user = ctx.bot.get_guild(Configuration.get_master_var("GUILD_ID")).get_member(ctx.author.id)
        return is_hunter(user)

    return commands.check(predicate)


class DMOnly(CheckFailure):
    pass


def dm_only():
    async def predicate(ctx):
        if ctx.guild is None:
            return True
        raise DMOnly()

    return commands.check(predicate)
