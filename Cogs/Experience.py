import math
import asyncio
from datetime import timedelta

import discord
from discord.ext import commands

from Utils import Checks, BugBotLogging, Configuration, Pages, ExpUtils
from Utils.Enums import TransactionEvent

from Utils.ExpUtils import InvalidItemError, OutOfStockError, InsufficientBalanceError


class Experience:

    def __init__(self, bot):
        self.bot = bot
        self._bug_check = bot.loop.create_task(self.process_bug_xp())
        self._expiry_check = bot.loop.create_task(self.check_expiry())
        Pages.register('store', self.init_store, self.update_store)

    def __unload(self):
        self._bug_check.cancel()
        self._expiry_check.cancel()
        Pages.unregister('store')

    async def process_bug_xp(self):
        # TODO: Eventually need something to consume Trello webhooks (polling for now)
        try:
            while not self.bot.is_closed():
                # Get bugs that need to be verified
                pending_bugs = ExpUtils.get_xp_pending_bugs()
                # Create batches of cards to reduce Trello calls
                batches = []
                batch = {}
                for bug in pending_bugs:
                    batch[bug.trello_id] = bug.id
                    if len(batch) > 9:
                        batches.append(batch)
                        batch = {}
                if len(batch) > 0:
                    batches.append(batch)
                for b in batches:
                    # Get card data from Trello for this batch
                    cards = await self.bot.trello.batch_get_cards(b.keys())
                    for idx, c in enumerate(cards):
                        if '200' not in c:
                            await BugBotLogging.bot_log(f':warning: Error with batch call on card ID {b.keys()[idx]}: {c["message"]} ({c["statusCode"]})')
                            continue
                        card = c['200']
                        card_id = card['shortLink']
                        # If the card was archived as new (i.e. approved dupe)
                        if card['closed'] and card['idList'] in Configuration.get_var('bugbot', 'TRELLO').get('NEW_LISTS'):
                            ExpUtils.award_bug_xp(b[card_id], 0, self.bot.user.id)
                            await BugBotLogging.bot_log(f':eye_in_speech_bubble: Bug `{card_id}` was archived during verification')
                        # If the card is in one of the dead bug/won't fix/CNR lists
                        elif card['idList'] in Configuration.get_var('bugbot', 'TRELLO').get('DEAD_BUG_LISTS'):
                            amount = Configuration.get_var('bugbot', 'XP').get('DEAD_BUG')
                            user_id = ExpUtils.award_bug_xp(b[card_id], amount, self.bot.user.id)
                            await BugBotLogging.bot_log(f':eye_in_speech_bubble: Bug `{card_id}` marked as dead. Gave {amount} XP to {user_id}')
                        else:
                            # Loop through the priority label sets (P0 - P3)
                            for severity, data in Configuration.get_var('bugbot', 'TRELLO').get('PRIORITIES').items():
                                if any([x for x in card['labels'] if x['id'] in data['LABELS']]):
                                    amount = Configuration.get_var('bugbot', 'XP').get('VERIFIED_BUG') + data['XP_BONUS']
                                    user_id = ExpUtils.award_bug_xp(b[card_id], amount, self.bot.user.id)
                                    await BugBotLogging.bot_log(f':eye_in_speech_bubble: Bug `{card_id}` verified as {severity}. Gave {amount} XP to {user_id}')
                                    break
                    await asyncio.sleep(1)
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass
        except discord.ConnectionClosed:
            self._bug_check.cancel()
            self._bug_check = self.bot.loop.create_task(self.process_bug_xp())

    async def check_expiry(self):
        try:
            while not self.bot.is_closed():
                # Get (and mark as expired) any temporary roles that have expired
                expired = ExpUtils.expire_roles()
                if len(expired) > 0:
                    dt = self.bot.get_guild(Configuration.get_master_var('GUILD_ID'))
                    for e in expired:
                        member = dt.get_member(e[0])
                        role = dt.get_role(e[1])
                        if member is not None and role is not None:
                            try:
                                await member.remove_roles(role, reason='XP purchase expired')
                            except (discord.Forbidden, discord.HTTPException):
                                await BugBotLogging.bot_log(f':warning: Unable to remove expired role {role.name} from {member}')
                                raise
                            else:
                                await BugBotLogging.bot_log(f':alarm_clock: Removed expired {role.name} role from {member}')
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass
        except discord.ConnectionClosed:
            self._expiry_check.cancel()
            self._expiry_check = self.bot.loop.create_task(self.check_expiry())

    def build_store_embed(self, page_num, total_pages, only_in_stock):
        items = ExpUtils.get_store_items(page_num + 1, only_in_stock)
        em = discord.Embed()
        em.title = f'Discord Testers Store ({page_num + 1}/{total_pages})'
        em.description = 'Use XP to get super cool Dabbit-approved™ rewards from the store!'
        em.set_thumbnail(url='https://cdn.discordapp.com/attachments/330341170720800768/471497246328881153/2Mjvv7E.png')
        em.colour = 15158332
        for i in items:
            link = ''
            if i.link is not None:
                link = f'\n[Example]({i.link})'
            content = f'Cost: {i.cost} XP\nDescription: {i.description}{link}\nBuy this with `!buy {i.id}`'
            # Add some extra details for the storefront commands
            if not only_in_stock:
                content += f'\nPhysical: {str(i.physical)} / In Stock: {str(i.in_stock)}\nExpires after (s): {str(i.expires_after)} / Role ID: {str(i.role_id)}'
            em.add_field(name=i.name, value=content, inline=False)
        return em

    @commands.command()
    @Checks.is_bug_hunter()
    @Checks.dm_only()
    async def store(self, ctx: commands.Context):
        pages = math.ceil(ExpUtils.get_store_count() / 2)
        await Pages.create_new('store', ctx, total_pages=pages, only_in_stock=True)

    @commands.group()
    @Checks.is_employee()
    async def storefront(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send('Unknown storefront command')

    @storefront.command()
    @Checks.is_employee()
    async def list(self, ctx: commands.Context):
        # Essentially the same as !store but shows everything
        pages = math.ceil(ExpUtils.get_store_count(False) / 2)
        await Pages.create_new('store', ctx, total_pages=pages, only_in_stock=False)

    @storefront.command()
    @Checks.is_employee()
    async def edit(self, ctx: commands.Context, item_id: int, field: str, *, value: str):
        # FIXME: There's probably a better way to do this
        if value == 'none':
            value = None
        else:
            if field in ['cost', 'expires_after', 'role_id']:
                value = int(value)
            elif field in ['physical', 'in_stock']:
                value = value.lower() in ['yes', 'true']
        data = {field: value}
        if ExpUtils.edit_store_item(item_id, **data):
            await ctx.send(f':ok_hand: Updated the {field} field on item {item_id}')
            await BugBotLogging.bot_log(f':department_store: {ctx.author} updated the {field} field on store item {item_id} to {value}')
        else:
            await ctx.send(f'Unable to edit the {field} field on item {item_id}')

    @storefront.command(aliases=['create'])
    @Checks.is_employee()
    async def add(self, ctx: commands.Context, *, item_data: str = ''):
        # FIXME: There's probably a better way to do this too (question/answer loop?)
        elements = item_data.split('|')
        if len(elements) != 7:
            return await ctx.send('Missing item data. This should be in the format:\n`name|desc|cost|link|physical|expires_secs|role_id`\n\nExamples:\n`Bug Squasher|Description here|250|none|no|604800|524676139730468874`\n`Bug Hunter Hoodie|Description here|9000|https://imgur.com/3DR75k6|yes|none|none`')
        item = {
            'name': elements[0],
            'description': elements[1],
            'cost': int(elements[2]),
            'link': elements[3] if elements[3] != 'none' else None,
            'physical': elements[4].lower().startswith('y'),
            'expires_after': int(elements[5]) if elements[5] != 'none' else None,
            'role_id': int(elements[6]) if elements[6] != 'none' else None
        }
        added = ExpUtils.add_store_item(**item)
        if added:
            await ctx.send(f'Added {added.name} with ID {added.id}')
            await BugBotLogging.bot_log(f':department_store: {ctx.author} added a new store item, {added.name} (ID: {added.id})')
        else:
            await ctx.send('Failed to add item')

    @storefront.command(aliases=['delete'])
    @Checks.is_employee()
    async def remove(self, ctx: commands.Context, item_id: int):
        if ExpUtils.delete_store_item(item_id):
            await ctx.send(f'Item {item_id} deleted')
            await BugBotLogging.bot_log(f':department_store: {ctx.author} deleted item with ID {item_id} from the store')
        else:
            await ctx.send(f'Unable to delete item {item_id}. If it has purchases linked, try !storefront edit <id> in_stock no')

    @commands.command(aliases=['getpurchase'])
    @commands.guild_only()
    @Checks.is_modinator()
    async def get_purchase(self, ctx: commands.Context, purchase_id: int):
        purchase = ExpUtils.get_purchase(purchase_id)
        if purchase is not None:
            member = ctx.guild.get_member(purchase.hunter.id)
            em = discord.Embed()
            em.title = f'Purchase Details (ID: {purchase_id})'
            em.colour = 7506394     
            em.add_field(name='User', value=f'{member} ({member.id})', inline=False)
            em.add_field(name='Item', value=f'{purchase.item.name}', inline=False)
            em.add_field(name='Bought', value=f'{purchase.timestamp.strftime("%Y-%m-%d %H:%M:%S")}', inline=False)
            if purchase.item.expires_after is not None:
                expiry = (purchase.timestamp + timedelta(seconds=purchase.item.expires_after)).strftime('%Y-%m-%d %H:%M:%S')
                if purchase.expired:
                    expiry += ' (expired)'
            else:
                expiry = 'N/A'
            em.add_field(name='Expiry', value=expiry, inline=False)
            if purchase.item.role_id is not None:
                em.add_field(name='Auto-fulfilled', value='Yes' if purchase.fulfilled else 'No', inline=False)
            await ctx.send(embed=em)
        else:
            await ctx.send(f'Unable to find a purchase with ID {purchase_id}')

    @commands.command()
    @Checks.is_modinator()
    async def transactions(self, ctx: commands.Context, user: discord.User, limit: int = 5):
        # TODO: Make this look better
        td = ''
        transactions = ExpUtils.get_transactions(user.id, last=limit)
        for t in transactions:
            td += f'Date/Time: {t.timestamp.strftime("%Y-%m-%d %H:%M:%S")}\nAmount: {t.xp_change}\nInitiated by: {t.initiator}\nEvent: {TransactionEvent(t.event).name}\n\n'
        await ctx.send(f'Last {limit} transactions for {user}:\n```{td}```')

    async def give_repro_xp(self, user_id, event):
        # Called by the queue cog (only on new repros) and will handle giving XP if eligible
        bucket_groups = {
            'QUEUE_REPRO': [TransactionEvent.approve, TransactionEvent.deny],
            'CANREPRO': [TransactionEvent.can_repro, TransactionEvent.cannot_repro]
        }
        events = None
        for group, el in bucket_groups.items():
            if event in el:
                events = el
                break
        if events is None:
            return False
        tc = ExpUtils.get_transactions(user_id, events, last='day').count()
        limits = Configuration.get_var('bugbot', 'DAILY_XP_LIMITS')
        if tc < limits.get(group):
            amount = Configuration.get_var('bugbot', 'XP').get(group)
            ExpUtils.add_xp(user_id, amount, self.bot.user.id, event)

    @commands.command()
    @Checks.is_bug_hunter()
    @Checks.dm_only()
    async def buy(self, ctx: commands.Context, item_id: int):
        try:
            balance, purchase = ExpUtils.checkout(ctx.author.id, item_id, self.bot.user.id)
        except InvalidItemError:
            return await ctx.send(Configuration.get_var('strings', 'STORE_ITEM_NOT_FOUND'))
        except OutOfStockError:
            return await ctx.send(Configuration.get_var('strings', 'STORE_ITEM_UNAVAILABLE'))
        except InsufficientBalanceError as e:
            return await ctx.send(Configuration.get_var('strings', 'STORE_NEED_MORE_XP').format(xp=e))
        prize_log = Configuration.get_channel('PRIZE_LOG')
        await prize_log.send(f':shopping_cart: {ctx.author} ({ctx.author.id}) bought {purchase.item.name} (Purchase ID: {purchase.id})')
        expiry = ''
        if purchase.item.expires_after is not None:
            expiry = f'\nExpires: {(purchase.timestamp + timedelta(seconds=purchase.item.expires_after)).strftime("%Y-%m-%d %H:%M:%S")}'
        receipt = f'```Item: {purchase.item.name}\nDate/Time: {purchase.timestamp.strftime("%Y-%m-%d %H:%M:%S")}\nPurchase ID: {purchase.id}{expiry}```'
        if purchase.item.physical:
            await ctx.send(Configuration.get_var('strings', 'STORE_PHYSICAL').format(receipt=receipt))
        else:
            if purchase.item.role_id is not None:
                dt = self.bot.get_guild(Configuration.get_master_var('GUILD_ID'))
                member = dt.get_member(ctx.author.id)
                try:
                    await member.add_roles(discord.Object(id=purchase.item.role_id), reason=f'Store purchase (ID: {purchase.id})')
                except (discord.Forbidden, discord.HTTPException):
                    await BugBotLogging.bot_log(f':warning: Unable to add {purchase.item.name} role purchase to {ctx.author}')
                    await ctx.send(Configuration.get_var('strings', 'STORE_ROLE_ERROR'))
                    raise
                else:
                    await ctx.send(Configuration.get_var('strings', 'STORE_ROLE').format(receipt=receipt))
                    await BugBotLogging.bot_log(f':shopping_cart: Applied {purchase.item.name} role to {ctx.author}')
                    if not ExpUtils.fulfil_purchase(purchase.id):
                        await BugBotLogging.bot_log(f':warning: Failed to mark purchase ID {purchase.id} as fulfilled')
            else:
                await ctx.send(Configuration.get_var('strings', 'STORE_DIGITAL').format(receipt=receipt))

    @commands.command(aliases=['cooldown', 'cooldowns'])
    @Checks.is_bug_hunter()
    async def xpcap(self, ctx: commands.Context):
        # TODO
        # Also could roll this into the !xp command
        pass

    @commands.command(aliases=['givexp', 'addxp'])
    @Checks.is_employee()
    async def give_xp(self, ctx: commands.Context, user: discord.User, amount: int):
        if amount < 1:
            await ctx.send('XP amount cannot be less than 1')
        else:
            balance = ExpUtils.add_xp(user.id, amount, ctx.author.id, TransactionEvent.reward)
            await BugBotLogging.bot_log(f':moneybag: {ctx.author} gave {amount} XP to {user}. Their new balance is {balance} XP')
            await ctx.send(f'Gave {amount} XP to {user}. New balance is {balance} XP', delete_after=5.0)
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.command(aliases=['takexp', 'removexp'])
    @Checks.is_employee()
    async def take_xp(self, ctx: commands.Context, user: discord.User, amount: int):
        if amount < 1:
            await ctx.send('XP amount cannot be less than 1')
        else:
            balance = ExpUtils.remove_xp(user.id, amount, ctx.author.id, TransactionEvent.xp_taken)
            await BugBotLogging.bot_log(f':moneybag: {ctx.author} removed {amount} XP from {user}. Their new balance is {balance} XP')
            await ctx.send(f'Removed {amount} XP from {user}. New balance is {balance} XP', delete_after=5.0)
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.command()
    @Checks.is_modinator()
    async def reward(self, ctx: commands.Context, user: discord.User):
        amount = Configuration.get_var('bugbot', 'XP').get('REWARD')
        balance = ExpUtils.add_xp(user.id, amount, ctx.author.id, TransactionEvent.reward)
        if balance is not None:
            await BugBotLogging.bot_log(f':moneybag: {ctx.author} rewarded {user} with {amount} XP. Their new balance is {balance} XP')
            await ctx.send(f':ok_hand: {user} received some XP for helping out!', delete_after=5.0)
        else:
            await ctx.send(f'{user} is not recognised as a Bug Hunter', delete_after=5.0)
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.command()
    @Checks.is_bug_hunter()
    @Checks.dm_only()
    async def xp(self, ctx: commands.Context):
        balance = ExpUtils.get_xp(ctx.author.id)
        await ctx.send(f'You have {balance} XP!')

    @commands.command()
    @Checks.is_modinator()
    async def getxp(self, ctx: commands.Context, user: discord.User):
        balance = ExpUtils.get_xp(user.id)
        await ctx.send(f'{user} has {balance} XP', delete_after=10.0)
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def init_store(self, ctx, total_pages, only_in_stock):
        em = self.build_store_embed(0, total_pages, only_in_stock)
        return None, em, total_pages > 1, []

    async def update_store(self, ctx, message, page_num, action, data):
        if action == 'PREV':
            page_num -= 1
        elif action == 'NEXT':
            page_num += 1
        if page_num < 0:
            page_num = data['total_pages'] - 1
        if page_num > data['total_pages']:
            page_num = 0
        em = self.build_store_embed(page_num, data['total_pages'], data['only_in_stock'])
        return None, em, page_num


def setup(bot):
    bot.add_cog(Experience(bot))
