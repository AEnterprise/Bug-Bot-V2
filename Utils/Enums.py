from enum import Enum


class Platforms(Enum):
    android = 0
    ios = 1
    desktop = 2
    linux = 3
    store = 4
    marketing = 5
    mac = 6 # for storeinfo


class BugState(Enum):
    queued = 0
    approved = 1
    denied = 2


class BugInfoType(Enum):
    can_reproduce = 0
    can_not_reproduce = 1
    note = 2
    attachment = 3


class TransactionEvent(Enum):
    can_repro = 0
    cannot_repro = 1
    approve = 2
    deny = 3
    attach = 4
    revoke = 5
    bug_verified = 6
    hug = 7
    fight = 8
    bunny = 9
    vote = 10
    reward = 11
    xp_taken = 12
    purchase = 13
