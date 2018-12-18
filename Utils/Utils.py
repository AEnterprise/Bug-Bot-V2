import json

from Utils import BugBotLogging


def fetch_from_disk(filename, alternative=None):
    try:
        with open(f"{filename}.json") as file:
            return json.load(file)
    except FileNotFoundError:
        if alternative is not None:
            fetch_from_disk(alternative)
        return dict()


def save_to_disk(filename, dict):
    with open(f"{filename}.json", "w") as file:
        json.dump(dict, file, indent=4, skipkeys=True, sort_keys=True)


def escape_markdown(text):
    text = str(text)
    for c in ("\\", "`", "*", "_", "~", "<"):
        text = text.replace(c, f"\{c}\u200b")
    return text.replace("@", "@\u200b")


async def cleanExit(bot, trigger):
    await BugBotLogging.bot_log(f"Shutdown triggered by {trigger}.")
    await bot.logout()
    await bot.close()

def trim_message(message, limit):
    if len(message) < limit - 3:
        return message
    return f"{message[:limit-3]}..."