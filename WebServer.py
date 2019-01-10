from aiohttp import web

from Utils import ReportUtils, RedisListener

routes = web.RouteTableDef()


@routes.post('/BugBot/reports')
async def hello(request):
    # retrieve data:
    data = await request.post()

    problems = ReportUtils.validate(data)
    d = dict()
    for k, v in data.items():
        d[k] = v
    submitted = len(problems) is 0
    if submitted:
        await RedisListener.send(d)
    reply = dict(submitted=submitted,
                 messsage="Report submitted" if submitted else "Report rejected",
                 problems=problems
                 )
    # TODO: handle other error codes
    return web.json_response(reply, status=200 if submitted else 400)


async def initialize(app):
    await RedisListener.initialize(app.loop, "bot_to_web", "web_to_bot", receive_reply, print)


async def shutdown(app):
    RedisListener.terminate()


async def receive_reply(reply):
    pass


app = web.Application()
app.add_routes(routes)
app.on_startup.append(initialize)
app.on_cleanup.append(shutdown)
web.run_app(app)
