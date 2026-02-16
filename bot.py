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


spam_users = {}
whitelist = set()

maintenance_mode = False
anti_link = True
badwords_filter = True

log_channel_id = None
OWNER_ID = None

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
    for channel in guild.text_channels:
        try:
            await channel.set_permissions(guild.default_role, send_messages=False)
        except:
            continue
    await send_log(guild, "🚨 Server Lockdown Enabled!")

async def disable_lockdown(guild):
    for channel in guild.text_channels:
        try:
            await channel.set_permissions(guild.default_role, send_messages=True)
        except:
            continue
    await send_log(guild, "✅ Server Lockdown Disabled!")

# ----------------------------
# MAINTENANCE MODE
# ----------------------------
async def enable_maintenance(guild):
    for channel in guild.channels:
        try:
            await channel.set_permissions(guild.default_role, view_channel=False)
        except:
            continue

async def disable_maintenance(guild):
    for channel in guild.channels:
        try:
            await channel.set_permissions(guild.default_role, view_channel=True)
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
# ANTI-SPAM + BADWORDS AUTO TIMEOUT
# ----------------------------
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if maintenance_mode and message.author.id != OWNER_ID:
        return

    # Badwords Filter
    badwords = ["fuck", "bitch", "asshole"]
    if badwords_filter and any(word in message.content.lower() for word in badwords):
        await message.delete()
        until = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        await message.author.edit(timeout=until)

        await message.channel.send(
            f"🚨 {message.author.mention} Badword detected! Timeout 5 min."
        )
        return

    # Anti-Link
    if anti_link and re.search(r"(https?://|discord\.gg/)", message.content):
        await message.delete()
        await message.channel.send(
            f"🚫 {message.author.mention} Links not allowed!",
            delete_after=3
        )
        return

    # Anti Spam
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

    # ✅ FIXED DUPLICATE COMMAND ISSUE
    await bot.process_commands(message)

# ----------------------------
# HELP MENU WITH BUTTONS
# ----------------------------
class HelpButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    async def update_embed(self, interaction, title, desc):
        embed = discord.Embed(
            title=title,
            description=desc,
            color=discord.Color.red()
        )
        embed.set_footer(text="🚨 Ultimate Security Bot Help Menu")

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🛡 Moderation", style=discord.ButtonStyle.danger)
    async def moderation(self, interaction, button):
        await self.update_embed(
            interaction,
            "🛡 Moderation Commands",
            "`!kick @user reason` ➝ Kick member\n"
            "`!ban @user reason` ➝ Ban member\n"
            "`!timeout @user 10m` ➝ Temporary mute\n"
            "`!lockdown` ➝ Lock server\n"
            "`!unlockdown` ➝ Unlock server\n"
        )

    @discord.ui.button(label="🚨 Security", style=discord.ButtonStyle.danger)
    async def security(self, interaction, button):
        await self.update_embed(
            interaction,
            "🚨 Security Protection",
            "✅ Anti-Spam Auto Timeout (5 min)\n"
            "✅ Badwords Auto Timeout (5 min)\n"
            "✅ Anti-Link Delete\n"
            "✅ Anti-Nuke Auto Ban\n"
        )

    @discord.ui.button(label="👑 Owner", style=discord.ButtonStyle.danger)
    async def owner(self, interaction, button):
        await self.update_embed(
            interaction,
            "👑 Owner Commands",
            "`!wl @user` ➝ Whitelist user\n"
            "`!maintenance on` ➝ Private Server\n"
            "`!maintenance off` ➝ Public Server\n"
            "`!setlog #channel` ➝ Set log channel\n"
        )

    @discord.ui.button(label="ℹ Info", style=discord.ButtonStyle.danger)
    async def info(self, interaction, button):
        await self.update_embed(
            interaction,
            "ℹ Info Commands",
            "`!ping` ➝ Bot latency\n"
            "`!userinfo @user` ➝ User info\n"
            "`!avatar` ➝ Show avatar\n"
            "`!si` ➝ Detailed Server Info\n"
        )

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🚨 Ultimate Security Bot Help Menu",
        description="Click buttons below to view commands.",
        color=discord.Color.red()
    )
    embed.set_footer(text="All Commands Working ✅")

    await ctx.send(embed=embed, view=HelpButtons())

# ----------------------------
# MODERATION COMMANDS
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
    amount = int(time[:-1])
    until = datetime.datetime.utcnow() + datetime.timedelta(minutes=amount)
    await member.edit(timeout=until)
    await ctx.send(f"✅ Timed out {member.mention}")

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
    await ctx.send(f"@realxicx {round(bot.latency*1000)}ms")

@bot.command()
async def userinfo(ctx, member: discord.Member):
    await ctx.send(f"👤 {member} Joined: {member.joined_at.date()}")

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(member.avatar.url)

# ----------------------------
# DETAILED SERVER INFO COMMAND
# ----------------------------
@bot.command()
async def si(ctx):
    g = ctx.guild

    embed = discord.Embed(
        title=f"📌 Server Info: {g.name}",
        color=discord.Color.red(),
        timestamp=datetime.datetime.utcnow()
    )

    embed.set_thumbnail(url=g.icon.url if g.icon else None)

    embed.add_field(name="👑 Owner", value=g.owner.mention, inline=False)
    embed.add_field(
        name="🗓 Created On",
        value=g.created_at.strftime("%d %B %Y"),
        inline=False
    )
    embed.add_field(name="👥 Members", value=g.member_count, inline=False)
    embed.add_field(name="🎭 Roles", value=len(g.roles), inline=False)

    embed.add_field(
        name="📂 Channels",
        value=f"Text: {len(g.text_channels)}\nVoice: {len(g.voice_channels)}\nCategories: {len(g.categories)}",
        inline=False
    )

    embed.set_footer(text=f"Server ID: {g.id}")

    await ctx.send(embed=embed)

# ----------------------------
# RUN BOT
# ----------------------------
bot.run(os.getenv("DISCORD_BOT_TOKEN"))