from ruamel.yaml import YAML, YAMLError

yaml = YAML()

from Utils import BugBotLogging

MASTER_CONFIG = dict()
MASTER_LOADED = False
CONFIGS = dict()
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


def load_config(filename):
    try:
        with open(f'config/{filename}', 'r') as yamlfile:
            return yaml.load(yamlfile)
    except FileNotFoundError:
        BugBotLogging.error(f'Unable to load config/{filename}')
    except YAMLError:
        BugBotLogging.error(f'Unable to parse config/{filename}')
        raise


def get_var(group, key):
    global CONFIGS
    group = group.lower()
    if group not in CONFIGS:
        CONFIGS[group] = load_config(f'{group}.yaml')
    return CONFIGS[group].get(key, None)


def get_role(name):
    return BOT.get_guild(get_master_var('GUILD_ID')).get_role(get_master_var("ROLES").get(name.upper(), None))


def list_of_role_ids():
    list_of_ids = []
    for key in get_master_var("ROLES").items():
        list_of_ids.append(key[1])
    return list_of_ids


def list_of_bugchannels_ids():
    list_of_ids = []
    for key in get_master_var("BUGCHANNELS").items():
        list_of_ids.append(key[1])
    return list_of_ids


def list_of_channels_ids():
    list_of_ids = []
    for key in get_master_var("CHANNELS").items():
        list_of_ids.append(key[1])
    return list_of_ids


def get_channel(name):
    return BOT.get_guild(get_master_var('GUILD_ID')).get_channel(get_master_var("CHANNELS").get(name.upper(), None))


def get_bugchannel(name):
    return BOT.get_guild(get_master_var('GUILD_ID')).get_channel(get_master_var("BUGCHANNELS").get(name.upper(), None))


def get_tester(id):
    return BOT.get_guild(get_master_var('GUILD_ID')).get_member(id)
