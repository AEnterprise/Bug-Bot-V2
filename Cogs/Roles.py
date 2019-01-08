import contextlib
import io
import textwrap
import traceback
import time
import discord
import datetime
import asyncio
from discord import Member

from discord.ext import commands

from Utils import Pages, Utils, Emoji, Configuration

assignable_roles = [

    "ios", "android", "linux", "not employee", "admin", "employee"
    ]


class Role_Assigning:

    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden = True)
    async def roles(self, ctx):

        roles_user_has = ctx.author.roles
        user_ID = ctx.author.id
        channel_ID = ctx.channel.id
        Member_to_dm = discord.Member

        embed = await self.roles_embed(user_ID, channel_ID, roles_user_has)
        dm_channel_id = await discord.User.dm_channel(Member_to_dm)
        message = await dm_channel_id.send(embed=embed)
        for emoji in Emoji.SELF_ASSIGNABLE_ROLES.values():
            await message.add_reaction(emoji)


    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == 422786385015996439:
            return

        channel_ID = payload.channel_id
        user_ID = payload.user_id
        channel = self.bot.get_channel(channel_ID)
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(user_ID)
        Message_id = payload.message_id

        if str(payload.emoji) in Emoji.SELF_ASSIGNABLE_ROLES.values():
            for key, value in Emoji.SELF_ASSIGNABLE_ROLES.items():
                if str(value) == str(payload.emoji):
                    apple = Configuration.get_role(str(key))
                    await member.add_roles(apple)
                    await asyncio.sleep(1)
                    roles_user_has = member.roles
                    new_embed = await self.roles_embed(user_ID, channel_ID, roles_user_has)
                    message_object = await channel.get_message(Message_id)
                    await message_object.edit(embed=new_embed)
                    break

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == 422786385015996439:
            return

        channel_ID = payload.channel_id
        user_ID = payload.user_id
        channel = self.bot.get_channel(channel_ID)
        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(user_ID)
        Message_id = payload.message_id

        if str(payload.emoji) in Emoji.SELF_ASSIGNABLE_ROLES.values():
            for key, value in Emoji.SELF_ASSIGNABLE_ROLES.items():
                if str(value) == str(payload.emoji):
                    apple = Configuration.get_role(str(key))
                    await member.remove_roles(apple)
                    await asyncio.sleep(1)
                    roles_user_has = member.roles
                    new_embed = await self.roles_embed(user_ID, channel_ID, roles_user_has)
                    message_object = await channel.get_message(Message_id)
                    await message_object.edit(embed=new_embed)
                    break

    async def roles_embed(self, user_ID, channel_ID, roles_user_has):

        channel = self.bot.get_channel(channel_ID)
        guild = self.bot.get_guild(Configuration.get_master_var("GUILD_ID"))
        member = guild.get_member(user_ID)
        role_list = "Here are the roles you have.Use the reactions below to add the relevant role to yourself on REACTION ADD. To remove the role from yourself, REMOVE the relevant reaction\n"

        for has_role in roles_user_has:
            if has_role.name.lower() in assignable_roles:
                emoji_to_add = Emoji.SELF_ASSIGNABLE_ROLES[has_role.name.lower()]
                role_list += f"<:approve:528377465618563102> - {emoji_to_add}" + str(has_role)+ "\n"
                pass
            else:
                pass
        for key in assignable_roles:
            if key.lower() not in role_list.lower():
                emoji_to_add = Emoji.SELF_ASSIGNABLE_ROLES[key.lower()]
                role_list += f"<:deny:528385167493038080>  - {emoji_to_add}" + str(key) + "\n"
        embed = discord.Embed(colour=discord.Colour(0x54d5ff), timestamp=datetime.datetime.utcfromtimestamp(time.time()),
                                  description=role_list)
        return embed



def setup(bot):
    bot.add_cog(Role_Assigning(bot))
