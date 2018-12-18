import discord
from discord.ext import commands

import Configuration


def is_employee():
    async def predicate(ctx):
        return [r for r in ctx.author.roles if (r.id == Configuration.get_master_var("EMPLOYEE") or r.id == Configuration.get_master_var("ADMINS"))]
    return commands.check(predicate)

def is_modinator():
    async def predicate(ctx):
        return [r for r in ctx.author.roles if r.id == Configuration.get_master_var("MODINATOR")]
    return commands.check(predicate)

def is_bug_hunter():
    async def predicate(ctx):
        return [r for r in ctx.author.roles if r.id == Configuration.get_master_var("BUG_HUNTER")]
    return commands.check(predicate)
