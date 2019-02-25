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

class Role_Assigning(commands.Cog, name='Roles'):

    def __init__(self, bot):
        self.bot = bot



    @commands.command(hidden = True)
    async def roles(self, ctx):

        # The only things we need from CTX are uid and cid, both of which get passed along.
        user_ID = ctx.author.id

        # The message is "assembled" here to make use of CTX.
        embed = await self.roles_embed(user_ID)
        message = await ctx.author.send(embed=embed)
        for emoji in Configuration.get_var("master", "SELF_ROLES"):
            await message.add_reaction(Emoji.get_emoji(emoji))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # The bot should ignore itself.
        if payload.user_id == self.bot.user.id:
            return

        # This is my solution to make sure it's only reacting to things in DMs.
        if payload.guild_id is not None:
            return

        await self.add_or_remove_roles(payload)


    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        # The bot should ignore itself.
        if payload.user_id == self.bot.user.id:
            return

        # This is my solution to make sure it's only reacting to things in DMs.
        if payload.guild_id != None:
            return

        await self.add_or_remove_roles(payload)



    async def roles_embed(self, user_ID):

        assignable_role_names = Configuration.get_var("master", "SELF_ROLES")

        approve = Emoji.get_chat_emoji('APPROVE')
        deny = Emoji.get_chat_emoji('DENY')
        member = Configuration.get_tester(user_ID)
        role_list = f"This embed shows all of the roles that are available to self assign. The Green Check mark ({approve}) means you have the role, the red X ({deny}) means you do not have that role.\nClicking the corresponding reaction will either add or remove the role you want and update this embed dynamically. If the bot isn't responding, try using the **`!roles`** command again.\n\n"

        # Checks each of the listed self assignable roles and looks to see if you have them. At the end it looks to see what is not in the message that's going to be
        # sent and figure that if it's not there then you don't have role, then sends the message

        aquired = ""
        other = ""

        for name in assignable_role_names:
            emoji_to_add = Emoji.get_chat_emoji(name)
            role = Configuration.get_role(name)
            if role in member.roles:
                aquired += f"{approve} - {emoji_to_add} {role.name}\n"
            else:
                other += f"{deny} - {emoji_to_add} {role.name}\n"

        role_list += f"{aquired}\n{other}"



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
        assignable_role_names = Configuration.get_var("master", "SELF_ROLES")
        for name in assignable_role_names:
            emoji = Emoji.get_emoji(name)
            if str(payload.emoji) == str(emoji):
                role = Configuration.get_role(name)
                if role in member.roles:
                    await member.remove_roles(role)
                else:
                    await member.add_roles(role)
                break

        # Without the sleep it'll sometimes return the previous list of roles so the embed doesn't update correctly.
        await asyncio.sleep(1)
        # Rebuilds the embed to send a new one with the updated role.
        new_embed = await self.roles_embed(user_ID)
        message_object = await self.bot.get_user(user_ID).get_message(Message_id)
        await message_object.edit(embed=new_embed)


def setup(bot):
    bot.add_cog(Role_Assigning(bot))
