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

OWNER_ID = None
log_channel_id = None
spam_users = {}
whitelist = set()

maintenance_mode = False
anti_link = True
badwords_filter = True

warn_data = {}

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

async def disable_lockdown(guild):
    for channel in guild.text_channels:
        try:
            await channel.set_permissions(guild.default_role, send_messages=True)
        except:
            continue

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
# ANTI-NUKE SYSTEM
# ----------------------------
async def anti_nuke_action(guild, action_type):
    async for entry in guild.audit_logs(limit=1, action=action_type):
        user = entry.user

        if user.bot or user.id in whitelist:
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
# ANTI-SPAM + BADWORDS TIMEOUT
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

    # Anti-Spam
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
# HELP MENU BUTTON SYSTEM
# ----------------------------
class HelpMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.pages = [
            "**Use `!help <command>` to get more information**\n\n"
            "🔹 `!mute`\n"
            "🔹 `!unmute`\n"
            "🔹 `!warn`\n"
            "🔹 `!warns`\n"
            "🔹 `!unwarn`\n"
            "🔹 `!purge`\n"
            "🔹 `!kick`\n"
            "🔹 `!ban`\n"
            "🔹 `!setslowmode`\n"
            "🔹 `!namewarn`\n",

            "**Use `!help <command>` to get more information**\n\n"
            "🔸 `!userinfo`\n"
            "🔸 `!avatarinfo`\n"
            "🔸 `!bannerinfo`\n"
            "🔸 `!guildiconinfo`\n"
            "🔸 `!guildbannerinfo`\n"
            "🔸 `!guildmembercount`\n"
            "🔸 `!stickerpackinfo`\n"
            "🔸 `!si` (Server Info)\n"
            "🔸 `!maintenance on/off`\n"
            "🔸 `!lockdown`\n"
            "🔸 `!unlockdown`\n"
        ]

        self.page = 0

    async def update(self, interaction):
        embed = discord.Embed(
            title="📌 Moderation Bot Help Menu",
            description=self.pages[self.page],
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Page {self.page+1}/{len(self.pages)}")

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⬅ Previous", style=discord.ButtonStyle.primary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page - 1) % len(self.pages)
        await self.update(interaction)

    @discord.ui.button(label="Next ➡", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page + 1) % len(self.pages)
        await self.update(interaction)

@bot.command()
async def help(ctx):
    view = HelpMenu()

    embed = discord.Embed(
        title="📌 Moderation Bot Help Menu",
        description=view.pages[0],
        color=discord.Color.red()
    )
    embed.set_footer(text="Page 1/2")

    await ctx.send(embed=embed, view=view)

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
async def mute(ctx, member: discord.Member, minutes: int):
    until = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
    await member.edit(timeout=until)
    await ctx.send(f"✅ Muted {member.mention} for {minutes} min")

@bot.command()
async def unmute(ctx, member: discord.Member):
    await member.edit(timeout=None)
    await ctx.send(f"✅ Unmuted {member.mention}")

# ----------------------------
# WARN SYSTEM
# ----------------------------
@bot.command()
async def warn(ctx, member: discord.Member, *, reason="No reason"):
    warn_data[member.id] = warn_data.get(member.id, 0) + 1
    await ctx.send(f"⚠ Warned {member.mention}\nReason: {reason}")

@bot.command()
async def warns(ctx, member: discord.Member):
    count = warn_data.get(member.id, 0)
    await ctx.send(f"⚠ {member.mention} has **{count}** warnings.")

@bot.command()
async def unwarn(ctx, member: discord.Member):
    warn_data[member.id] = 0
    await ctx.send(f"✅ Cleared warnings for {member.mention}")

@bot.command()
async def namewarn(ctx, member: discord.Member):
    await ctx.send(f"🚨 {member.mention} Name Warning Issued!")

# ----------------------------
# PURGE + SLOWMODE
# ----------------------------
@bot.command()
async def purge(ctx, amount: int):
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"🗑 Deleted {len(deleted)} messages", delete_after=3)

@bot.command()
async def setslowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"✅ Slowmode set to {seconds}s")

