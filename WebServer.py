import asyncio
import uuid

from aiohttp import web

from Utils import ReportUtils, RedisMessager
from Utils.Enums import ReportError
from Utils.RedisMessager import Redisception
from Utils.ReportUtils import BugReportException

routes = web.RouteTableDef()
replies = dict()


def is_trello_ip(ip):
    return ip in ['107.23.104.115', '107.23.149.70', '54.152.166.250', '54.164.77.56', '54.209.149.230']


@routes.head('/BugBot/trello')
@routes.post('/BugBot/trello')
async def trello(request):
    remote_ip = request.remote
    if remote_ip == '127.0.0.1':
        remote_ip = request.headers['X-Forwarded-For']  # For local testing with ngrok
    if not is_trello_ip(remote_ip):
        return web.Response(status=403)
    # TODO: Could also verify the signature
    if request.method == 'POST':
        data = await request.json()
        await request.app.redis.send('trello', data['action'])
    return web.Response()


@routes.post('/BugBot/reports')
async def hello(request):
    # retrieve data:
    input = await request.post()
    # convert to a regular dict so we we can serialize to json
    data = dict()
    for k, v in input.items():
        data[k] = v
    # attach UUID to track the reply
    uid = str(uuid.uuid4())
    data["UUID"] = uid
    try:
        # make sure it's valid
        ReportUtils.validate_report(data)
    except BugReportException as ex:
        # not valid, notify sender
        reply = dict(submitted=False)
        if ex.code is ReportError.unknown_platform:
            reply["message"] = f'{ex.msg} is not a valid platform!'
        elif ex.code is ReportError.links_detected:
            reply["message"] = 'Your report contains links, this is not allowed, please submit without links and ask a bug hunter to attach the images'
        elif ex.code is ReportError.missing_fields:
            reply["message"] = f'{ex.msg} is a required field'
        elif ex.code is ReportError.missing_steps:
            reply["message"] = f'You need to supply steps'
        elif ex.code is ReportError.blacklisted_words:
            reply["message"] = f'You cannot use {ex.msg}'
        elif ex.code is ReportError.length_exceeded:
            reply["message"] = f'{ex.msg} is too long'

        return web.json_response(reply, status=400)

    else:
        # send it to the bot for final processing
        data["type"] = "bug_submission"
        try:
            reply = await request.app.redis.get_reply('web_to_bot', data)
        except Redisception:
            # no reply, the bot isn't there or something is very wrong
            reply = dict(submitted=False, message="Report submission failed, please try again later")
            return web.json_response(reply, status=500)
        else:
            return web.json_response(reply, status=200 if reply["submitted"] else 400)


async def initialize(app):
    # TODO: error proper logging
    app.redis = RedisMessager.Messager("bot-web-messages", "web-bot-messages", app.loop)
    await app.redis.initialize()


async def shutdown(app):
    await app.redis.terminate()




app = web.Application()
app.add_routes(routes)
app.on_startup.append(initialize)
app.on_cleanup.append(shutdown)
web.run_app(app)
