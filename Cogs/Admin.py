import contextlib
import io
import textwrap
import traceback

from discord.ext import commands

from Utils import Pages, Utils, Emoji


class Admin:

    def __init__(self, bot):
        self.bot = bot
        Pages.register("eval", self.init_eval, self.update_eval, sender_only=True)

    def __unload(self):
        Pages.unregister("eval")

    async def __local_check(self, ctx):
        return await ctx.bot.is_owner(ctx.author)

    @commands.command(hidden=True)
    async def restart(self, ctx):
        """Restarts the bot"""
        await ctx.send("Restarting...")
        await Utils.lockdown_shutdown(self.bot)
        await Utils.cleanExit(self.bot, ctx.author.name)

    @commands.command(hidden=True)
    async def eval(self, ctx: commands.Context, *, code: str):
        output = None
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message
        }

        env.update(globals())

        if code.startswith('```'):
            code = "\n".join(code.split("\n")[1:-1])

        out = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(code, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            output = f'{e.__class__.__name__}: {e}'
        else:
            func = env['func']
            try:
                with contextlib.redirect_stdout(out):
                    ret = await func()
            except Exception as e:
                value = out.getvalue()
                output = f'{value}{traceback.format_exc()}'
            else:
                value = out.getvalue()
                if ret is None:
                    if value:
                        output = value
                else:
                    output = f'{value}{ret}'
        if output is not None:
            await Pages.create_new("eval", ctx, pages=Pages.paginate(output))
        else:
            await ctx.message.add_reaction(Emoji.get_emoji("YES"))

    async def init_eval(self, ctx, pages):
        page = pages[0]
        num = len(pages)
        return f"**Eval output 1/{num}**\n```py\n{page}```", None, num > 1, []

    async def update_eval(self, ctx, message, page_num, action, data):
        pages = data["pages"]
        page, page_num = Pages.basic_pages(pages, page_num, action)
        return f"**Eval output {page_num + 1}/{len(pages)}**\n```py\n{page}```", None, page_num


def setup(bot):
    bot.add_cog(Admin(bot))
