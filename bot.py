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
# MAINTENANCE MODE PRIVATE ALL
# ----------------------------
async def enable_maintenance(guild):
    for channel in guild.channels:
        try:
            await channel.set_permissions(
                guild.default_role,
                view_channel=False
            )
        except:
            continue

async def disable_maintenance(guild):
    for channel in guild.channels:
        try:
            await channel.set_permissions(
                guild.default_role,
                view_channel=True
            )
        except:
            continue

# ----------------------------
# ANTI NUKE SYSTEM
# ----------------------------
async def anti_nuke_action(guild, action_type):
    async for entry in guild.audit_logs(limit=1, action=action_type):
        user = entry.user

        if user.bot:
            return

        if user.id in whitelist:
            return

        try:
            await guild.ban(user, reason="🚨 Anti-Nuke Triggered")
            await send_log(guild, f"🚨 Anti-Nuke Banned: {user}")
        except:
            print("❌ Missing Ban Permission")

@bot.event
async def on_guild_channel_delete(channel):
    await anti_nuke_action(channel.guild, discord.AuditLogAction.channel_delete)

@bot.event
async def on_guild_role_delete(role):
    await anti_nuke_action(role.guild, discord.AuditLogAction.role_delete)

# ----------------------------
# ANTI-SPAM + BADWORDS AUTO TIMEOUT (5 MIN)
# ----------------------------
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if maintenance_mode and message.author.id != OWNER_ID:
        return

    # Badwords Timeout
    badwords = ["fuck", "bitch", "asshole"]
    if badwords_filter and any(word in message.content.lower() for word in badwords):
        await message.delete()
        until = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        await message.author.edit(timeout=until)

        await message.channel.send(
            f"🚨 {message.author.mention} Badword detected! Timeout 5 min."
        )
        return

    # Anti Spam Timeout
    user_id = message.author.id
    if user_id not in spam_users:
        spam_users[user_id] = {"count": 1, "time": datetime.datetime.utcnow()}
    else:
        spam_users[user_id]["count"] += 1

    diff = (datetime.datetime.utcnow() - spam_users[user_id]["time"]).seconds

    if diff <= 5 and spam_users[user_id]["count"] >= 6:
        until = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        await message.author.edit(timeout=until)

        await message.channel.send(
            f"🚨 {message.author.mention} Spam detected! Timeout 5 min."
        )

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

    now = datetime.datetime.utcnow()
    join_tracker.append(now)

    join_tracker = [t for t in join_tracker if (now - t).seconds < raid_time]

    if len(join_tracker) >= raid_limit and not raid_mode:
        await enable_lockdown(member.guild)

    await send_log(member.guild, f"👋 Welcome {member.mention} joined!")

# ----------------------------
# HELP MENU RED EMBED + BUTTONS
# ----------------------------
help_pages = [
    {
        "title": "🛡 Moderation Commands",
        "description":
        "`!kick @user reason` ➝ Kick member\n"
        "`!ban @user reason` ➝ Ban member\n"
        "`!timeout @user 10m` ➝ Mute temporarily\n"
    },
    {
        "title": "🚨 Security Protection",
        "description":
        "✅ Anti-Spam Auto Timeout (5min)\n"
        "✅ Badwords Auto Timeout (5min)\n"
        "✅ Anti-Nuke Auto Ban\n"
        "✅ Anti-Raid Lockdown\n"
    },
    {
        "title": "👑 Owner Commands",
        "description":
        "`!wl @user` ➝ Whitelist user\n"
        "`!maintenance on/off` ➝ Private/Public Server\n"
        "`!lockdown / !unlockdown`\n"
        "`!setlog #channel`\n"
    },
    {
        "title": "ℹ Info Commands",
        "description":
        "`!ping` ➝ Bot latency\n"
        "`!serverinfo` ➝ Server info\n"
        "`!userinfo @user`\n"
        "`!avatar`\n"
    }
]

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.page = 0

    async def update(self, message):
        embed = discord.Embed(
            title=help_pages[self.page]["title"],
            description=help_pages[self.page]["description"],
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Page {self.page+1}/{len(help_pages)}")
        await message.edit(embed=embed, view=self)

    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.danger)
    async def back(self, interaction, button):
        self.page = (self.page - 1) % len(help_pages)
        await self.update(interaction.message)
        await interaction.response.defer()

    @discord.ui.button(label="Next ➡", style=discord.ButtonStyle.danger)
    async def next(self, interaction, button):
        self.page = (self.page + 1) % len(help_pages)
        await self.update(interaction.message)
        await interaction.response.defer()

@bot.command()
async def help(ctx):
    view = HelpView()
    embed = discord.Embed(
        title=help_pages[0]["title"],
        description=help_pages[0]["description"],
        color=discord.Color.red()
    )
    await ctx.send(embed=embed, view=view)

# ----------------------------
# MODERATION COMMANDS
# ----------------------------
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    await member.kick(reason=reason)
    await ctx.send("✅ Kicked Successfully")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    await member.ban(reason=reason)
    await ctx.send("✅ Banned Successfully")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, time: str):
    amount = int(time[:-1])
    unit = time[-1]

    duration = datetime.timedelta(minutes=amount)
    until = datetime.datetime.utcnow() + duration

    await member.edit(timeout=until)
    await ctx.send("✅ Timed Out Successfully")

# ----------------------------
# OWNER COMMANDS
# ----------------------------
@bot.command()
async def wl(ctx, member: discord.Member):
    if ctx.author.id != OWNER_ID:
        return

    whitelist.add(member.id)
    await ctx.send("✅ User Whitelisted")

@bot.command()
async def maintenance(ctx, mode: str):
    global maintenance_mode
    if ctx.author.id != OWNER_ID:
        return

    if mode.lower() == "on":
        maintenance_mode = True
        await enable_maintenance(ctx.guild)
        await ctx.send("🛠 Maintenance ON (Server Private)")
    else:
        maintenance_mode = False
        await disable_maintenance(ctx.guild)
        await ctx.send("✅ Maintenance OFF (Server Public)")

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
    await ctx.send("✅ Log Channel Set")

# ----------------------------
# INFO COMMANDS
# ----------------------------
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong {round(bot.latency*1000)}ms")

@bot.command()
async def serverinfo(ctx):
    g = ctx.guild
    await ctx.send(f"📌 {g.name} | Members: {g.member_count}")

@bot.command()
async def userinfo(ctx, member: discord.Member):
    await ctx.send(f"👤 {member} Joined: {member.joined_at.date()}")

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(member.avatar.url)

# ----------------------------
# RUN BOT
# ----------------------------
bot.run(os.getenv("DISCORD_BOT_TOKEN"))