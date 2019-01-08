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

        # The only things we need from CTX are uid and cid, both of which get passed along.
        user_ID = ctx.author.id
        channel_ID = ctx.channel.id

        # The message is "assembled" here to make use of CTX.
        embed = await self.roles_embed(user_ID)
        message = await ctx.author.send(embed=embed)
        for emoji in Emoji.SELF_ASSIGNABLE_ROLES.values():
            await message.add_reaction(emoji)


    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # The bot should ignore itself.
        if payload.user_id == Configuration.get_master_var("BOT_ID"):
            return

        # This is my solution to make sure it's only reacting to things in DMs.
        if payload.guild_id != None:
            return

        await self.add_or_remove_roles(payload)



    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        # The bot should ignore itself.
        if payload.user_id == Configuration.get_master_var("BOT_ID"):
            return

        # This is my solution to make sure it's only reacting to things in DMs.
        if payload.guild_id != None:
            return

        await self.add_or_remove_roles(payload)



    async def roles_embed(self, user_ID):


        guild = self.bot.get_guild(Configuration.get_master_var("GUILD_ID"))
        member = guild.get_member(user_ID)
        role_list = "This embed shows all of the roles that are available to self assign. The Green Check mark (<:approve:528377465618563102>) means you have the role, the red X (<:deny:528385167493038080>) means you do not have that role.\nClicking the corresponding reaction will either add or remove the role you want and update this embed dynamically. If the bot isn't responding, try using the **`!roles`** command again.\n\n"
        roles_user_has = member.roles

        # Checks each of the listed self assignable roles and looks to see if you have them. At the end it looks to see what is not in the message that's going to be
        # sent and figure that if it's not there then you don't have role, then sends the message
        for has_role in roles_user_has:
            if has_role.name.lower() in assignable_roles:
                emoji_to_add = Emoji.SELF_ASSIGNABLE_ROLES[has_role.name.lower()]
                role_list += f"<:approve:528377465618563102> - {emoji_to_add}" + str(has_role)+ "\n"
                # I learned that "pass" was a thing from doing this!
                pass
            else:
                pass
        for key in assignable_roles:
            if key.lower() not in role_list.lower():
                # Grabs the Unicode emote based on the config in the Emoji.py file
                emoji_to_add = Emoji.SELF_ASSIGNABLE_ROLES[key.lower()]
                role_list += f"<:deny:528385167493038080>  - {emoji_to_add} " + str(key) + "\n"
        # Maybe I can spend some time later making it more pretty. This is pretty much copy/paste from gearbot.
        embed = discord.Embed(colour=discord.Colour(0x54d5ff), timestamp=datetime.datetime.utcfromtimestamp(time.time()),
                                  description=role_list)
        return embed

    async def add_or_remove_roles(self, payload):

        user_ID = payload.user_id
        guild = self.bot.get_guild(Configuration.get_master_var("GUILD_ID"))
        member = guild.get_member(user_ID)
        Message_id = payload.message_id

        # The goal here is if you have the role already, you lose it. If you don't, you gain it. It then edits the embed with the new role list.
        if str(payload.emoji) in Emoji.SELF_ASSIGNABLE_ROLES.values():
            for key, value in Emoji.SELF_ASSIGNABLE_ROLES.items():
                if str(value) == str(payload.emoji):
                    apple = Configuration.get_role(str(key))
                    if apple in member.roles:
                        await member.remove_roles(apple)
                        break
                    else:
                        await member.add_roles(apple)
                        break
        # Without the sleep it'll sometimes return the previous list of roles so the embed doesn't update correctly.
        await asyncio.sleep(1)
        roles_user_has = member.roles
        # Rebuilds the embed to send a new one with the updated role.
        new_embed = await self.roles_embed(user_ID)
        message_object = await self.bot.get_user(user_ID).get_message(Message_id)
        await message_object.edit(embed=new_embed)


def setup(bot):
    bot.add_cog(Role_Assigning(bot))
