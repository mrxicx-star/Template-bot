import discord
from discord.ext import commands
import datetime
import os
import re

# ----------------------------
# BOT SETUP
# ----------------------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

warnings = {}
strikes = {}
spam_users = {}
whitelist = set()

maintenance_mode = False
anti_link = True
badwords_filter = True

log_channel_id = None
auto_role_id = None
OWNER_ID = None

# ----------------------------
# ANTI RAID SETTINGS
# ----------------------------
join_tracker = []
raid_mode = False
raid_limit = 5
raid_time = 10

# ----------------------------
# BOT READY
# ----------------------------
@bot.event
async def on_ready():
    global OWNER_ID
    app_info = await bot.application_info()
    OWNER_ID = app_info.owner.id

    print(f"✅ Bot Online: {bot.user}")
    print(f"👑 Owner Loaded: {OWNER_ID}")

# ----------------------------
# LOG SYSTEM
# ----------------------------
async def send_log(guild, msg):
    if log_channel_id:
        channel = guild.get_channel(log_channel_id)
        if channel:
            await channel.send(msg)

# ----------------------------
# LOCKDOWN FUNCTIONS
# ----------------------------
async def enable_lockdown(guild):
    global raid_mode
    raid_mode = True

    for channel in guild.text_channels:
        try:
            await channel.set_permissions(guild.default_role, send_messages=False)
        except:
            continue

    await send_log(guild, "🚨 ANTI-RAID TRIGGERED! Server Locked Down!")

async def disable_lockdown(guild):
    global raid_mode
    raid_mode = False

    for channel in guild.text_channels:
        try:
            await channel.set_permissions(guild.default_role, send_messages=True)
        except:
            continue

    await send_log(guild, "✅ Lockdown Disabled! Server Unlocked!")

# ----------------------------
# ANTI-SPAM + ANTI-LINK + BADWORDS
# ----------------------------
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # Maintenance Mode Fix
    if maintenance_mode and message.author.id != OWNER_ID:
        return

    # ----------------------------
    # Anti-Link
    # ----------------------------
    if anti_link and re.search(r"(https?://|discord\.gg/)", message.content):
        await message.delete()
        await message.channel.send(
            f"🚫 {message.author.mention} Links not allowed!",
            delete_after=3
        )
        return

    # ----------------------------
    # Anti-Badwords + Auto Timeout 5 Min
    # ----------------------------
    badwords = ["fuck", "bitch", "asshole"]

    if badwords_filter and any(word in message.content.lower() for word in badwords):
        await message.delete()

        try:
            until = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
            await message.author.edit(timeout=until)

            await message.channel.send(
                f"🚨 {message.author.mention} used bad words!\n⏳ Timed out for **5 minutes**!",
                delete_after=5
            )

            await send_log(
                message.guild,
                f"⚠ Badwords Timeout: {message.author} muted for 5 minutes"
            )

        except:
            await message.channel.send("❌ I don't have timeout permission!")

        return

    # ----------------------------
    # Anti-Spam + Auto Timeout 5 Min
    # ----------------------------
    user_id = message.author.id

    if user_id not in spam_users:
        spam_users[user_id] = {"count": 1, "time": datetime.datetime.utcnow()}
    else:
        spam_users[user_id]["count"] += 1

    diff = (datetime.datetime.utcnow() - spam_users[user_id]["time"]).seconds

    if diff <= 5 and spam_users[user_id]["count"] >= 6:
        try:
            until = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
            await message.author.edit(timeout=until)

            await message.channel.send(
                f"🚨 {message.author.mention} Spamming detected!\n⏳ Timed out for **5 minutes**!"
            )

            await send_log(message.guild, f"🚨 Spam Timeout: {message.author}")

        except:
            pass

        spam_users[user_id] = {"count": 0, "time": datetime.datetime.utcnow()}

    if diff > 5:
        spam_users[user_id] = {"count": 1, "time": datetime.datetime.utcnow()}

    await bot.process_commands(message)

# ----------------------------
# MEMBER JOIN + ANTI RAID
# ----------------------------
@bot.event
async def on_member_join(member):
    global join_tracker

    if auto_role_id:
        role = member.guild.get_role(auto_role_id)
        if role:
            await member.add_roles(role)

    now = datetime.datetime.utcnow()
    join_tracker.append(now)

    join_tracker = [t for t in join_tracker if (now - t).seconds < raid_time]

    if len(join_tracker) >= raid_limit and not raid_mode:
        await enable_lockdown(member.guild)

    await send_log(member.guild, f"👋 Welcome {member.mention} joined!")

# ----------------------------
# OWNER COMMANDS
# ----------------------------
@bot.command()
async def lockdown(ctx):
    if ctx.author.id != OWNER_ID:
        return
    await enable_lockdown(ctx.guild)
    await ctx.send("🚨 Lockdown Enabled!")

@bot.command()
async def unlockdown(ctx):
    if ctx.author.id != OWNER_ID:
        return
    await disable_lockdown(ctx.guild)
    await ctx.send("✅ Lockdown Disabled!")

@bot.command()
async def setlog(ctx, channel: discord.TextChannel):
    global log_channel_id
    if ctx.author.id != OWNER_ID:
        return
    log_channel_id = channel.id
    await ctx.send("✅ Log channel set")

@bot.command()
async def autorole(ctx, role: discord.Role):
    global auto_role_id
    if ctx.author.id != OWNER_ID:
        return
    auto_role_id = role.id
    await ctx.send("✅ AutoRole set")

# ----------------------------
# INFO COMMANDS
# ----------------------------
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong {round(bot.latency*1000)}ms")

# ----------------------------
# RUN BOT
# ----------------------------
bot.run(os.getenv("DISCORD_BOT_TOKEN"))