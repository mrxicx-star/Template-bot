import discord
from discord.ext import commands
import asyncio
import youtube_dl

# ---------------- BOT SETUP ----------------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ---------------- YTDL + MUSIC ----------------
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'extract_flat': 'in_playlist',
    'default_search': 'ytsearch',
}
ffmpeg_options = {'options': '-vn'}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# ---------------- MUSIC COMMANDS ----------------
@bot.command()
async def play(ctx, *, query):
    if ctx.author.voice is None:
        return await ctx.send("❌ You must be in a voice channel to play music!")

    voice_channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)

    async with ctx.typing():
        player = await YTDLSource.from_url(query, loop=bot.loop, stream=True)
        ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

    await ctx.send(f"🎶 Now playing: **{player.title}**")

@bot.command()
async def skip(ctx):
    if ctx.voice_client is None:
        return await ctx.send("❌ No song is playing!")
    ctx.voice_client.stop()
    await ctx.send("⏭ Skipped the current song!")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Disconnected from voice channel!")
    else:
        await ctx.send("❌ I'm not in a voice channel!")

@bot.command()
async def pause(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸ Music paused!")
    else:
        await ctx.send("❌ No music is playing!")

@bot.command()
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶ Music resumed!")
    else:
        await ctx.send("❌ Music is not paused!")

# ---------------- HELP COMMAND ----------------
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📜 Moderation & Utility Commands",
        description=(
            "!kick, !ban, !mute, !unmute, !timeout, !warn, !warnings, !clear, !softban, "
            "!lock, !unlock, !slowmode, !modlogs, !notes, !addnote, !case, !roleinfo, !serverinfo, !userinfo, !tempban\n\n"
            "🎵 Music Commands:\n"
            "!play <song>, !skip, !pause, !resume, !leave\n\n"
            "🎲 Fun Commands:\n"
            "!8ball, !coinflip, !diceroll, !cat, !dog, !meme, !rps, !slots, !urbandictionary, !insult, !rank, !leaderboard\n\n"
            "⚙️ Utility Commands:\n"
            "!ping, !help, !weather, !translate, !calc, !remindme, !search, !vote, !invite\n\n"
            "🛠️ Other Commands:\n"
            "!setup all, !delall, !greetset, !id, !clean, !uptime, !latency, !setprefix, !diagnose, !perms, !setnick\n\n"
            "💌 Social / Profile / Fun:\n"
            "!application, !status, !afk, !profile, !reminder, !urban, !dictionary, !joke, !fact, !quote, !roll, !flip, !choose, !hug, !kiss, !pat, !slap, !highfive, !dance, !cry, !laugh, !smile, !angry, !think"
        ),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed)

# ---------------- OTHER COMMANDS ----------------
# Example for moderation (expand all 80+ commands as needed)
@bot.command()
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"✅ Kicked {member} for {reason if reason else 'no reason'}.")

@bot.command()
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"✅ Banned {member} for {reason if reason else 'no reason'}.")

# ---------------- BOT RUN ----------------
# Using GitHub secret token (no token in code)
import os
bot.run(os.getenv("DISCORD_TOKEN"))