# ----------------------------
# INFO COMMANDS
# ----------------------------
@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author

    embed = discord.Embed(
        title=f"User Info: {member}",
        color=discord.Color.green()
    )

    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%d %B %Y"))

    embed.set_thumbnail(url=member.avatar.url)

    await ctx.send(embed=embed)

@bot.command()
async def avatarinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(member.avatar.url)

@bot.command()
async def bannerinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    user = await bot.fetch_user(member.id)

    if user.banner:
        await ctx.send(user.banner.url)
    else:
        await ctx.send("❌ No banner found.")

# ----------------------------
# SERVER INFO COMMAND (Screenshot Style)
# ----------------------------
@bot.command(name="si")
async def serverinfo(ctx):
    guild = ctx.guild

    embed = discord.Embed(
        title="Server Info",
        description=f"**{guild.name}**",
        color=discord.Color.purple()
    )

    embed.add_field(name="Owner", value=guild.owner.mention, inline=False)
    embed.add_field(name="Verification Level", value=str(guild.verification_level).title(), inline=False)
    embed.add_field(name="Boosts", value=f"Tier {guild.premium_tier}", inline=False)

    embed.add_field(name="Category Channels", value=len(guild.categories), inline=True)
    embed.add_field(name="Text Channels", value=len(guild.text_channels), inline=True)
    embed.add_field(name="Voice Channels", value=len(guild.voice_channels), inline=True)

    embed.add_field(name="Total Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Total Members", value=guild.member_count, inline=True)

    created_at = guild.created_at.strftime("%d/%m/%Y %I:%M %p")

    embed.set_footer(text=f"Id: {guild.id} | Created at: {created_at}")

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    await ctx.send(embed=embed)

# ----------------------------
# SETUP ALL COMMAND
# ----------------------------
@bot.command(name="setupall")
async def setupall(ctx):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Only Owner can use this!")

    guild = ctx.guild
    await ctx.send("⚙ Setting up server... Please wait!")

    # ---------- ROLES ----------
    roles_to_create = [
        ("👑 Owner", discord.Color.gold()),
        ("🛡 Admin", discord.Color.red()),
        ("⚔ Moderator", discord.Color.blue()),
        ("💎 VIP", discord.Color.purple()),
        ("👤 Member", discord.Color.green()),
    ]

    for role_name, role_color in roles_to_create:
        if not discord.utils.get(guild.roles, name=role_name):
            await guild.create_role(name=role_name, color=role_color)

    # ---------- CATEGORIES + CHANNELS ----------
    categories = {
        "🔔 INFORMATION": ["📌rules", "📢announcements", "📜server-info"],
        "💬 COMMUNITY": ["💭general-chat", "😂memes", "🎵music"],
        "🛡 MODERATION": ["🚨mod-logs", "🔒reports", "⚙bot-commands"],
        "🎮 FUN ZONE": ["🎲games", "🐾bots", "🎁giveaways"]
    }

    for cat_name, channels in categories.items():
        category = discord.utils.get(guild.categories, name=cat_name)

        if not category:
            category = await guild.create_category(cat_name)

        for ch in channels:
            if not discord.utils.get(guild.text_channels, name=ch):
                await guild.create_text_channel(ch, category=category)

    # ---------- VOICE CHANNELS ----------
    voice_category = discord.utils.get(guild.categories, name="🎧 VOICE")
    if not voice_category:
        voice_category = await guild.create_category("🎧 VOICE")

    voice_channels = ["🔊 General VC", "🎵 Music VC", "🎮 Gaming VC"]

    for vc in voice_channels:
        if not discord.utils.get(guild.voice_channels, name=vc):
            await guild.create_voice_channel(vc, category=voice_category)

    await ctx.send("✅ Setup Completed! Server is Ready 🚀")


# ----------------------------
# OWNER COMMANDS
# ----------------------------
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
async def wl(ctx, member: discord.Member):
    if ctx.author.id != OWNER_ID:
        return
    whitelist.add(member.id)
    await ctx.send(f"✅ {member.mention} added to whitelist!")

# ----------------------------
# RUN BOT
# ----------------------------
bot.run(os.getenv("DISCORD_BOT_TOKEN"))