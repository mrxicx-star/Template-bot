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

    if maintenance_mode and message.author.id != OWNER_ID:
        return

    # Anti-Link
    if anti_link and re.search(r"(https?://|discord\.gg/)", message.content):
        await message.delete()
        await message.channel.send(
            f"🚫 {message.author.mention} Links not allowed!",
            delete_after=3
        )
        return

    # Anti-Badwords
    badwords = ["fuck", "bitch", "asshole"]
    if badwords_filter and any(word in message.content.lower() for word in badwords):
        await message.delete()
        await message.channel.send(
            f"⚠ {message.author.mention} Bad words not allowed!",
            delete_after=3
        )
        return

    # Anti-Spam
    user_id = message.author.id
    if user_id not in spam_users:
        spam_users[user_id] = {"count": 1, "time": datetime.datetime.utcnow()}
    else:
        spam_users[user_id]["count"] += 1

    diff = (datetime.datetime.utcnow() - spam_users[user_id]["time"]).seconds

    if diff <= 5 and spam_users[user_id]["count"] >= 6:
        until = datetime.datetime.utcnow() + datetime.timedelta(minutes=2)
        await message.author.edit(timeout=until)

        await message.channel.send(
            f"🚨 {message.author.mention} Spamming detected! Muted 2 min."
        )
        await send_log(message.guild, f"🚨 Spam muted: {message.author}")

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
# HELP MENU (FULL EXPLAIN)
# ----------------------------
help_pages = [
    {
        "title": "🛡 Moderation Commands",
        "description":
        "`!kick @user reason` ➝ Kick member\n"
        "`!ban @user reason` ➝ Ban member\n"
        "`!timeout @user 10m` ➝ Temporary mute\n"
    },
    {
        "title": "⚠ Warning + Strike System",
        "description":
        "`!warn @user reason` ➝ Warn user\n"
        "`!warns @user` ➝ Show warnings\n"
        "`!strike @user reason` ➝ Give strike\n"
        "⚡ 3 strikes = Auto Ban\n"
    },
    {
        "title": "🚨 Anti-Raid Protection",
        "description":
        "✅ Auto Lockdown if raid detected\n"
        "`!lockdown` ➝ Manual Lockdown\n"
        "`!unlockdown` ➝ Disable Lockdown\n"
    },
    {
        "title": "👑 Owner Commands",
        "description":
        "`!wl @user` ➝ Toggle whitelist\n"
        "`!wl` ➝ Show whitelist\n"
        "`!maintenance on/off`\n"
        "`!setlog #channel`\n"
        "`!autorole @role`\n"
    },
    {
        "title": "ℹ Info Commands",
        "description":
        "`!ping` ➝ Bot latency\n"
        "`!serverinfo` ➝ Server details\n"
        "`!userinfo @user` ➝ User info\n"
        "`!avatar` ➝ Avatar show\n"
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
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Page {self.page+1}/{len(help_pages)}")
        await message.edit(embed=embed, view=self)

    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.gray)
    async def back(self, interaction, button):
        self.page = (self.page - 1) % len(help_pages)
        await self.update(interaction.message)
        await interaction.response.defer()

    @discord.ui.button(label="Next ➡", style=discord.ButtonStyle.gray)
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
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=view)

# ----------------------------
# COMMANDS
# ----------------------------
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    await member.kick(reason=reason)
    await ctx.send(f"✅ Kicked {member.mention}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    await member.ban(reason=reason)
    await ctx.send(f"✅ Banned {member.mention}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, time: str):
    unit = time[-1]
    amount = int(time[:-1])

    duration = datetime.timedelta(minutes=amount) if unit == "m" else None
    if not duration:
        return await ctx.send("❌ Example: 10m")

    until = datetime.datetime.utcnow() + duration
    await member.edit(timeout=until)
    await ctx.send(f"✅ Timed out {member.mention}")

@bot.command()
async def warn(ctx, member: discord.Member, *, reason="No reason"):
    warnings.setdefault(member.id, []).append(reason)
    await ctx.send(f"⚠ Warned {member.mention}")

@bot.command()
async def warns(ctx, member: discord.Member):
    user_warns = warnings.get(member.id, [])
    if not user_warns:
        return await ctx.send("✅ No warnings.")
    await ctx.send("\n".join(user_warns))

@bot.command()
async def strike(ctx, member: discord.Member, *, reason="No reason"):
    strikes.setdefault(member.id, []).append(reason)
    count = len(strikes[member.id])

    await ctx.send(f"⚔ Strike {count}/3 for {member.mention}")
    if count >= 3:
        await member.ban(reason="3 Strikes reached")
        await ctx.send("⛔ Auto banned!")

# ----------------------------
# OWNER COMMANDS
# ----------------------------
@bot.command()
async def wl(ctx, member: discord.Member = None):
    if ctx.author.id != OWNER_ID:
        return

    if member is None:
        if not whitelist:
            return await ctx.send("⚠ Whitelist empty.")
        return await ctx.send("\n".join([f"<@{u}>" for u in whitelist]))

    if member.id in whitelist:
        whitelist.remove(member.id)
        await ctx.send("❌ Removed from whitelist")
    else:
        whitelist.add(member.id)
        await ctx.send("✅ Added to whitelist")

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
# INFO
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