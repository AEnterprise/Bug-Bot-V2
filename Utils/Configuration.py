import json

from Utils import BugBotLogging

MASTER_CONFIG = dict()
MASTER_LOADED = False


def load_master():
    global MASTER_CONFIG, MASTER_LOADED
    try:
        with open('config/master.json', 'r') as jsonfile:
            MASTER_CONFIG = json.load(jsonfile)
            MASTER_LOADED = True
    except FileNotFoundError:
        BugBotLogging.error("Unable to load config, running with defaults.")
    except Exception as e:
        BugBotLogging.error("Failed to parse configuration.")
        print(e)
        raise e


def get_master_var(key, default=None):
    global MASTER_CONFIG, MASTER_LOADED
    if not MASTER_LOADED:
        load_master()
    if not key in MASTER_CONFIG.keys():
        MASTER_CONFIG[key] = default
        save_master()
    return MASTER_CONFIG[key]


def save_master():
    global MASTER_CONFIG
    with open('config/master.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(MASTER_CONFIG, indent=4, skipkeys=True, sort_keys=True)))


def get_role(ctx, name):
    return ctx.guild.get_role(get_master_var("ROLES")[name.upper()])

def get_channel(ctx, name):
    return ctx.bot.get_channel(get_master_var("CHANNELS")[name.upper()])
