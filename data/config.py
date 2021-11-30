import discord
from cogs.message import Message
from discord_components import *

class Config:
	def __init__(self, bot):
		self.bot = bot
		self.msg = Message(self.bot)

	async def setup(self):
		self.msg.refresh()
		DiscordComponents(self.bot)
	
	async def search(self, message):
		await self.msg.searchmemes(message)