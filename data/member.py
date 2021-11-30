import discord
from discord.ext import commands

class Member:
    command_id_list = {
        133757834922819584
    }

    bot_id_list = {
        881725998834524180,
        882129649927348244
    }

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice = None

    @property
    def is_admin(self, ctx: commands.Context):
        if ctx.message.author.guild_permissions.administrator or ctx.message.author.id == 133757834922819584:#in command_id_list:
            return True
        return False

    @property
    def is_bot(self, ctx: commands.Context):
        if ctx.message.author.id == 881725998834524180 or ctx.message.author.id == 882129649927348244:#in self.bot_id_list:
            return True
        return False

    @property
    def is_connected(self, ctx:commands.Context, member):
        voice_client = get(ctx.member.voice_clients, guild=ctx.guild)
        return voice_client and voice_client.is_connected()