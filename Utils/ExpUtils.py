import operator
from functools import reduce
from datetime import datetime, timedelta

import discord
from peewee import fn, IntegrityError

from Utils import Configuration, BugBotLogging
from Utils.Enums import TransactionEvent, BugState
from Utils.DataUtils import Bug, BugHunter, Transaction, StoreItem, Purchase


class InsufficientBalanceError(Exception):
    def __init__(self, message, required):
        super().__init__(message)
        self.required = required


class InvalidItemError(Exception):
    pass


class OutOfStockError(Exception):
    pass


def create_hunter(user_id):
    # Assume they're a Bug Hunter for info purposes
    return BugHunter.create(id=user_id, hunter_at=datetime.utcnow())


def add_xp(user_id, amount, initiator_id, event):
    try:
        hunter = BugHunter.get_by_id(user_id)
    except BugHunter.DoesNotExist:
        hunter = create_hunter(user_id)
    hunter.xp += amount
    hunter.save()
    Transaction.create(hunter=hunter, xp_change=amount, initiator=initiator_id, event=event)
    return hunter.xp


def remove_xp(user_id, amount, initiator_id, event):
    try:
        hunter = BugHunter.get_by_id(user_id)
    except BugHunter.DoesNotExist:
        hunter = create_hunter(user_id)
    if amount > hunter.xp:
        raise InsufficientBalanceError(f'XP to remove ({amount}) is greater than balance ({hunter.xp})', amount - hunter.xp)
    else:
        hunter.xp -= amount
        hunter.save()
        Transaction.create(hunter=hunter, xp_change=-amount, initiator=initiator_id, event=event)
        return hunter.xp


def get_xp(user_id):
    try:
        return BugHunter.get_by_id(user_id).xp
    except BugHunter.DoesNotExist:
        return 0


def get_xp_pending_bugs():
    clauses = [
        (Bug.state == BugState.approved),
        (Bug.xp_awarded == False)  # noqa
    ]
    return (Bug
            .select()
            .where(reduce(operator.and_, clauses)))


async def award_bug_xp(bot, trello_id, list_id=None, label_ids=[], archived=False):
    bug = Bug.get_or_none(Bug.trello_id == trello_id)
    if bug is None:
        return
    dt = bot.get_guild(Configuration.get_master_var('GUILD_ID'))
    # If the card was archived as new (i.e. approved dupe)
    if archived and list_id in Configuration.get_var('bugbot', 'TRELLO').get('NEW_LISTS'):
        bug.xp_awarded = True
        bug.trello_list = list_id
        bug.save()
        await BugBotLogging.bot_log(f':eye_in_speech_bubble: Bug `{trello_id}` was archived during verification')
    # If the card is in one of the dead bug/won't fix/CNR lists
    elif list_id in Configuration.get_var('bugbot', 'TRELLO').get('DEAD_BUG_LISTS'):
        bug.xp_awarded = True
        bug.trello_list = list_id
        bug.save()
        await BugBotLogging.bot_log(f':eye_in_speech_bubble: Bug `{trello_id}` marked as dead during verification')
    else:
        # Loop through the priority label sets (P0 - P3)
        for severity, data in Configuration.get_var('bugbot', 'TRELLO').get('PRIORITIES').items():
            if any([x for x in label_ids if x in data['LABELS']]):
                amount = Configuration.get_var('bugbot', 'XP').get('VERIFIED_BUG') + data['XP_BONUS']
                priority = int(severity[-1])
                add_xp(bug.reporter, amount, bot.user.id, TransactionEvent.bug_verified)
                bug.xp_awarded = True
                bug.priority = priority
                if list_id is not None:
                    bug.trello_list = list_id
                bug.save()
                member = dt.get_member(bug.reporter)
                await BugBotLogging.bot_log(f':eye_in_speech_bubble: Bug `{trello_id}` verified as {severity}. Gave {amount} XP to {member} (`{bug.reporter}`)')
                break


def expire_roles():
    now = datetime.utcnow()
    clauses = [
        (Purchase.expired == False),  # noqa
        (Purchase.item.expires_after.is_null(False)),
        (fn.ADDTIME(Purchase.timestamp, fn.SEC_TO_TIME(Purchase.item.expires_after)) <= now)
    ]
    expired = (Purchase
               .select()
               .join_from(Purchase, StoreItem)
               .join_from(Purchase, BugHunter)
               .where(reduce(operator.and_, clauses)))
    to_remove = []
    for e in expired:
        e.expired = True
        e.save()
        to_remove.append((e.hunter.id, e.item.role_id))
    return to_remove


def get_transactions(user_id, events=None, last=5):
    clauses = [(Transaction.hunter.id == user_id)]
    if events is not None:
        clauses.append((Transaction.event << events))
    if last == 'day':
        last = None
        dt = datetime.utcnow() - timedelta(days=1)
        clauses.append((Transaction.timestamp >= dt))
    return (Transaction
            .select()
            .join(BugHunter)
            .where(reduce(operator.and_, clauses))
            .limit(last)
            .order_by(Transaction.timestamp.desc()))


def checkout(user_id, item_id, bot_id):
    try:
        item = StoreItem.get_by_id(item_id)
    except StoreItem.DoesNotExist:
        raise InvalidItemError(f'Unable to find a store item with ID {item_id}')
    if not item.in_stock:
        raise OutOfStockError(f'Item {item_id} is out of stock')
    try:
        balance = remove_xp(user_id, item.cost, bot_id, TransactionEvent.purchase)
    except InsufficientBalanceError:
        raise
    else:
        hunter = BugHunter.get_by_id(user_id)
        purchase = Purchase.create(hunter=hunter, item=item)
        return balance, purchase


def get_purchase(purchase_id):
    try:
        return Purchase.get_by_id(purchase_id)
    except Purchase.DoesNotExist:
        return None


def get_store_count(only_in_stock=True):
    query = StoreItem.select()
    if only_in_stock:
        query = query.where((StoreItem.in_stock == True))  # noqa
    return query.count()


def get_store_items(page_num, only_in_stock=True):
    query = StoreItem.select()
    if only_in_stock:
        query = query.where((StoreItem.in_stock == True))  # noqa
    return query.paginate(page_num, 2)


def add_store_item(**kwargs):
    return StoreItem.create(**kwargs)


def edit_store_item(item_id, **kwargs):
    rows = (StoreItem
            .update(**kwargs)
            .where(StoreItem.id == item_id)
            .execute())
    return rows > 0


def delete_store_item(item_id):
    try:
        rows = (StoreItem
                .delete()
                .where(StoreItem.id == item_id)
                .execute())
    except IntegrityError:
        return False
    else:
        return rows > 0


def fulfil_purchase(purchase_id):
    rows = (Purchase
            .update({Purchase.fulfilled: True})
            .where(Purchase.id == purchase_id)
            .execute())
    return rows > 0
