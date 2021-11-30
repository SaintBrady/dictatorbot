import discord
from data.member import Member
from discord.ext import commands
from discord.ext.commands import bot_has_permissions, MissingPermissions

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='mute')
    async def _chatmute(self, ctx: commands.Context, *, target: discord.Member):
        """Mutes member from typing in text chat for all channels"""

        if Member.is_admin:
            role = discord.utils.get(target.guild.roles, name='Silence')
            await target.add_roles(role)
            embed=discord.Embed(title="User Muted!", description="**{0}** was muted by **{1}**!".format(target, ctx.message.author), color=0xff00f6)
            await ctx.channel.send(embed=embed)
        else:
            embed=discord.Embed(title="Permission Denied.", description="You don't have permission to use this command.", color=0xff00f6)
            await ctx.channel.send(embed=embed)

    @commands.command(name='unmute')
    async def _chatunmute(self, ctx: commands.Context, *, target: discord.Member):
        """Unmutes specified user from chat channels"""

        if Member.is_admin:
            role = discord.utils.get(target.guild.roles, name='Silence')
            await target.remove_roles(role)
            embed=discord.Embed(title="User Unmuted!", description="**{0}** was unmuted by **{1}**!".format(target, ctx.message.author), color=0xff00f6)
            await ctx.channel.send(embed=embed)
        else:
            embed=discord.Embed(title="Permission Denied.", description="You don't have permission to use this command.", color=0xff00f6)
            await ctx.channel.send(embed=embed)

    @commands.command(name='gag')
    async def _gag(self, ctx: commands.Context, *, target: discord.Member):
        """Mutes specified user from voice channels"""

        if Member.is_admin:
            await target.edit(mute=True)

    @commands.command(name='ungag')
    async def _ungag(self, ctx: commands.Context, *, target: discord.Member):
        """Unmutes specified user from voice channels"""

        if Member.is_admin:
            await target.edit(mute=False)

    @commands.command(name='serverkick')
    @bot_has_permissions(administrator=True)
    async def _serverkick(self, ctx: commands.Context, target: discord.Member, *, reason=None):
        """Kicks specified user from server with option comments"""

        if Member.is_admin:
            await ctx.guild.kick(target)
            await ctx.send(f'User {target} has been kicked for reason: {reason}')
            return
        await ctx.send("Lol, nah fam. Nice try though...")

    @commands.command(name='kick')
    @bot_has_permissions(administrator=True)
    async def _kick(self, ctx: commands.Context, target: discord.Member, *, reason=None):
        """Kicks specified user from voice channel with option comments"""

        if Member.is_admin and target.voice:
            await target.move_to(None)
            return
        await ctx.send("Lol, nah fam. Nice try though...")

def setup(bot):
	bot.add_cog(Admin(bot))