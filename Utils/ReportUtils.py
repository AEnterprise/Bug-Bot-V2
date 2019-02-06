# Validators: return error message on fail, empty string on pass
# probably a better way to do this, but this works pretty good for now
import re

from discord import Embed, Forbidden, NotFound

from Utils import Configuration, Utils, Emoji
from Utils.DataUtils import Bug
from Utils.Enums import Platforms, ReportError, BugInfoType, BugBlockType, BugState


class BugReportException(Exception):
    def __init__(self, code, msg=''):
        super().__init__(msg)
        self.code = code
        self.msg = msg


def validate_report(report, require_all=True):
    fields = ["title", "steps", "expected", "actual", "client_info", "device_info", "platform"]
    if require_all:
        for name in fields:
            if name not in report or report[name].strip() == "":
                raise BugReportException(ReportError.missing_fields, name)
    for name in report:
        if name not in fields and name != "user_id":
            raise BugReportException(ReportError.bad_field, name)
    # Check the platform is valid (or can be aliased)
    platforms = Configuration.get_var('bugbot', 'BUG_PLATFORMS')
    if "platform" in report:
        platform_data = platforms.get(report["platform"].upper(), None)
        if platform_data is None:
            for p, pd in platforms.items():  # TODO: Squash this
                if report["platform"].lower() in pd['ALIASES']:
                    report["platform"] = p
                    platform_data = pd
                    break
        if platform_data is None:
            raise BugReportException(ReportError.unknown_platform, report["platform"])

    if "steps" in report and len(report["steps"]) < 2:
        raise BugReportException(ReportError.missing_steps)

    # Check for links/invites in the report (exclude trello.com)
    for name, r in report.items():
        if re.search(r'(discordapp\.com/invite|discord\.gg|(ftp|https?)://(?!trello\.com)\S+)', r, re.IGNORECASE):
            raise BugReportException(ReportError.links_detected, name)
        if len(r) > 1024:
            raise BugReportException(ReportError.length_exceeded, name)
    blacklist = [x for x in Configuration.get_var('bugbot', 'BUG_TEXT_BLACKLIST') if x in report['title'].lower() or x in report[ 'actual'].lower()]  # FIXME: This matches within words so will catch 'buggy'...etc
    if len(blacklist) > 0:
        raise BugReportException(ReportError.blacklisted_words, ', '.join(blacklist))


async def add_report(user, sections, source):

    # Add report to database and get report ID
    bug = Bug.create(
        reporter=user.id,
        title=sections['title'],
        steps=sections['steps'],
        expected=sections['expected'],
        actual=sections['actual'],
        client_info=sections['client_info'],
        device_info=sections['device_info'],
        platform=Platforms[sections["platform"].lower()],
        source=source
    )

    # Build embed
    report = {'id': bug.id, 'repros': [], 'attachments': []}
    report.update(sections)
    report['submitter'] = {'username': str(user), 'id': user.id, 'emoji': ''}
    if hasattr(user, 'roles'):
        if Configuration.get_role('BUG_HUNTER') in user.roles:
            report['submitter']['emoji'] = Emoji.get_chat_emoji('MEOWBUGHUNTER')
    platforms = Configuration.get_var('bugbot', 'BUG_PLATFORMS')
    platform_data = platforms.get(sections["platform"].upper(), None)
    if not platform_data['EMOJI'].startswith(':'):
        platform_data['EMOJI'] = Emoji.get_chat_emoji(platform_data['EMOJI'])
    report['platform'] = {'name': platform_data['DISPLAY'], 'colour': platform_data['COLOUR'], 'emoji': platform_data['EMOJI']}
    em = build_report_embed(report)

    # Post embed in queue and get message ID
    queue = Configuration.get_bugchannel('QUEUE')
    msg = await queue.send(embed=em)

    # Update database entry with message ID
    bug.msg_id = msg.id
    bug.save()

    # Return the report ID
    return bug.id


