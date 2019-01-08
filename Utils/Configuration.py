import yaml

from Utils import BugBotLogging

MASTER_CONFIG = dict()
MASTER_LOADED = False
BOT = None


def initialize(bot):
    global BOT
    BOT = bot
    load_master()


def load_master():
    global MASTER_CONFIG, MASTER_LOADED
    try:
        with open('config/master.yaml', 'r') as yamlfile:
            MASTER_CONFIG = yaml.load(yamlfile)
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
    with open('config/master.yaml', 'w') as yamlfile:
        yaml.dump(MASTER_CONFIG, yamlfile, default_flow_style=False)


def get_role(name):
    return BOT.get_guild(get_master_var('GUILD_ID')).get_role(get_master_var("ROLES").get(name.upper(), None))


def get_channel(name):
    return BOT.get_guild(get_master_var('GUILD_ID')).get_channel(get_master_var("CHANNELS").get(name.upper(), None))
