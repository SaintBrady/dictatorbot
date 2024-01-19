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

intents = discord.Intents.all()#(messages=True, members=True, guilds=True)
bot = commands.Bot(command_prefix='!', help_command=None, intents=intents)

config = Config(bot)

@bot.event#
async def on_ready():
    await bot.load_extension("cogs.admin")
    await bot.load_extension("cogs.message")
    #await bot.load_extension("cogs.music") --Need to check if deprecated or changes to function defs available. Throws KeyError currently
    #await bot.load_extension("cogs.rpg") --Probably borked now that Discord Components is gone. Find suitable alternative
    await config.setup()

bot.run(os.getenv('BOT_TOKEN'))