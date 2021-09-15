import discord
import os
import pymongo

from dotenv import load_dotenv
from discord.ext import commands
from discord_components import *
from discord.ext.commands import bot_has_permissions, MissingPermissions
from pymongo import MongoClient

load_dotenv();

cluster = MongoClient(os.getenv('DB_TOKEN'))
db = cluster["UserData"]
collection = db["UserDataColl"]

intents = discord.Intents(messages=True, members=True, guilds=True)
bot = commands.Bot(command_prefix='bot ', help_command=None, intents=intents)

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

#Kicks specified user from server with option comments
@bot.command()
@bot_has_permissions(administrator=True)
async def dropkick(ctx, member: discord.Member, *, reason=None):
	if(await isAdmin(ctx)):
		await ctx.guild.kick(member)
		await ctx.send(f'User {member} has been kicked for reason: {reason}')
		return
	await ctx.send("Lol, nah fam. Nice try though...")

#Kicks specified user from voice channel with option comments
@bot.command()
@bot_has_permissions(administrator=True)
async def kick(ctx, member: discord.Member, *, reason=None):
	if(await isAdmin(ctx)):
		voice = await ctx.author.voice.channel.connect()
		await voice.voice_disconnect()
		return
	await ctx.send("Lol, nah fam. Nice try though...")

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

@bot.command()
async def datainj(ctx):
	members = await ctx.guild.fetch_members().flatten()
	for member in members:
		querieduser = {"_id": member.id}
		if(collection.count_documents(querieduser) == 0 and not member.bot):
			userdata = {"_id": member.id, "allocPoints": 10, "stat_strength": 10, "stat_dexterity": 10, "stat_constitution": 10, "stat_intelligence": 10, "stat_wisdom": 10, "stat_charisma": 10}
			collection.insert_one(userdata)
		#collection.delete_one(querieduser)

@bot.command()
async def reset(ctx, *, args=None):
	if(args=="all"):
		collection.update_many({}, { "$set": { "allocPoints": 10, "stat_strength": 10, "stat_intelligence": 10, "stat_dexterity": 10, "stat_constitution": 10, "stat_intelligence": 10, "stat_wisdom": 10, "stat_charisma": 10 }})
		return
	user_query = collection.find_one({ "_id": ctx.author.id })
	collection.update_one(user_query, { "$set": { "allocPoints": 10, "stat_strength": 10, "stat_intelligence": 10, "stat_dexterity": 10, "stat_constitution": 10, "stat_intelligence": 10, "stat_wisdom": 10, "stat_charisma": 10 }})

#Sets up character creation stat menu
@bot.command()
async def stats(ctx):
	user_query = collection.find_one({ "_id": ctx.author.id })
	await query_update(user_query)

	global screen
	screen = 1

	char_panel = await buttons(ctx, stat_str_points, stat_int_points, stat_dex_points, stat_con_points, stat_wis_points, allocPoints)
	await ctx.send(content="**Character Profile**\nPoints Remaining: " + str(allocPoints), components=char_panel, custom_id=ctx.author.id)

@bot.command()
async def stats2(ctx):
	user_query = collection.find_one({ "_id": ctx.author.id })
	allocPoints = user_query["allocPoints"]
	stat_cha_points = user_query["stat_charisma"]

	global screen
	screen = 2

	char_panel = await buttons2(ctx, stat_cha_points, allocPoints)
	await ctx.send(content="**Character Profile**\nPoints Remaining: " + str(allocPoints), components=char_panel)

@bot.command()
async def abilities(ctx):
	embed = discord.Embed(title = "Test", color = discord.Color.random())
	await ctx.send(content="**Abilities**", components=[Select(placeholder="Choose abilities!", options=[SelectOption(label="Stab", value="Stab"), SelectOption(label="Cry", value="Cry")])])
	interaction = await bot.wait_for("select_option", check=check)
	await interaction.respond(type=3)

@bot.event
async def button_is_disabled(minmax, stat, ap):
	min_stat_val = 6
	max_stat_val = 20
	return False if((minmax == 0 and stat > min_stat_val) or
					(minmax == 1 and stat < max_stat_val and ap > 0)) else True

