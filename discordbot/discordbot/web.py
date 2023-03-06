import discord
from aiohttp import web


class Web(discord.AutoShardedClient):
    def init_web(self):
        self.web_app = web.Application()

        self.web_app.add_routes(
            [web.get("/", self.handle), web.get("/{name}", self.handle)]
        )
        self.web_app.add_routes(
            ["/channel_messages/{channel_id}", self.http_get_channel_messages]
        )

        web.run_app(self.web_app)

    async def handle(self, request):
        name = request.match_info.get("name", "Anonymous")
        text = "Hello, " + name
        return web.Response(text=text)

    async def http_get_channel_messages(self, request):
        channel_id = request.match_info.get("channel_id")
        channel = self.get_channel(int(channel_id))
        if not channel or not isinstance(channel, discord.channel.TextChannel):
            return
        me = channel.guild.get_member(self.user.id)

        messages = []
        if channel.permissions_for(me).read_messages:
            async for message in channel.history(limit=50):
                messages.append(
                    json.dumps(format_message(message), separators=(",", ":"))
                )
