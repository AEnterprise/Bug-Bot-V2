from enum import Enum


class Platforms(Enum):
    android = 0
    ios = 1
    desktop = 2
    linux = 3
    store = 4
    marketing = 5


class BugState(Enum):
    queued = 0
    approved = 1
    denied = 2


class BugInfoType(Enum):
    can_reproduce = 0
    can_not_reproduce = 1
    note = 2


class TransactionEvent(Enum):
    queue_action = 0
    repro = 1
    vote = 2
    fun = 3
