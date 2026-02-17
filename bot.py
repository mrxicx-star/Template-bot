import discord
from discord.ext import commands, tasks
from discord.utils import get
import asyncio
import random
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ---------------------
# EVENTS
# ---------------------
@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")

@bot.event
async def on_guild_join(guild):
    print(f"Joined a new guild: {guild.name}")

# ---------------------
# HELP COMMAND
# ---------------------
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📜 Moderation Bot Commands",
        description="Here are all available commands:",
        color=discord.Color.purple()
    )

    commands_list = [
        # Moderation
        "!warn, !warnings, !clear, !mute, !unmute, !softban, !lock, !unlock, !slowmode, !modlogs, !notes, !addnote, !case, !roleinfo, !serverinfo, !userinfo, !tempban, !kick, !ban, !timeout",
        # Music
        "!play, !skip, !pause, !resume, !queue, !clear-queue, !stop, !loop, !shuffle, !volume, !nowplaying, !seek, !join, !leave, !lyrics",
        # Fun/Social
        "!8ball, !coinflip, !diceroll, !cat, !dog, !meme, !rps, !slots, !urbandictionary, !insult, !rank, !leaderboard, !giveaway, !poll, !avatar",
        # Utility / AI
        "!imagine, !blend, !describe, !ping, !help, !weather, !translate, !calc, !remindme, !search, !vote, !invite",
        # Power/Other
        "!id, !clean, !uptime, !latency, !setprefix, !diagnose, !perms, !setnick, !application, !status, !afk, !profile, !reminder, !urban, !dictionary, !joke, !fact, !quote, !roll, !flip, !choose, !hug, !kiss, !pat, !slap, !highfive, !dance, !cry, !laugh, !smile, !angry, !think",
        # Server Setup
        "!setupall, !del, !greetset"
    ]

    for cmd in commands_list:
        embed.add_field(name="\u200b", value=cmd, inline=False)

    await ctx.send(embed=embed)

# ---------------------
# SAMPLE MODERATION COMMANDS
# ---------------------
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
    await ctx.send(f"✅ {member} has been temporarily banned for {time} seconds. Reason: {reason}")
    await asyncio.sleep(time)
    await member.unban()
    await ctx.send(f"✅ {member} has been unbanned after {time} seconds.")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def delall(ctx):
    for channel in ctx.guild.channels:
        try:
            await channel.delete()
        except:
            pass
    await ctx.send("✅ All channels deleted.")

# ---------------------
# SETUP TEMPLATE COMMAND
# ---------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def setupall(ctx):
    """Setup all categories, channels, and roles (template)"""
    # Sample setup
    categories = ["SERVER SPAWN", "GATEWAY", "IMPORTANT", "YOUTUBE ZONE", "CHILL ZONE", "GAMING ZONE", "LEVEL ZONE", "EVENT ZONE", "VOICE ZONE", "MUSIC ZONE", "APPLICATION", "STAFF ZONE"]
    for cat in categories:
        existing = get(ctx.guild.categories, name=cat)
        if not existing:
            await ctx.guild.create_category(cat)

    # Roles example
    roles = ["ADMIN", "MOD", "TRIAL MOD", "YOUTUBER", "VERIFIED", "MEMBER"]
    for role in roles:
        existing_role = get(ctx.guild.roles, name=role)
        if not existing_role:
            await ctx.guild.create_role(name=role)

    await ctx.send("✅ Server template setup completed!")

# ---------------------
# GREET CHANNEL COMMAND
# ---------------------
greet_channel = None

@bot.command()
@commands.has_permissions(administrator=True)
async def greetchannelset(ctx, channel: discord.TextChannel):
    global greet_channel
    greet_channel = channel
    await ctx.send(f"✅ Welcome messages will now be sent in {channel.mention}")

@bot.event
async def on_member_join(member):
    if greet_channel:
        embed = discord.Embed(
            title=f"Welcome {member.name}!",
            description="We hope you enjoy your stay on this server 😄",
            color=discord.Color.green()
        )
        await greet_channel.send(embed=embed)

# ---------------------
# RUN BOT
# ---------------------
bot.run(os.getenv("DISCORD_TOKEN"))