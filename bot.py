import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from datetime import datetime, timedelta

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Moderation log channel id placeholder (set with !setlog)
mod_log_channel_id = None
autorole_id = None
mod_role_id = None

# Store warnings per user
user_warnings = {}

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")
    print("Loaded commands: 80+")
    
# -------------------- HELP COMMAND --------------------
@bot.command()
async def help(ctx):
    commands_list = [
        "!nick", "!me", "!spoiler", "!giphy", "!tenor", "!shrug", "!tableflip", "!unflip",
        "!msg", "!thread", "!kick", "!ban", "!timeout", "!warn", "!warnings", "!clear",
        "!mute", "!unmute", "!softban", "!lock", "!unlock", "!slowmode", "!modlogs",
        "!notes", "!addnote", "!case", "!roleinfo", "!serverinfo", "!userinfo", "!tempban",
        "!play", "!skip", "!pause", "!resume", "!queue", "!clear-queue", "!stop", "!loop",
        "!shuffle", "!volume", "!nowplaying", "!seek", "!join", "!leave", "!lyrics",
        "!8ball", "!coinflip", "!diceroll", "!cat", "!dog", "!meme", "!rps", "!slots",
        "!urbandictionary", "!insult", "!rank", "!leaderboard", "!giveaway start", "!poll",
        "!avatar", "!imagine", "!blend", "!describe", "!ping", "!help", "!weather",
        "!translate", "!calc", "!remindme", "!search", "!vote", "!invite", "!id", "!clean",
        "!uptime", "!latency", "!setprefix", "!diagnose", "!perms", "!setnick", "!application",
        "!status", "!afk", "!profile", "!reminder", "!urban", "!dictionary", "!joke", "!fact",
        "!quote", "!roll", "!flip", "!choose", "!hug", "!kiss", "!pat", "!slap", "!highfive",
        "!dance", "!cry", "!laugh", "!smile", "!angry", "!think", "!setup all", "!delall",
        "!greetchannelset"
    ]
    embed = discord.Embed(title="📜 Help - All Commands", color=discord.Color.blue())
    embed.description = "\n".join(commands_list)
    await ctx.send(embed=embed)

# -------------------- MODERATION --------------------
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"✅ {member} has been kicked. Reason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"✅ {member} has been banned. Reason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def tempban(ctx, member: discord.Member, time: int, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"✅ {member} has been tempbanned for {time} minutes. Reason: {reason}")
    await discord.utils.sleep_until(datetime.utcnow() + timedelta(minutes=time))
    await ctx.guild.unban(member)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount)
    await ctx.send(f"🗑️ Deleted {amount} messages.", delete_after=5)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason=None):
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, speak=False, send_messages=False)
    await member.add_roles(mute_role)
    await ctx.send(f"🔇 {member} has been muted. Reason: {reason}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    await member.remove_roles(mute_role)
    await ctx.send(f"🔊 {member} has been unmuted.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def softban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await member.unban(reason="Softban clear")
    await ctx.send(f"✅ {member} has been softbanned. Reason: {reason}")

# -------------------- SETUP AND DELETE --------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    """Create categories, channels, roles from your template"""
    guild = ctx.guild
    
    # Example: create category + channels
    overwatch = await guild.create_category("🏍️ SERVER SPAWN")
    await guild.create_text_channel("・entrance", category=overwatch)
    await guild.create_text_channel("・overview", category=overwatch)
    
    # Voice category
    voice_cat = await guild.create_category("🔊 VOICE ZONE")
    await guild.create_voice_channel("General Vc", category=voice_cat)
    await guild.create_voice_channel("Chill Vc", category=voice_cat)
    
    await ctx.send("✅ Server setup completed!")

@bot.command()
@commands.has_permissions(administrator=True)
async def delall(ctx):
    """Delete all roles, channels, categories"""
    for channel in ctx.guild.channels:
        await channel.delete()
    for role in ctx.guild.roles:
        if role != ctx.guild.default_role:
            await role.delete()
    await ctx.send("✅ Deleted all roles and channels!")

# -------------------- GREET CHANNEL --------------------
greet_channel_id = None

@bot.command()
@commands.has_permissions(administrator=True)
async def greetchannelset(ctx, channel: discord.TextChannel):
    global greet_channel_id
    greet_channel_id = channel.id
    await ctx.send(f"✅ Welcome messages will be sent to {channel.mention}")

@bot.event
async def on_member_join(member):
    if greet_channel_id:
        channel = bot.get_channel(greet_channel_id)
        await channel.send(f"👋 Welcome {member.mention} to {member.guild.name}!")

# -------------------- PLACEHOLDER COMMANDS --------------------
placeholder_commands = [
    "nick","me","spoiler","giphy","tenor","shrug","tableflip","unflip","msg","thread",
    "play","skip","pause","resume","queue","clear-queue","stop","loop","shuffle",
    "volume","nowplaying","seek","join","leave","lyrics","8ball","coinflip","diceroll",
    "cat","dog","meme","rps","slots","urbandictionary","insult","rank","leaderboard",
    "giveaway","poll","avatar","imagine","blend","describe","ping","weather","translate",
    "calc","remindme","search","vote","invite","id","clean","uptime","latency","setprefix",
    "diagnose","perms","setnick","application","status","afk","profile","reminder",
    "urban","dictionary","joke","fact","quote","roll","flip","choose","hug","kiss",
    "pat","slap","highfive","dance","cry","laugh","smile","angry","think"
]

for cmd_name in placeholder_commands:
    @bot.command(name=cmd_name)
    async def placeholder(ctx):
        await ctx.send(f"✅ `{ctx.invoked_with}` command works! (placeholder)")

# -------------------- RUN --------------------
bot.run(os.environ["DISCORD_BOT_TOKEN"])