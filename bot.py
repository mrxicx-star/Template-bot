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
anti_spam = True

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
# AUTO TIMEOUT FUNCTION
# ----------------------------
async def auto_timeout(member, minutes, reason):
    try:
        until = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
        await member.edit(timeout=until)
    except:
        pass

# ----------------------------
# ANTI-SPAM + ANTI-LINK + BADWORDS
# ----------------------------
@bot.event
async def on_message(message):

    if message.author.bot:
        return

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
        await auto_timeout(message.author, 5, "Posting Links")
        return

    # ----------------------------
    # Anti-Badwords
    # ----------------------------
    badwords = ["fuck", "bitch", "asshole"]
    if badwords_filter and any(word in message.content.lower() for word in badwords):
        await message.delete()
        await message.channel.send(
            f"⚠ {message.author.mention} Bad words not allowed!",
            delete_after=3
        )
        await auto_timeout(message.author, 5, "Bad Words Abuse")
        return

    # ----------------------------
    # Anti-Spam
    # ----------------------------
    if anti_spam:
        user_id = message.author.id

        if user_id not in spam_users:
            spam_users[user_id] = {"count": 1, "time": datetime.datetime.utcnow()}
        else:
            spam_users[user_id]["count"] += 1

        diff = (datetime.datetime.utcnow() - spam_users[user_id]["time"]).seconds

        if diff <= 5 and spam_users[user_id]["count"] >= 6:
            await message.channel.send(
                f"🚨 {message.author.mention} Spamming detected! Timeout 5 min."
            )
            await auto_timeout(message.author, 5, "Spam Detected")
            await send_log(message.guild, f"🚨 Spam Timeout: {message.author}")

            spam_users[user_id] = {"count": 0, "time": datetime.datetime.utcnow()}

        if diff > 5:
            spam_users[user_id] = {"count": 1, "time": datetime.datetime.utcnow()}

    await bot.process_commands(message)

# ----------------------------
# MEMBER JOIN + RAID TRACK
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
        "`!kick @user reason` ➝ Kick member\n"
        "`!ban @user reason` ➝ Ban member\n"
        "`!timeout @user 10m` ➝ Mute member\n"
    },
    {
        "title": "🚨 Security Protection",
        "description":
        "✅ Anti-Link Auto Timeout (5m)\n"
        "✅ Badwords Auto Timeout (5m)\n"
        "✅ Anti-Spam Auto Timeout (5m)\n"
        "✅ Anti-Raid Auto Lockdown\n"
    },
    {
        "title": "👑 Owner Commands",
        "description":
        "`!wl add @user`\n"
        "`!wl remove @user`\n"
        "`!wl list`\n"
        "`!wl panel` ➝ Control Panel\n"
        "`!lockdown / !unlockdown`\n"
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
# CONTROL PANEL VIEW
# ----------------------------
class ControlPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    async def refresh(self, interaction):
        embed = discord.Embed(
            title="🛡 Security Control Panel",
            color=discord.Color.blurple()
        )

        embed.add_field(name="Anti-Link", value="✅ ON" if anti_link else "❌ OFF")
        embed.add_field(name="Badwords", value="✅ ON" if badwords_filter else "❌ OFF")
        embed.add_field(name="Anti-Spam", value="✅ ON" if anti_spam else "❌ OFF")

        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Toggle Anti-Link", style=discord.ButtonStyle.green)
    async def toggle_link(self, interaction, button):
        global anti_link
        anti_link = not anti_link
        await interaction.response.defer()
        await self.refresh(interaction)

    @discord.ui.button(label="Toggle Badwords", style=discord.ButtonStyle.red)
    async def toggle_badwords(self, interaction, button):
        global badwords_filter
        badwords_filter = not badwords_filter
        await interaction.response.defer()
        await self.refresh(interaction)

    @discord.ui.button(label="Toggle Anti-Spam", style=discord.ButtonStyle.blurple)
    async def toggle_spam(self, interaction, button):
        global anti_spam
        anti_spam = not anti_spam
        await interaction.response.defer()
        await self.refresh(interaction)

# ----------------------------
# WL GROUP
# ----------------------------
@bot.group()
async def wl(ctx):
    if ctx.author.id != OWNER_ID:
        return
    if ctx.invoked_subcommand is None:
        await ctx.send("Use: `!wl add/remove/list/panel`")

@wl.command()
async def add(ctx, member: discord.Member):
    whitelist.add(member.id)
    await ctx.send(f"✅ Added {member.mention} to whitelist")

@wl.command()
async def remove(ctx, member: discord.Member):
    whitelist.discard(member.id)
    await ctx.send(f"❌ Removed {member.mention} from whitelist")

@wl.command()
async def list(ctx):
    if not whitelist:
        return await ctx.send("⚠ Whitelist empty")

    embed = discord.Embed(title="✅ Whitelisted Users", color=discord.Color.green())
    embed.description = "\n".join([f"<@{u}>" for u in whitelist])
    await ctx.send(embed=embed)

@wl.command()
async def panel(ctx):
    embed = discord.Embed(title="🛡 Security Control Panel", color=discord.Color.blurple())
    embed.description = "Click buttons to toggle protections"

    view = ControlPanel()
    await ctx.send(embed=embed, view=view)

# ----------------------------
# LOCKDOWN COMMANDS
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

# ----------------------------
# RUN BOT
# ----------------------------
bot.run(os.getenv("DISCORD_BOT_TOKEN"))