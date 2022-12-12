from aiohttp import web
import discord


async def handle(request):
    name = request.match_info.get("name", "Anonymous")
    text = "Hello, " + name
    return web.Response(text=text)


async def on_get_channel_messages(request):
    channel = self.bot.get_channel(int(channel_id))
    if not channel or not isinstance(channel, discord.channel.TextChannel):
        return


web_app = web.Application()

web_app.add_routes([web.get("/", handle), web.get("/{name}", handle)])

if __name__ == "__main__":
    web.run_app(web_app)