def build_report_embed(data):
    em = Embed(colour=data['platform']['colour'])
    if 'block_text' in data:
        em.description = f':lock: {data["block_text"]}'
    em.add_field(name='Submitter', value=f'{data["submitter"]["username"]} (`{data["submitter"]["id"]}`) {data["submitter"]["emoji"]}', inline=False)
    em.add_field(name='Platform', value=f'{data["platform"]["name"]} {data["platform"]["emoji"]}', inline=False)
    em.add_field(name='Short Description', value=data['title'], inline=False)
    em.add_field(name='Steps to Reproduce', value=data['steps'], inline=False)
    em.add_field(name='Expected Result', value=data['expected'], inline=False)
    em.add_field(name='Actual Result', value=data['actual'], inline=False)
    em.add_field(name='Client Info', value=data['client_info'], inline=True)
    em.add_field(name='Device/System Info', value=data['device_info'], inline=True)
    em.add_field(name='Report ID', value=f'**{data["id"]}**', inline=False)

    if 'trello_id' in data:
        em.add_field(name='Trello', value=f'https://trello.com/c/{data["trello_id"]}', inline=False)

    interactions = []
    for x in reversed(data['repros']):
        if x['type'] == 'can_reproduce':
            emoji = Emoji.get_chat_emoji('APPROVE')
        elif x['type'] == 'can_not_reproduce':
            emoji = Emoji.get_chat_emoji('DENY')
        elif x['type'] == 'note':
            emoji = ':pencil:'
        interactions.append(f'{emoji} **{x["username"]}** (`{x["id"]}`): || `{x["details"]}` ||')
    for x in data['attachments']:
        interactions.append(f':paperclip: **{x["username"]}** (`{x["id"]}`): {x["link"]}')

    if len(interactions) > 0:
        em.add_field(name='---', value='\n'.join(interactions), inline=False)

    return em


def bug_to_embed(bug, bot):
    # Get the platform data
    platform = Configuration.get_var('bugbot', 'BUG_PLATFORMS').get(bug.platform.name.upper(), None)
    # Prepare the dict to build the embed
    data = {
        'platform': {
            'name': platform['DISPLAY'],
            'colour': platform['COLOUR'],
            'emoji': platform['EMOJI']
        },
        'submitter': {
            'username': str(bot.get_user(bug.reporter)),
            'id': bug.reporter,
            'emoji': ''
        },
        'id': bug.id,
        'title': bug.title,
        'steps': bug.steps,
        'expected': bug.expected,
        'actual': bug.actual,
        'client_info': bug.client_info,
        'device_info': bug.device_info,
        'repros': [],
        'attachments': []
    }
    # Get the platform emoji if it's custom
    if not data['platform']['emoji'].startswith(':'):
        data['platform']['emoji'] = Emoji.get_chat_emoji(data['platform']['emoji'])
    # Add user emoji if they're a hunter
    reporter = Configuration.get_tester(bug.reporter)
    if reporter is not None:
        if Configuration.get_role('BUG_HUNTER') in reporter.roles:
            data['submitter']['emoji'] = Emoji.get_chat_emoji('MEOWBUGHUNTER')
    # Prepare repro/notes/attachments
    stances = {'can_reproduce': 0, 'can_not_reproduce': 0}
    for i in bug.info:
        item = {'username': str(bot.get_user(i.user)), 'id': i.user}
        if i.type == BugInfoType.attachment:
            item['link'] = i.content
            data['attachments'].append(item)
        else:
            item['type'] = i.type.name
            item['details'] = i.content
            data['repros'].append(item)
            try:
                stances[i.type.name] += 1
            except KeyError:
                pass
    # If the bug has been locked
    if bug.block_type == BugBlockType.user:
        data['block_text'] = 'This report has been temporarily locked for the reporter to make edits'
    elif bug.block_type == BugBlockType.mod:
        data['block_text'] = f'This report has been temporarily locked by {bot.get_user(bug.block_user)}: `{bug.block_reason}`'
    elif bug.block_type == BugBlockType.flow:
        state = 'approved/denied'
        if stances['can_reproduce'] >= 3:
            state = 'approved'
        elif stances['can_not_reproduce'] >= 3:
            state = 'denied'
        data['block_text'] = f'This report will be fully {state} in 20 seconds unless a !revoke is used'
    if bug.trello_id is not None:
        data['trello_id'] = bug.trello_id
    return build_report_embed(data)


async def update_bug(bug, bot):
    # if not approved we need the queue
    channel = None
    if bug.state == BugState.queued:
        channel = 'QUEUE'
    elif bug.state == BugState.approved:
        channel = bug.platform.name.upper()
    channel = Configuration.get_bugchannel(channel)
    try:
        message = await channel.get_message(bug.msg_id)
        await message.edit(embed=bug_to_embed(bug, bot))
    except (Forbidden, NotFound):
        pass