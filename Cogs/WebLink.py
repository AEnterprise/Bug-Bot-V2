import json
from datetime import datetime

import aioredis
from aioredis.pubsub import Receiver

import BugBot
from Utils import Configuration, BugBotLogging, ReportUtils, Checks, ExpUtils
from Utils.DataUtils import Bug
from Utils.Enums import ReportSource, Platforms


class WebLink:

    def __init__(self, bot) -> None:
        self.bot = bot
        bot.loop.create_task(self.init())
        self.redis_link = None
        self.receiver = Receiver(loop=bot.loop)
        # add handlers here
        self.handlers = dict(
            bug_submission=self.submit,
            user_reports=self.user_reports,
            get_bug=self.get_bug,
            patch_bug=self.patch_bug
        )
        self.no_reply_handlers = dict(
            process_trello_event=self.process_trello_event
        )
        self.task = self._receiver()

    def __unload(self):
        self.bot.loop.create_task(self._unload())

    async def _unload(self):
        # cog terminted, clean up
        for c in self.receiver.channels.values():
            self.redis_link.unsubscribe(c)
        self.receiver.stop()
        self.redis_link.close()
        await self.redis_link.wait_closed()

    async def init(self):
        try:
            redis_info = Configuration.get_master_var("REDIS", dict(host="localhost", port=6379))
            self.redis_link = await aioredis.create_redis_pool(
                (redis_info["host"], redis_info["port"]),
                encoding="utf-8", db=0, maxsize=2)  # size 2: one send, one receive
            await self.redis_link.subscribe(self.receiver.channel("web-bot-messages"))
            self.bot.loop.create_task(self._receiver())
            BugBotLogging.info("Web uplink established, disabling submit command")
            # self.bot.remove_command("submit")
        except OSError:
            await BugBotLogging.bot_log("Failed to connect to the web api, backup submit command enabled!")

    async def _receiver(self):
        async for sender, message in self.receiver.iter(encoding='utf-8', decoder=json.loads):
            try:
                handler = self.handlers[message["type"]] if message["type"] in self.handlers else self.no_reply_handlers[message["type"]]
                reply = dict(reply=await handler(message), uid=message["uid"])
                await self.redis_link.publish_json("bot-web-messages", reply)
            except Exception as e:
                await BugBot.handle_exception("Dash message handling", e, None, None, None, None, message)

    async def submit(self, data):
        # validation has already been done by the webserver so we don't need to bother doing that again here

        # no reporting during lockdown
        if self.bot.lockdown:
            reply = dict(submitted=False, lockdown=True, message=self.bot.lockdown_message)
            await self.bot.redis.send('bot_to_web', reply)
        else:
            user = self.bot.get_user(int(data['user_id']))
            try:
                # try to send report
                id = await ReportUtils.add_report(user, data, ReportSource.form)
                reply = dict(submitted=True, lockdown=False,
                             message=f"Your report ID is {id}")
                return reply
            except Exception as ex:
                # something went wrong, notify the other side
                reply = dict(submitted=False, lockdown=False,
                             message="Something went very wrong. Mods have been notified, please try again later")
                await BugBot.handle_exception("submit processing", ex)
                return reply

    async def user_reports(self, data):
        # determine if the user is a moderator or not (moderators can see and edit all reports)
        # TODO: what if the user is not there? give error, give results, handled by discord?
        user_id = int(data["user"])
        query = Bug.select()
        if self.is_mod(user_id):
            query = query.where(Bug.reporter == user_id)
        bugs = list()
        for bug in query.order_by(Bug.id.desc()).paginate(data["page"], 25):
            bugs.append(dict(
                id=bug.id,
                title=bug.title,
                state=bug.state.value,
                platform=bug.platform.value
            ))
        return dict(status=200, data=bugs)

    def is_mod(self, user_id):
        user = Configuration.get_tester(user_id)
        return user is not None and Checks.is_mod(user)

    async def get_bug(self, data):
        rid = int(data["bug"])
        bug = Bug.get_or_none(id=rid)
        if bug is not None:
            report_dict = dict(
                id=bug.id,
                title=bug.title,
                state=bug.state.value,
                platform=bug.platform.value,
                reporter=bug.reporter,
                reported_at=bug.reported_at.isoformat(),
                steps=bug.steps,
                expected=bug.expected,
                actual=bug.actual,
                client_info=bug.client_info,
                device_info=bug.device_info

            )
            return dict(status=200, data=report_dict)
        return dict(status=404, data=dict(updated=False, message="No report found"))

    async def patch_bug(self, data):
        # webserver did the validation already
        bug = Bug.get_or_none(id=data["bug"])
        if bug is None:
            return dict(status=404, data=dict(updated=False, message="Invalid bug ID"))
        user_id = int(data["user_id"])
        if user_id != bug.reporter and not self.is_mod(user_id):
            return dict(status=403, data=dict(updated=False, message="You are not allowed to edit this bug"))
        new_info = data["data"]
        for k, v in new_info.items():
            if k == "platform":
                platforms = Configuration.get_var('bugbot', 'BUG_PLATFORMS')
                platform_data = platforms.get(v.upper(), None)
                if platform_data is None:
                    for p, pd in platforms.items():
                        if v.lower() in pd['ALIASES']:
                            v = p
                            break
            setattr(bug, k, v)
        bug.save()
        await ReportUtils.update_bug(bug, self.bot)
        return dict(status=200, data=dict(updated=True))

    async def process_trello_event(self, data):
        card_events = ['addAttachmentToCard', 'addLabelToCard', 'addMemberToCard', 'commentCard', 'deleteAttachmentFromCard', 'removeLabelFromCard', 'removeMemberFromCard', 'updateCard']
        if data['type'] in card_events:
            bug = Bug.get_or_none(Bug.trello_id == data['data']['card']['shortLink'])
            if bug is not None:
                bug.last_activity = datetime.utcnow()
                if 'listAfter' in data['data']:
                    bug.trello_list = data['data']['listAfter']['id']
                elif 'list' in data['data']:
                    bug.trello_list = data['data']['list']['id']
                bug.save()
                if data['type'] == 'commentCard':
                    pass
                    # If a dev/engineer commented on the card (backlog feature)
                    # if data['idMemberCreator'] in Configuration.get_var('bugbot', 'dev_trello_ids'):
                    #    pass
                if not bug.xp_awarded:
                    if data['type'] == 'updateCard':
                        await ExpUtils.award_bug_xp(self.bot, bug.trello_id, bug.trello_list, archived=data['data']['card'].get('closed', False))
                    elif data['type'] == 'addLabelToCard':
                        await ExpUtils.award_bug_xp(self.bot, bug.trello_id, label_ids=[data['data']['label']['id']], archived=data['data']['card'].get('closed', False))


def setup(bot):
    bot.add_cog(WebLink(bot))
