import discord
from discord.ext import commands

from Utils import Configuration


def is_employee():
    async def predicate(ctx):
        if hasattr(ctx.author, 'roles'):
            roles = ctx.author.roles
        else:
            member = ctx.bot.get_guild(Configuration.get_master_var("GUILD_ID")).get_member(ctx.author.id)
            roles = member.roles if member is not None else []
        return [r for r in roles if (r == Configuration.get_role("EMPLOYEE") or r == Configuration.get_role("ADMINS"))]
    return commands.check(predicate)


def is_modinator():
    async def predicate(ctx):
        if hasattr(ctx.author, 'roles'):
            roles = ctx.author.roles
        else:
            member = ctx.bot.get_guild(Configuration.get_master_var("GUILD_ID")).get_member(ctx.author.id)
            roles = member.roles if member is not None else []
        return [r for r in roles if r == Configuration.get_role("MODINATOR")]
    return commands.check(predicate)


def is_bug_hunter():
    async def predicate(ctx):
        if hasattr(ctx.author, 'roles'):
            roles = ctx.author.roles
        else:
            member = ctx.bot.get_guild(Configuration.get_master_var("GUILD_ID")).get_member(ctx.author.id)
            roles = member.roles if member is not None else []
        return [r for r in roles if r == Configuration.get_role("BUG_HUNTER")]
    return commands.check(predicate)


def dm_only():
    async def predicate(ctx):
        return ctx.guild is None
    return commands.check(predicate)
