import discord
import os

from dotenv import load_dotenv
from discord.ext import commands
from discord_components import DiscordComponents, Button, ButtonStyle
from discord.ext.commands import has_permissions, MissingPermissions

load_dotenv();

bot = commands.Bot(command_prefix='bot ', help_command=None)
botid = 881725998834524180
bot_channelid = 881729379527426108

contentDict = {}
contentFile = open("content.txt", "r")

adminCommands = {
	"bot mute <User> - Mutes user in voice chat",
	"bot unmute <User> - Unmutes user in voice chat",
	"bot chatmute <User> - Mutes user in text chat channels",
	"bot chatunmute <User> - Unmutes user in text chat channels",
	"bot kick <User> - Kicks selected user from server"
	}

#-------------------------------------------------------ADMIN COMMANDS------------------------------------------------------------

#Checks if user is listed as server admin or autorized bot dev
@bot.event
async def isAdmin(ctx):
	if ctx.message.author.guild_permissions.administrator or ctx.message.author.id == 133757834922819584:
		return True
	return False

#Mutes specified user from chat channels
@bot.command(pass_context = True)
async def chatmute(ctx, member: discord.Member):
     if await isAdmin():
        role = discord.utils.get(member.guild.roles, name='Silence')
        await member.add_roles(role)
        embed=discord.Embed(title="User Muted!", description="**{0}** was muted by **{1}**!".format(member, ctx.message.author), color=0xff00f6)
        await ctx.channel.send(embed=embed)
     else:
        embed=discord.Embed(title="Permission Denied.", description="You don't have permission to use this command.", color=0xff00f6)
        await ctx.channel.send(embed=embed)

#Unmutes specified user from chat channels
@bot.command(pass_context = True)
async def chatunmute(ctx, member: discord.Member):
     if await isAdmin():
        role = discord.utils.get(member.guild.roles, name='Silence')
        await member.remove_roles(role)
        embed=discord.Embed(title="User Unmuted!", description="**{0}** was unmuted by **{1}**!".format(member, ctx.message.author), color=0xff00f6)
        await ctx.channel.send(embed=embed)
     else:
        embed=discord.Embed(title="Permission Denied.", description="You don't have permission to use this command.", color=0xff00f6)
        await ctx.channel.send(embed=embed)

#Mutes specified user from voice channels
@bot.command(pass_context = True)
async def mute(ctx, member: discord.Member):
     if await isAdmin(ctx):
     	await member.edit(mute=True)

#Unmutes specified user from voice channels
@bot.command(pass_context = True)
async def unmute(ctx, member: discord.Member):
     if await isAdmin(ctx):
     	await member.edit(mute=False)

#Kicks specified user from voice channel with option comments
@bot.command()
@has_permissions(administrator=True)
async def kick(ctx, member: discord.Member, *, reason=None):
	if(isAdmin(member)):
		ctx.send("Lol, nah fam. Nice try though...")
		return
	#await ctx.guild.kick(member)
	await ctx.send(f'User {member} has been kicked for reason: {reason}')

#-------------------------------------------------------BOT CONFIG------------------------------------------------------------

#Run on initial setup. Refreshes bot and send message to bot channel
@bot.event
async def on_ready():
	await refresh()
	DiscordComponents(bot)
	await bot.get_channel(bot_channelid).send("Bot Ready...")

#Pointer command for bot refresh
@bot.command()
async def refresh(ctx):
	await refresh()
	await ctx.channel.send("Refreshed Successfully")

#Refreshes content file to add/remove commands from the list dynamically
@bot.event
async def refresh():
	await reset_phrases()
	contentFile = open("content.txt", "r")
	for line in contentFile:
		(key, val) = line.split(" : ")
		contentDict[key] = val

#Temp command to cointain commands which print multi-line phrases
@bot.event
async def reset_phrases():
	contentDict.clear()
	contentDict["***Phrases***"] = ""
	contentDict["baka"] = "You kinda smell\nLike a BAKA\n**E R E N     Y E A G E R**"
	contentDict["***Images & GIFs***"] =  ""

#-------------------------------------------------------RP COMMANDS-----------------------------------------------------------

#Sets up character creation stat menu
@bot.command()
async def stats(ctx):
	allocPoints = 5
	stat1Points = 0
	stat2Points = 0

	b_sub_stat1 = Button(style=ButtonStyle.blue, label="-", custom_id="stat1_sub")
	b_stat1 = Button(style=ButtonStyle.grey, label="Stat 1: " + str(stat1Points))
	b_add_stat1 = Button(style=ButtonStyle.blue, label="+", custom_id="stat1_add")
	b_sub_stat2 = Button(style=ButtonStyle.blue, label="-", custom_id="stat2_sub")
	b_stat2 = Button(style=ButtonStyle.grey, label="Stat 2: " + str(stat2Points))
	b_add_stat2 = Button(style=ButtonStyle.blue, label="+", custom_id="stat2_add")

	await ctx.send(content="**Character Profile**\nPoints Remaining: " + str(allocPoints), components=[[(b_sub_stat1),(b_stat1),(b_add_stat1)], [(b_sub_stat2),(b_stat2),(b_add_stat2)]])

#Handles stat add and subtract buttons from DStats
@bot.event
async def on_button_click(interaction):
	if interaction.component.label.startswith("+"):
		if interaction.component.custom_id == "stat1_add":
			stat1Points += 1
		else:
			stat2Points += 1
		allocPoints -= 1
	elif interaction.component.label.startswith("-"):
		if interaction.component.custom_id == "stat1_sub":
			stat1Points -= 1
		else:
			stat2Points -= 1
		allocPoints += 1

#------------------------------------------------------MESSAGE & HELP COMMANDS------------------------------------------------------------

#Command handler for content file
@bot.event
async def on_message(message):
	if(message.author.id != botid):
	    for word in contentDict:
		    if word in message.content.lower():
		    	await message.channel.send(contentDict[word])
		    	break
	await bot.process_commands(message)

#Lists available bot commands
@bot.command()
async def help(ctx, *, args=None):
	helpMessage = ''
	if(args=='admin'):
		if(not await isAdmin(ctx)):
			await ctx.channel.send("Permission Denied. Access restricted to adminitrators.")
			return
		await ctx.channel.send("**ADMIN COMMANDS**")
		for command in adminCommands:
			helpMessage += command + "\n"

	else:
		helpMessage = '**BOT COMMANDS**\n'
		for word in contentDict:
			helpMessage += word + "\n"
	await ctx.channel.send(helpMessage)

bot.run(os.getenv('TOKEN'))