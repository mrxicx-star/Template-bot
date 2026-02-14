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
# HELP MENU
# ----------------------------
help_pages = [
    {
        "title": "🛡 Moderation Commands",
        "description":
        "!kick @user reason ➝ Kick member\n"
        "!ban @user reason ➝ Ban member\n"
        "!timeout @user 10m ➝ Temporary mute\n"
    },
    {
        "title": "⚠ Warning + Strike System",
        "description":
        "!warn @user reason ➝ Warn user\n"
        "!warns @user ➝ Show warnings\n"
        "!strike @user reason ➝ Give strike\n"
        "⚡ 3 strikes = Auto Ban\n"
    },
    {
        "title": "🚨 Anti-Raid Protection",
        "description":
        "✅ Auto Lockdown if raid detected\n"
        "!lockdown ➝ Manual Lockdown\n"
        "!unlockdown ➝ Disable Lockdown\n"
    },
    {
        "title": "👑 Owner Commands",
        "description":
        "!wl @user ➝ Toggle whitelist\n"
        "!wl ➝ Show whitelist\n"
        "!maintenance on/off ➝ Private/Public Server\n"
        "!setlog #channel\n"
        "!autorole @role\n"
    },
    {
        "title": "ℹ Info Commands",
        "description":
        "!ping ➝ Bot latency\n"
        "!serverinfo ➝ Server details\n"
        "!userinfo @user ➝ User info\n"
        "!avatar ➝ Avatar show\n"
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
# OWNER COMMANDS
# ----------------------------

# ✅ Maintenance Private/Public Feature Added
@bot.command()
async def maintenance(ctx, mode: str):

    global maintenance_mode

    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Only Owner can use this command!")

    mode = mode.lower()

    if mode == "on":
        maintenance_mode = True
        await ctx.send("🛠 Maintenance ON!\n🔒 Server Private Mode Enabled!")

        for channel in ctx.guild.channels:
            try:
                await channel.set_permissions(
                    ctx.guild.default_role,
                    view_channel=False
                )
            except:
                continue

        await send_log(ctx.guild, "🛠 Maintenance Enabled → Server Private!")

    elif mode == "off":
        maintenance_mode = False
        await ctx.send("✅ Maintenance OFF!\n🌍 Server Public Mode Enabled!")

        for channel in ctx.guild.channels:
            try:
                await channel.set_permissions(
                    ctx.guild.default_role,
                    view_channel=True,
                    send_messages=True
                )
            except:
                continue

        await send_log(ctx.guild, "✅ Maintenance Disabled → Server Public!")

    else:
        await ctx.send("❌ Use: `!maintenance on` or `!maintenance off`")

# ----------------------------
# RUN BOT
# ----------------------------
bot.run(os.getenv("DISCORD_BOT_TOKEN"))