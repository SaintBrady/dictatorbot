import discord
import os
import pymongo
from data.config import Config

from pymongo import MongoClient
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv();

cluster = MongoClient(os.getenv('DB_TOKEN'))
db = cluster["UserData"]
collection = db["UserDataColl"]

intents = discord.Intents(messages=True, members=True, guilds=True)
bot = commands.Bot(command_prefix='!', help_command=None, intents=intents)

bot.load_extension("cogs.admin")
bot.load_extension("cogs.message")
bot.load_extension("cogs.music")
bot.load_extension("cogs.rpg")

config = Config(bot)

@bot.event
async def on_ready():
    await config.setup()

bot.run(os.getenv('BOT_TOKEN'))