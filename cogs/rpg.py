import discord
import pymongo
from discord.ext import commands
from discord_components import *
from main import cluster, db, collection
from pymongo import MongoClient

class RPG(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	'''
	Add submit button for ability points panel. Message component only allows 3 ARs, so will likely have to reference a new global in multiple functions.
	Add return button to revert back to previous ability page
	'''

	selected = [False, False, False, False, False, False, False, False, False]
	
	ab_arr = [
		"Shadow Spear", "🗡️", "Shadow Spear", "Hurl a spear of shadow at target",
		"Whip Lash", "⛓️", "Whip Lash", "Lash at target with a spiked whip, causing bleeding",
		"Hectic Cleave", "🌪️", "Hectic Cleave", "Cleaves multiple nearby targets",
		"Heal", "❤️‍🩹", "Heal", "Heals self or selected party member instantly",
		"Rend", "🩸", "Rend", "Causes target to bleed, dealing damage over time",
		"Poison", "☠️", "Poison", "Poisons target, dealing nature damage over time",
		"Teleport", "💥", "Teleport", "Teleport short distances. Don't. Teleport. Into. Walls.",
		"Sprint", "👟", "Sprint", "I'M FAST AS F**K BOI",
		"Flash Powder", "😵‍💫", "Flash Powder", "Stuns enemies in the blink of an eye!",
		"Greater Mana Regen", "🧙‍♂️", "Greater Mana Regen", "Regenerates larger quantities of mana over time",
		"Greater Health Regen", "💖", "Greater Health Regen", "Regenerates larger quantities of health over time",
		"Luck of the Draw", "🍀", "Luck of the draw", "Increased chance of finding rare items",
		"Leader", "❤️‍🔥", "Leader", "Bonus to charisma and inspiration",
		"Fighter", "⚔️", "Fighter", "Gain Berzerk: Damage EVERYONE in your path",
		"Alchemist", "⚗️", "Alchemist", "Brew potions to settle the score",
		"Summon Familiar", "🎎", "Summon Familiar", "Summons a familiar of your choice",
		"Mirror Mage", "👥", "Mirror Mage", "Summons the caster's mirror image, replicating spells",
		"Combustion", "🔥", "Combustion", "Unleashes a devastating firestorm on nearby foes",
		"Pickpocket", "💰", "Pickpocket", "Become adept at loosening others' coinpurses",
		"Demolitions Expert", "🧨", "Demolitions Expert", "Learn the art of explosives. Bomb go BOOM",
		"Astronomer", "🔭", "Astronomer", "Use the stars to guide your path",
		"Lockpicking", "🔑", "Lockpicking", "Gain the ability to pick locks above your level",
		"Tracking", "🔍", "Tracking", "Gain the ability to track prey: Both animal and human",
		"Bartering", "💴", "Bartering", "Grants better deals with shopkeepers",
		"Sign of the Bear", "🐻", "Sign of the Bear", "Bonus to melee attacks and defense",
		"Sign of the Wolf", "🐺", "Sign of the Wolf", "Bonus to combo attacks. Increases party stats",
		"Sign of the Owl", "🦉", "Sign of the Owl", "Bonus to perception. More easily detect enemy weak points"
		]

	abilities_submit = ActionRow(Button(style=ButtonStyle.blue, label="Submit", custom_id="submit_abilities", disabled=True)),

	sendButton = 0
	msg = 0
	ability_page = 0
	my_id = 0

	@commands.command()
	async def datainj(self, ctx):
		members = await ctx.guild.fetch_members().flatten()
		for member in members:
			querieduser = {"_uid": member.id}
			if(collection.count_documents(querieduser) == 0 and not member.bot):
				userdata = {"_uid": member.id, "allocPoints": 10, "stat_strength": 10, "stat_dexterity": 10, "stat_intelligence": 10, "stat_wisdom": 10, "stat_charisma": 10, "gold": 0}
				collection.insert_one(userdata)

	@commands.command()
	async def reset(self, ctx, *, args=None):
		if(args=="all"):
			collection.update_many({}, { "$set": { "allocPoints": 10, "stat_strength": 10, "stat_dexterity": 10, "stat_intelligence": 10, "stat_intelligence": 10, "stat_wisdom": 10, "stat_charisma": 10, "gold": 0 }})
			return
		user_query = collection.find_one({ "_uid": ctx.author.id })
		collection.update_one(user_query, { "$set": { "allocPoints": 10, "stat_strength": 10, "stat_dexterity": 10, "stat_intelligence": 10, "stat_intelligence": 10, "stat_wisdom": 10, "stat_charisma": 10, "gold": 0 }})

	@commands.command(name='delete')
	async def deletechar(self, ctx: commands.Context, *args):
		name = ""
		for word in args:
			name += word

		try:
			user_query = collection.find_one({"_uid": ctx.message.author.id, "char_name": name})
			collection.delete_one(user_query)
		except TypeError:
			await ctx.send("No such character named " + name + " found for your id!")

	@commands.command(name='rpg')
	async def createchar(self, ctx: commands.Context, command=None, *args):
		global name; name = ""
		self.my_id = ctx.message.author.id

		for word in args:
			name += word

		if(command=="name"):
			if(collection.count_documents({"char_name": name}) > 0):
				await ctx.send("Name already taken!")
				return

			collection.insert_one({"_uid": ctx.message.author.id, "char_name": name, "allocPoints": 10, "stat_strength": 10, "stat_dexterity": 10, "stat_intelligence": 10, "stat_wisdom": 10, "stat_charisma": 10, "gold": 0})

			for i in range(9):
				collection.update_one({"char_name": name}, {'$set': {"ability_" + str(i): ""}})

		elif(command=="edit"):
			if(collection.count_documents({"_uid": ctx.message.author.id, "char_name": name}) == 0):
				await ctx.send("No such character named " + name + " found for your id!")
				return
		else:
			await ctx.send("Invalid command form. Try '.rpg name <charname>' for new characters or '.rpg edit <charname>' to edit and existing character.")
			return

		await self.abilities(ctx)

	async def abilities(self, ctx):
		n = self.ability_page
		ab_arr = self.ab_arr

		query = collection.find_one({"_uid": self.my_id, "char_name": name})
		components = []
		count = 0

		for i in range(3):
			options = []

			for key in query:
				if key != ("ability_" + str(3*n+i)):
					continue

				for j in range(3):
					isDefault = False
					current_ability = 4*(3*i+j)+(36*n)

					if(query[key] == ab_arr[current_ability]):
						isDefault = True
						count += 1

					op = SelectOption(label=ab_arr[current_ability], emoji=ab_arr[current_ability+1], value=ab_arr[current_ability+2], description=ab_arr[current_ability+3], default=isDefault)
					options.append(op)
				
				break
			row = ActionRow(Select(placeholder="Choose abilities!", options=options, custom_id="Ability_" + str(3*n+i)))

			components.append(row)

		self.msg = await ctx.send(content="**Abilities**", components=components)
		self.sendButton = await ctx.send(components=self.abilities_submit)

		if(count == 3):
			await self.enable_submit(ctx)

	async def submitAbilities(self, interaction):
		ctx = await self.bot.get_context(interaction.message)

		await interaction.message.delete()
		await self.msg.delete()

		self.ability_page += 1
		if(self.ability_page > 2):
			await self.stats(ctx, interaction)
			return

		await self.abilities(ctx)

	async def stats(self, ctx, interaction):
		user_query = collection.find_one({ "_uid": interaction.user.id})
		await self.query_update(user_query)

		char_panel = await self.buttons(ctx, stat_str_points, stat_dex_points, stat_int_points, stat_wis_points, stat_cha_points)
		await ctx.send(content="**Character Profile**\nPoints Remaining: " + str(allocPoints), components=char_panel)

	async def query_update(self, user_query):
		global allocPoints, stat_str_points, stat_dex_points, stat_int_points, stat_wis_points, stat_cha_points
		allocPoints = user_query["allocPoints"]
		stat_str_points = user_query["stat_strength"]
		stat_dex_points = user_query["stat_dexterity"]
		stat_int_points = user_query["stat_intelligence"]
		stat_wis_points = user_query["stat_wisdom"]
		stat_cha_points = user_query["stat_charisma"]

	async def buttons(self, ctx, strength, dexterity, intelligence, wisdom, charisma):
		makeButton = self.makeButton

		str_ar = makeButton("Strength", strength)
		dex_ar = makeButton("Dexterity", dexterity)
		int_ar = makeButton("Intelligence", intelligence)
		wis_ar = makeButton("Wisdom", wisdom)
		cha_ar = makeButton("Charisma", charisma)

		return [str_ar, dex_ar, int_ar, wis_ar, cha_ar]

	def makeButton(self, statName, statType):
		isactive = self.button_is_disabled
		space = self.add_spacing
		statAbv = statName[0:3].lower()

		return ActionRow(
			Button(style=ButtonStyle.red, label="-", custom_id="stat_" + statAbv + "_sub", disabled=isactive(0, statType, allocPoints)),
			Button(style=ButtonStyle.grey, label=space(statName + ": " + str(statType), statType), custom_id="b_" + statAbv),
			Button(style=ButtonStyle.blue, label="+", custom_id="stat_" + statAbv + "_add", disabled=isactive(1, statType, allocPoints)))

	def button_is_disabled(self, minmax, stat, ap):
		min_stat_val = 6
		max_stat_val = 20
		return False if((minmax == 0 and stat > min_stat_val) or
						(minmax == 1 and stat < max_stat_val and ap > 0)) else True

	def add_spacing(self, string, stat_val):
		if "Str" in string:
			spaces = "\u2800\u2800\u2800\u2800\u2800"
		if "Dex" in string:
			spaces = "\u2800 \u2800 \u2800\u2800"
		if "Int" in string:
			spaces = "\u2800\u2800\u2800\u2800"
		if "Wis" in string:
			spaces = "\u2800\u2800\u2800\u2800\u2800"
		if "Cha" in string:
			spaces = "\u2800\u2800\u2800\u2800"

		if stat_val < 10:
			spaces += " "

		return(spaces + string + spaces)

	@commands.Cog.listener()
	async def on_button_click(self, interaction):
		await interaction.respond(type=7)

		if(interaction.message.components[0][0].custom_id == "submit_abilities"):
			await self.submitAbilities(interaction)

		else:
			user_query = collection.find_one({ "_uid": interaction.author.id })
			await self.query_update(user_query)

			mod_stats = {
				"stat_str": ["stat_strength", stat_str_points],
				"stat_dex": ["stat_dexterity", stat_dex_points],
				"stat_int": ["stat_intelligence", stat_int_points],
				"stat_wis": ["stat_wisdom", stat_wis_points],
				"stat_cha": ["stat_charisma", stat_cha_points]
			}

			button_id = interaction.component.custom_id[0:8]

			allocMod = -1
			statMod = 1

			if interaction.component.label.startswith("-"):
				statMod = -1
				allocMod = 1

			collection.update_many(user_query, { "$set": { mod_stats[button_id][0]: (mod_stats[button_id][1] + statMod), "allocPoints": allocPoints + allocMod}})
			user_query = collection.find_one({ "_uid": interaction.author.id })
			await self.query_update(user_query)

			char_panel = await self.buttons(interaction, stat_str_points, stat_dex_points, stat_int_points, stat_wis_points, stat_cha_points)

			await interaction.message.edit(content="**Character Profile**\nPoints Remaining: " + str(allocPoints), components=char_panel, disabled=True)

	@commands.Cog.listener()
	async def on_select_option(self, interaction):
		await interaction.respond(type=6)

		ctx = await self.bot.get_context(interaction.message)
		n = self.ability_page
		abNum = int(interaction.custom_id[8:9])

		collection.update_one({"char_name": name}, {'$set': {"ability_" + str(abNum): interaction.values[0]}})

		self.selected[abNum] = True

		for i in [0,1,2]:
			if(self.selected[3*n+i] == False):
				return

		await self.enable_submit(ctx)

	async def enable_submit(self, ctx):
		abilities_submit = ActionRow(
			Button(style=ButtonStyle.blue, label="Submit", custom_id="submit_abilities", disabled=False))
		try:
			await self.sendButton.delete()
			await ctx.send(components=[abilities_submit])
		except:
			pass

async def setup(bot):
    await bot.add_cog(RPG(bot))