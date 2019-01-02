from discord import utils

from Utils import Configuration

emojis = dict()

BACKUPS = {
    "LEFT": "◀",
    "LOADING": "⏳",
    "MUTE": "😶",
    "NAMETAG": "📛",
    "NO": "🚫",
    "REFRESH": "🔁",
    "RIGHT": "▶",
    "WARNING": "⚠",
    "WHAT": "☹",
    "YES": "✅",
    "TODO": "📋",
    "TACO": "🌮",
    "WRENCH": "🔧",
    "1": "1⃣",
    "2": "2⃣",
    "3": "3⃣",
    "4": "4⃣",
    "5": "5⃣",
    "6": "6⃣",
    "7": "7⃣",
    "8": "8⃣",
    "9": "9⃣",
    "10": "🔟",
    "QUESTION": "❓",
    "CLOCK": "⏰"
}

SELF_ASSIGNABLE_ROLES = {
    "linux": "🐧",
    "android": "🤖",
    "ios": "📱",
    "desktop": "🖥",
    "canary": "🐦",
    "mac": "🍎",
    "employee": "🍎",
    "not employee": "🍎",
    "admin": "🍎"

}


def initialize(bot):
    for name, eid in Configuration.get_master_var("EMOJI", {}).items():
        emojis[name] = utils.get(bot.emojis, id=eid)


def get_chat_emoji(name):
    return str(get_emoji(name))


def get_emoji(name):
    if name in emojis:
        return emojis[name]
    else:
        return BACKUPS[name]