@bot.event
async def buttons(ctx, strength, intelligence, dexterity, constitution, wisdom, ap):

	str_ar = ActionRow(
		Button(style=ButtonStyle.red, label="-", custom_id="stat_str_sub", disabled=await button_is_disabled(0, strength, ap)),
		#Button(style=ButtonStyle.grey, label=f'{"":⠀<5}' + "Strength: " + str(strength) + f'{"":⠀<5}', custom_id="b_str"),
		Button(style=ButtonStyle.grey, label=await add_spacing("Strength: " + str(strength), strength), custom_id="b_str"),
		Button(style=ButtonStyle.blue, label="+", custom_id="stat_str_add", disabled=await button_is_disabled(1, strength, ap)))
	int_ar = ActionRow(
		Button(style=ButtonStyle.red, label="-", custom_id="stat_int_sub", disabled=await button_is_disabled(0, intelligence, ap)),
		Button(style=ButtonStyle.grey, label=await add_spacing("Intelligence: " + str(intelligence), intelligence), custom_id="b_int"),
		Button(style=ButtonStyle.blue, label="+", custom_id="stat_int_add", disabled=await button_is_disabled(1, intelligence, ap)))
	dex_ar = ActionRow(
		Button(style=ButtonStyle.red, label="-", custom_id="stat_dex_sub", disabled=await button_is_disabled(0, dexterity, ap)),
		Button(style=ButtonStyle.grey, label=await add_spacing("Dexterity: " + str(dexterity), dexterity), custom_id="b_dex"),
		Button(style=ButtonStyle.blue, label="+", custom_id="stat_dex_add", disabled=await button_is_disabled(1, dexterity, ap)))
	con_ar = ActionRow(
		Button(style=ButtonStyle.red, label="-", custom_id="stat_con_sub", disabled=await button_is_disabled(0, constitution, ap)),
		Button(style=ButtonStyle.grey, label=await add_spacing("Constitution: " + str(constitution), constitution), custom_id="b_con"),
		Button(style=ButtonStyle.blue, label="+", custom_id="stat_con_add", disabled=await button_is_disabled(1, constitution, ap)))
	wis_ar = ActionRow(
		Button(style=ButtonStyle.red, label="-", custom_id="stat_wis_sub", disabled=await button_is_disabled(0, wisdom, ap)),
		Button(style=ButtonStyle.grey, label=await add_spacing("Wisdom: " + str(wisdom), wisdom), custom_id="b_wis"), 
		Button(style=ButtonStyle.blue, label="+", custom_id="stat_wis_add", disabled=await button_is_disabled(1, wisdom, ap)))

	components = [str_ar, int_ar, dex_ar, con_ar, wis_ar]
	return components

@bot.event
async def buttons2(ctx, charisma, ap):
	cha_ar = ActionRow(
		Button(style=ButtonStyle.red, label="-", custom_id="stat_cha_sub", disabled=await button_is_disabled(0, charisma, ap)),
		Button(style=ButtonStyle.grey, label=await add_spacing("Charisma: " + str(charisma), charisma), custom_id="b_wis"), 
		Button(style=ButtonStyle.blue, label="+", custom_id="stat_cha_add", disabled=await button_is_disabled(1, charisma, ap)))

	components = [cha_ar]
	return components

@bot.event
async def add_spacing(string, stat_val):
	if "Str" in string:
		spaces = "\u2800\u2800\u2800\u2800\u2800"
	if "Int" in string:
		spaces = "\u2800\u2800\u2800\u2800"
	if "Dex" in string:
		spaces = "\u2800 \u2800 \u2800\u2800"
	if "Con" in string:
		spaces = "\u2800 \u2800 \u2800"
	if "Wis" in string:
		spaces = "\u2800\u2800\u2800\u2800\u2800"
	if "Cha" in string:
		spaces = "\u2800\u2800\u2800\u2800"

	if stat_val < 10:
		spaces += " "

	return(spaces + string + spaces)

#Handles stat add and subtract buttons from stats
@bot.event
async def on_button_click(interaction):
	if interaction.user.id != interaction.message.custom_id:
		return

	user_query = collection.find_one({ "_id": interaction.author.id })
	await query_update(user_query)

	allocMod = -1
	statMod = 1

	mod_stats = {
		"stat_str": ["stat_strength", stat_str_points],
		"stat_int": ["stat_intelligence", stat_int_points],
		"stat_dex": ["stat_dexterity", stat_dex_points],
		"stat_con": ["stat_constitution", stat_con_points],
		"stat_wis": ["stat_wisdom", stat_wis_points],
		"stat_cha": ["stat_charisma", stat_cha_points]
	}

	button_id = interaction.component.custom_id[0:8]

	if interaction.component.label.startswith("-"):
		statMod = -1
		allocMod = 1

	collection.update_many(user_query, { "$set": { mod_stats[button_id][0]: (mod_stats[button_id][1] + statMod), "allocPoints": allocPoints + allocMod}})
	user_query = collection.find_one({ "_id": interaction.author.id })
	await query_update(user_query)

	if(screen == 1):
		char_panel = await buttons(interaction, stat_str_points, stat_int_points, stat_dex_points, stat_con_points, stat_wis_points, allocPoints)
	elif(screen == 2):
		char_panel2 = await buttons2(interaction, stat_cha_points, allocPoints)
	await interaction.message.edit(content="**Character Profile**\nPoints Remaining: " + str(allocPoints), components=char_panel, disabled=True)
	await interaction.respond(type=6)

@bot.event
async def on_select_option(interaction):

	await interaction.respond(type=6)

@bot.event
async def query_update(user_query):
	global allocPoints, stat_str_points, stat_int_points, stat_dex_points, stat_con_points, stat_wis_points, stat_cha_points
	allocPoints = user_query["allocPoints"]
	stat_str_points = user_query["stat_strength"]
	stat_int_points = user_query["stat_intelligence"]
	stat_dex_points = user_query["stat_dexterity"]
	stat_con_points = user_query["stat_constitution"]
	stat_wis_points = user_query["stat_wisdom"]
	stat_cha_points = user_query["stat_charisma"]

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

bot.run(os.getenv('BOT_TOKEN'))