import discord
import os
import pymongo
import youtube_dl

import asyncio
import functools
import itertools
import math
import random

from async_timeout import timeout
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

#-----------------------------------------------------------YT_DL-----------------------------------------------------------------

# Silence useless bug reports messages
youtube_dl.utils.bug_reports_message = lambda: ''


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        webpage_url = process_info['webpage_url']
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError('Couldn\'t retrieve any matches for `{}`'.format(webpage_url))

        return cls(ctx, discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS), data=info)

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append('{} days'.format(days))
        if hours > 0:
            duration.append('{} hours'.format(hours))
        if minutes > 0:
            duration.append('{} minutes'.format(minutes))
        if seconds > 0:
            duration.append('{} seconds'.format(seconds))

        return ', '.join(duration)


class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embed = (discord.Embed(title='Now playing',
                               description='```css\n{0.source.title}\n```'.format(self),
                               color=discord.Color.blurple())
                 .add_field(name='Duration', value=self.source.duration)
                 .add_field(name='Requested by', value=self.requester.mention)
                 .add_field(name='Uploader', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                 .add_field(name='URL', value='[Click]({0.source.url})'.format(self))
                 .set_thumbnail(url=self.source.thumbnail))

        return embed


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.loop:
                # Try to get the next song within 3 minutes.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(180):  # 3 minutes
                        self.current = await self.songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return

            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            await self.current.source.channel.send(embed=self.current.create_embed())

            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send('An error occurred: {}'.format(str(error)))

    @commands.command(name='join', invoke_without_subcommand=True)
    async def _join(self, ctx: commands.Context):
        """Joins a voice channel."""

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='summon')
    @commands.has_permissions(manage_guild=True)
    async def _summon(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        """Summons the bot to a voice channel.
        If no channel was specified, it joins your channel.
        """

        if not channel and not ctx.author.voice:
            raise VoiceError('You are neither connected to a voice channel nor specified a channel to join.')

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='leave', aliases=['disconnect'])
    @commands.has_permissions(manage_guild=True)
    async def _leave(self, ctx: commands.Context):
        """Clears the queue and leaves the voice channel."""

        if not ctx.voice_state.voice:
            return await ctx.send('Not connected to any voice channel.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.command(name='volume')
    async def _volume(self, ctx: commands.Context, *, volume: int):
        """Sets the volume of the player."""

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        if 0 > volume > 100:
            return await ctx.send('Volume must be between 0 and 100')

        ctx.voice_state.volume = volume / 100
        await ctx.send('Volume of the player set to {}%'.format(volume))

    @commands.command(name='now', aliases=['current', 'playing'])
    async def _now(self, ctx: commands.Context):
        """Displays the currently playing song."""

        await ctx.send(embed=ctx.voice_state.current.create_embed())

    @commands.command(name='pause')
    @commands.has_permissions(manage_guild=True)
    async def _pause(self, ctx: commands.Context):
        """Pauses the currently playing song."""

        if not ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='resume')
    @commands.has_permissions(manage_guild=True)
    async def _resume(self, ctx: commands.Context):
        """Resumes a currently paused song."""

        if not ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='stop')
    @commands.has_permissions(manage_guild=True)
    async def _stop(self, ctx: commands.Context):
        """Stops playing song and clears the queue."""

        ctx.voice_state.songs.clear()

        if not ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction('⏹')

    @commands.command(name='skip')
    async def _skip(self, ctx: commands.Context):
        """Vote to skip a song. The requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Not playing any music right now...')

        voter = ctx.message.author
        if voter == ctx.voice_state.current.requester:
            await ctx.message.add_reaction('⏭')
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            if total_votes >= 3:
                await ctx.message.add_reaction('⏭')
                ctx.voice_state.skip()
            else:
                await ctx.send('Skip vote added, currently at **{}/3**'.format(total_votes))

        else:
            await ctx.send('You have already voted to skip this song.')

    @commands.command(name='queue')
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        """Shows the player's queue.
        You can optionally specify the page to show. Each page contains 10 elements.
        """

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n'.format(i + 1, song)

        embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.songs), queue))
                 .set_footer(text='Viewing page {}/{}'.format(page, pages)))
        await ctx.send(embed=embed)

    @commands.command(name='shuffle')
    async def _shuffle(self, ctx: commands.Context):
        """Shuffles the queue."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.shuffle()
        await ctx.message.add_reaction('✅')

    @commands.command(name='remove')
    async def _remove(self, ctx: commands.Context, index: int):
        """Removes a song from the queue at a given index."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')

    @commands.command(name='loop')
    async def _loop(self, ctx: commands.Context):
        """Loops the currently playing song.
        Invoke this command again to unloop the song.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        # Inverse boolean value to loop and unloop.
        ctx.voice_state.loop = not ctx.voice_state.loop
        await ctx.message.add_reaction('✅')

    @commands.command(name='play')
    async def _play(self, ctx: commands.Context, *, search: str):
        """Plays a song.
        If there are songs in the queue, this will be queued until the
        other songs finished playing.
        This command automatically searches from various sites if no URL is provided.
        A list of these sites can be found here: https://rg3.github.io/youtube-dl/supportedsites.html
        """

        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            try:
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
            except YTDLError as e:
                await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
            else:
                song = Song(source)

                await ctx.voice_state.songs.put(song)
                await ctx.send('Enqueued {}'.format(str(source)))

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('You are not connected to any voice channel.')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('Bot is already in a voice channel.')

bot.add_cog(Music(bot))

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
	await ctx.send(content="**Character Profile**\nPoints Remaining: " + str(allocPoints), components=char_panel)

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
	await interaction.message.edit(content="**Character Profile**\nPoints Remaining: " + str(allocPoints), components=char_panel)
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