from datetime import datetime

from peewee import MySQLDatabase, Model, PrimaryKeyField, CharField, IntegerField, BigIntegerField, BooleanField, \
    ForeignKeyField, DateTimeField, Check, SmallIntegerField

from Utils import Configuration
from Utils.Enums import Platforms, BugState, BugInfoType, TransactionEvent, ReportSource

db_info = Configuration.get_master_var("DATABASE")
connection = MySQLDatabase(db_info["NAME"], user=db_info["USER"], password=db_info["PASSWORD"], host=db_info["HOST"],
                           port=db_info["PORT"], use_unicode=True, charset="utf8mb4")


class EnumField(IntegerField):
    """This class enables an Enum field for Peewee"""

    def __init__(self, choices, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choices = choices

    def db_value(self, value):
        return value.value

    def python_value(self, value):
        return self.choices(value)


class Bug(Model):
    id = PrimaryKeyField()
    reporter = BigIntegerField()
    title = CharField(collation="utf8mb4_general_ci")
    steps = CharField(max_length=2000, collation="utf8mb4_general_ci")
    expected = CharField(collation="utf8mb4_general_ci")
    actual = CharField(collation="utf8mb4_general_ci")
    client_info = CharField(collation="utf8mb4_general_ci")
    device_info = CharField(collation="utf8mb4_general_ci")
    platform = EnumField(Platforms)
    blocked = BooleanField(default=False)
    state = EnumField(BugState, default=BugState.queued)
    reported_at = DateTimeField(default=datetime.utcnow)
    xp_awarded = BooleanField(default=False)
    last_state_change = DateTimeField(default=datetime.utcnow)
    trello_id = CharField(max_length=30, null=True)
    trello_list = CharField(max_length=30, null=True)
    priority = SmallIntegerField(null=True)
    msg_id = BigIntegerField(null=True)
    source = EnumField(ReportSource)

    class Meta:
        database = connection


class BugInfo(Model):
    id = PrimaryKeyField()
    user = BigIntegerField()
    content = CharField(max_length=500, collation="utf8mb4_general_ci")
    bug = ForeignKeyField(Bug, backref="info")  # link to ticket
    type = EnumField(BugInfoType)
    added = DateTimeField(default=datetime.utcnow)
    trello_id = CharField(max_length=30)

    class Meta:
        database = connection


class BugHunter(Model):
    id = BigIntegerField(primary_key=True)  # re-use userid as hunter key
    xp = SmallIntegerField(default=0)
    initiate_at = DateTimeField(default=datetime.utcnow)
    hunter_at = DateTimeField(null=True)  # optional, for people still at initiate phase

    class Meta:
        database = connection
        constraints = [Check('xp >= 0')]


class Tag(Model):
    id = PrimaryKeyField()
    trigger = CharField(max_length=50, collation="utf8mb4_general_ci")
    response = CharField(max_length=2000, collation="utf8mb4_general_ci")
    faq = BooleanField()

    class Meta:
        database = connection


class Transaction(Model):
    id = PrimaryKeyField()
    timestamp = DateTimeField(default=datetime.utcnow)
    hunter = ForeignKeyField(BugHunter, backref="transactions")
    xp_change = SmallIntegerField()
    initiator = BigIntegerField()
    event = EnumField(TransactionEvent)

    class Meta:
        database = connection


class Storeinfo(Model):
    id = PrimaryKeyField()
    userid = BigIntegerField() # The user ID
    platform = EnumField(Platforms)
    information = CharField(max_length=100, default="Not set", collation="utf8mb4_general_ci")

    class Meta:
        database = connection


class StoreItem(Model):
    id = PrimaryKeyField()
    name = CharField(collation="utf8mb4_general_ci")
    cost = SmallIntegerField()
    description = CharField(max_length=500, collation="utf8mb4_general_ci")
    link = CharField(collation="utf8mb4_general_ci", null=True)
    physical = BooleanField()
    expires_after = IntegerField(null=True)
    role_id = BigIntegerField(null=True)
    in_stock = BooleanField(default=True)

    class Meta:
        database = connection


class Purchase(Model):
    id = PrimaryKeyField()
    timestamp = DateTimeField(default=datetime.utcnow)
    hunter = ForeignKeyField(BugHunter, backref="purchases")
    item = ForeignKeyField(StoreItem, backref="purchases")
    expired = BooleanField(default=False)
    fulfilled = BooleanField(default=False)  # not currently used

    class Meta:
        database = connection


def init():
    connection.connect()
    connection.create_tables([Bug, BugInfo, BugHunter, Tag, Transaction, Storeinfo, StoreItem, Purchase])
    connection.close()

