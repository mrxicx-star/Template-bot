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
bot.remove_command("help")  # Remove all old help commands

OWNER_ID = None
log_channel_id = None
spam_users = {}
whitelist = set()
maintenance_mode = False
anti_link = True
badwords_filter = True

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
# ANTI-SPAM + BADWORDS AUTO TIMEOUT
# ----------------------------
@bot.event
async def on_message(message):
    if message.author.bot or (maintenance_mode and message.author.id != OWNER_ID):
        return

    # Badwords Filter
    badwords = ["fuck", "bitch", "asshole"]
    if badwords_filter and any(word in message.content.lower() for word in badwords):
        await message.delete()
        until = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        await message.author.edit(timeout=until)
        await message.channel.send(f"🚨 {message.author.mention} Badword detected! Timeout 5 min.")
        return

    # Anti-Link
    if anti_link and re.search(r"(https?://|discord\.gg/)", message.content):
        await message.delete()
        await message.channel.send(f"🚫 {message.author.mention} Links not allowed!", delete_after=3)
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
        await message.channel.send(f"🚨 {message.author.mention} Spam detected! Timeout 5 min.")
        spam_users[user_id] = {"count": 0, "time": datetime.datetime.utcnow()}
    if diff > 5:
        spam_users[user_id] = {"count": 1, "time": datetime.datetime.utcnow()}

    await bot.process_commands(message)

# ----------------------------
# FIXED HELP MENU (ONE EMBED ONLY)
# ----------------------------
class HelpMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.pages = [
            "> Use `/help <command>` to get more information\n\n"
            "> `/caseupdate`\n"
            "> `/caseclose`\n"
            "> `/mute`\n"
            "> `/namewarn`\n"
            "> `/purge`\n"
            "> `/setslowmode`\n"
            "> `/unmute`\n"
            "> `/unwarn`\n"
            "> `/warn`\n"
            "> `/warns`",
            "> Use `/help <command>` to get more information\n\n"
            "> `/help`\n"
            "> `/info`\n"
            "> `/list`\n"
            "> `/avatarinfo`\n"
            "> `/bannerinfo`\n"
            "> `/guildbannerinfo`\n"
            "> `/guildiconinfo`\n"
            "> `/guildmembercount`\n"
            "> `/guildsplashinfo`\n"
            "> `/stickerpackinfo`\n"
            "> `/userinfo`\n"
            "> `/casedelete`\n"
            "> `/caseinfo`\n"
            "> `/caselist`\n"
            "> `/casesplit`"
        ]
        self.page = 0

    async def update(self, interaction):
        embed = discord.Embed(
            title="Moderation Bot Help Menu",
            description=self.pages[self.page],
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Page {self.page + 1}/{len(self.pages)}")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Previous Page", style=discord.ButtonStyle.primary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page - 1) % len(self.pages)
        await self.update(interaction)

    @discord.ui.button(label="Next Page", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page + 1) % len(self.pages)
        await self.update(interaction)

@bot.command()
async def help(ctx):
    view = HelpMenu()
    embed = discord.Embed(
        title="Moderation Bot Help Menu",
        description=view.pages[0],
        color=discord.Color.blue()
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
async def mute(ctx, member: discord.Member, time: str):
    amount = int(time[:-1])
    until = datetime.datetime.utcnow() + datetime.timedelta(minutes=amount)
    await member.edit(timeout=until)
    await ctx.send(f"✅ Muted {member.mention} for {time}")

@bot.command()
async def unmute(ctx, member: discord.Member):
    await member.edit(timeout=None)
    await ctx.send(f"✅ Unmuted {member.mention}")

@bot.command()
async def warn(ctx, member: discord.Member, *, reason="No reason"):
    await ctx.send(f"⚠ {member.mention} has been warned. Reason: {reason}")

@bot.command()
async def unwarn(ctx, member: discord.Member):
    await ctx.send(f"✅ Removed warning from {member.mention}")

@bot.command()
async def purge(ctx, amount: int):
    if 2 <= amount <= 100:
        deleted = await ctx.channel.purge(limit=amount)
        await ctx.send(f"🗑 Purged {len(deleted)} messages", delete_after=5)
    else:
        await ctx.send("Amount must be between 2 and 100")

@bot.command()
async def setslowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"✅ Slowmode set to {seconds} seconds")

# ----------------------------
# INFO COMMANDS
# ----------------------------
@bot.command()
async def info(ctx):
    await ctx.send("Moderation Bot v1.0 – Ultimate Security & Help System")

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(
        title=f"User Info: {member}",
        color=discord.Color.green()
    )
    embed.add_field(name="Joined", value=member.joined_at.strftime("%d %B %Y"))
    embed.add_field(name="ID", value=member.id)
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def avatarinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(member.avatar.url)

# ----------------------------
# OWNER COMMANDS
# ----------------------------
@bot.command()
async def wl(ctx, member: discord.Member):
    if ctx.author.id != OWNER_ID:
        return
    whitelist.add(member.id)
    await ctx.send(f"✅ {member.mention} whitelisted")

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

# ----------------------------
# SERVER INFO COMMAND (!si)
# ----------------------------
@bot.command(name="si")
async def serverinfo(ctx):
    guild = ctx.guild

    owner = guild.owner
    verification = str(guild.verification_level).title()

    categories = len(guild.categories)
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    total_channels = categories + text_channels + voice_channels

    roles = len(guild.roles)
    emojis = len(guild.emojis)
    stickers = len(guild.stickers)

    members = guild.member_count
    created_at = guild.created_at.strftime("%d/%m/%Y %I:%M %p")

    embed = discord.Embed(
        title="📌 Server Info",
        description=f"**{guild.name}**",
        color=discord.Color.purple()
    )

    embed.add_field(name="👑 Owner", value=f"{owner.mention}", inline=False)
    embed.add_field(name="🔒 Verification Level", value=f"{verification}", inline=False)

    embed.add_field(name="🚀 Boost Tier", value=f"Tier {guild.premium_tier}", inline=False)

    embed.add_field(name="📂 Categories", value=f"{categories}", inline=True)
    embed.add_field(name="💬 Text Channels", value=f"{text_channels}", inline=True)
    embed.add_field(name="🔊 Voice Channels", value=f"{voice_channels}", inline=True)

    embed.add_field(name="📌 Total Channels", value=f"{total_channels}", inline=False)

    embed.add_field(name="✨ Stickers", value=f"{stickers}", inline=True)
    embed.add_field(name="😄 Emojis", value=f"{emojis}", inline=True)
    embed.add_field(name="🎭 Roles", value=f"{roles}", inline=True)

    embed.add_field(name="👥 Members", value=f"{members}", inline=False)

    embed.set_footer(
        text=f"ID: {guild.id} | Created: {created_at}"
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    await ctx.send(embed=embed)


# ----------------------------
# RUN BOT
# ----------------------------
bot.run(os.getenv("DISCORD_BOT_TOKEN"))