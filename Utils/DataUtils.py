from datetime import datetime

from peewee import MySQLDatabase, Model, PrimaryKeyField, CharField, IntegerField, BigIntegerField, BooleanField, \
    ForeignKeyField, DateTimeField, Check, SmallIntegerField

from Utils import Configuration
from Utils.Enums import Platforms, BugState, BugInfoType, TransactionEvent

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
    client_info = CharField(collation="utf8mb4_general_ci")
    device_info = CharField(collation="utf8mb4_general_ci")
    platform = EnumField(Platforms)
    blocked = BooleanField(default=False)
    state = EnumField(BugState, default=0)
    reported_at = DateTimeField(default=datetime.utcnow)
    xp_awarded = BooleanField(default=False)
    last_state_change = DateTimeField(null=False)

    class Meta:
        database = connection


class BugInfo(Model):
    id = PrimaryKeyField()
    user = BigIntegerField()
    content = CharField(max_length=500, collation="utf8mb4_general_ci")
    bug = ForeignKeyField(Bug, backref="info")  # link to ticket
    type = EnumField(BugInfoType)
    added = DateTimeField(default=datetime.utcnow)

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


def init():
    connection.connect()
    connection.create_tables([Bug, BugInfo, BugHunter, Tag, Transaction])
    connection.close()
