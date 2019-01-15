# Validators: return error message on fail, empty string on pass
# probably a better way to do this, but this works pretty good for now
import re

from discord import Embed

from Utils import Configuration, Utils, Emoji
from Utils.DataUtils import Bug
from Utils.Enums import Platforms, ReportError


class BugReportException(Exception):
    def __init__(self, code, msg=''):
        super().__init__(msg)
        self.code = code
        self.msg = msg


def validate_report(report):
    for name in ["title", "steps", "expected", "actual", "client", "system", "platform"]:
        if name not in report or report[name].strip() == "":
            raise BugReportException(ReportError.missing_fields, name)
    # Check the platform is valid (or can be aliased)
    platforms = Configuration.get_var('bugbot', 'BUG_PLATFORMS')
    platform_data = platforms.get(report["platform"].upper(), None)
    if platform_data is None:
        for p, pd in platforms.items():  # TODO: Squash this
            if report["platform"].lower() in pd['ALIASES']:
                report["platform"] = p
                platform_data = pd
                break
    if platform_data is None:
        raise BugReportException(ReportError.unknown_platform, report["platform"])

    if len(report["steps"]) < 2:
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
        client_info=sections['client'],
        device_info=sections['system'],
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
    if 'lock' in data:
        mod = data['lock']['username']
        reason = data['lock']['reason']
        em.description = f':lock: This report has been temporarily locked by {mod} and cannot be interacted with (`{reason}`)'
    em.add_field(name='Submitter', value=f'{data["submitter"]["username"]} (`{data["submitter"]["id"]}`) {data["submitter"]["emoji"]}', inline=False)
    em.add_field(name='Platform', value=f'{data["platform"]["name"]} {data["platform"]["emoji"]}', inline=False)
    em.add_field(name='Short Description', value=data['title'], inline=False)
    em.add_field(name='Steps to Reproduce', value=data['steps'], inline=False)
    em.add_field(name='Expected Result', value=data['expected'], inline=False)
    em.add_field(name='Actual Result', value=data['actual'], inline=False)
    em.add_field(name='Client Info', value=data['client'], inline=True)
    em.add_field(name='Device/System Info', value=data['system'], inline=True)
    em.add_field(name='Report ID', value=f'**{data["id"]}**', inline=False)

    interactions = []
    for x in reversed(data['repros']):
        if x['type'] == 'approve':
            emoji = Emoji.get_chat_emoji('APPROVE')
        elif x['type'] == 'deny':
            emoji = Emoji.get_chat_emoji('DENY')
        elif x['type'] == 'note':
           emoji = ':pencil:'
        interactions.append(f'{emoji} **{x["username"]}** (`{x["id"]}`): `{x["details"]}`')
    for x in data['attachments']:
        interactions.append(f':paperclip: **{x["username"]}** (`{x["id"]}`): {x["link"]}')

    if len(interactions) > 0:
        em.add_field(name='---', value='\n'.join(interactions), inline=False)

    return em

        # EXAMPLE FORMAT:
        # {
        #     "platform": {
        #         "name": "iOS",
        #         "colour": 10460830,
        #         "emoji": ":iphone:"
        #     },
        #     "submitter": {
        #         "username": "Test#1234",
        #         "id": 258274103935369219,
        #         "emoji": "<:meowbughunter:533815499541184532>"
        #     },
        #     "id": 13883,
        #     "title": "",
        #     "steps": "1. This is a step\n2. Another step",
        #     "expected": "",
        #     "actual": "",
        #     "client": "",
        #     "system": "",
        #     "repros": [
        #         {
        #             "username": "Test#1234",
        #             "id": 258274103935369219,
        #             "type": "approve",
        #             "details": "Can repro..."
        #         }
        #     ],
        #     "lock": {
        #         "username": "Test#1234",
        #         "reason": "Checking with devs"
        #     },
        #     "attachments": [
        #         {
        #             "username": "Test#1234",
        #             "id": 258274103935369219,
        #             "link": ""
        #         }
        #     ]
        # }
