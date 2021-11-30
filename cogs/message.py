import discord
from data.member import Member
from discord.ext import commands

class Message(commands.Cog):

    adminCommands = {
        "bot mute <User> - Mutes user in voice chat",
        "bot unmute <User> - Unmutes user in voice chat",
        "bot chatmute <User> - Mutes user in text chat channels",
        "bot chatunmute <User> - Unmutes user in text chat channels",
        "bot kick <User> - Kicks selected user from server"
    }

    contentDict = {}

    def __init__(self, bot):
        self.bot = bot

    def refresh(self):
        """Refreshes content file to add/remove commands from the list"""

        self.reset_phrases()
        contentFile = open("content.txt", "r")
        for line in contentFile:
            (key, val) = line.split(" : ")
            self.contentDict[key] = val

    def reset_phrases(self):
        """Temp command to cointain commands which print multi-line phrases"""

        self.contentDict.clear()
        self.contentDict["***Phrases***"] = ""
        self.contentDict["baka"] = "You kinda smell\nLike a BAKA\n**E R E N     Y E A G E R**"
        self.contentDict["***Images & GIFs***"] =  ""

    @commands.Cog.listener("on_message")
    async def searchmemes(self, message):
        """Command handler for content file"""

        if not (message.author.id == 882129649927348244 or message.author.id == 881725998834524180):#Member.is_bot: #FIX ME (property def ctx called by bot, so id matches)
            for word in self.contentDict:
                if word in message.content.lower():
                    await message.channel.send(self.contentDict[word])
                    break

    @commands.command(name='help')
    async def help(self, ctx: commands.Context, *, args=None):
        """Lists available bot commands"""

        helpMessage = ''
        if(args=='admin'):
            if not Member.is_admin:
                await ctx.channel.send("Permission Denied. Access restricted to adminitrators.")
                return
            await ctx.channel.send("**ADMIN COMMANDS**")
            for command in self.adminCommands:
                helpMessage += command + "\n"

        else:
            helpMessage = '**BOT COMMANDS**\n'
            for word in self.contentDict:
                helpMessage += word + "\n"
        await ctx.channel.send(helpMessage)

def setup(bot):
    msg = Message(bot)
    msg.refresh()
    bot.add_cog(msg)
