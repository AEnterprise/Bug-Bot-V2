import discord
from discord.ext import commands

from Utils import Configuration


def is_employee():
    async def predicate(ctx):
        return [r for r in ctx.author.roles if (r == Configuration.get_role(ctx, "EMPLOYEE") or r == Configuration.get_role(ctx, "ADMINS"))]
    return commands.check(predicate)

def is_modinator():
    async def predicate(ctx):
        return [r for r in ctx.author.roles if r == Configuration.get_role(ctx, "MODINATOR")]
    return commands.check(predicate)

def is_bug_hunter():
    async def predicate(ctx):
        return [r for r in ctx.author.roles if r == Configuration.get_role(ctx, "BUG_HUNTER")]
    return commands.check(predicate)
