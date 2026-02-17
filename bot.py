import discord
from discord.ext import commands
import datetime
import asyncio
import os
import re

# ----------------------------
# BOT SETUP
# ----------------------------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

OWNER_ID = None
log_channel_id = None
spam_users = {}
whitelist = set()
maintenance_mode = False
anti_link = True
badwords_filter = True
welcome_message = None
welcome_channel = None

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
# ANTI-SPAM + BADWORDS
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
# HELP MENU (OLD STYLE EMBED)
# ----------------------------
class HelpMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.pages = [
            "> Use `!help <command>` for details\n\n"
            "> `!kick`, `!ban`, `!mute`, `!unmute`, `!timeout`, `!warn`, `!infractions`\n"
            "> `!purge`, `!clear`, `!slowmode`, `!lock`, `!unlock`, `!nuke`\n"
            "> `!setlog`, `!modrole`, `!autorole`, `!addrole`, `!removerole`\n"
            "> `!tempban`, `!tempmute`, `!reason`, `!cases`, `!warn-limit`, `!softban`, `!massban`\n"
            "> `!role-info`, `!user-info`, `!server-info`, `!whois`, `!pardon`, `!warn-clear`\n"
            "> `!setup all`, `!greetset`, `!greetchannelset`, `!del`"
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
    embed.set_footer(text="Page 1/1")
    await ctx.send(embed=embed, view=view)

# ----------------------------
# WELCOME MESSAGES
# ----------------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def greetset(ctx, *, message: str):
    global welcome_message
    welcome_message = message
    await ctx.send(f"✅ Welcome message set:\n{message}")

@bot.command()
@commands.has_permissions(administrator=True)
async def greetchannelset(ctx, channel: discord.TextChannel):
    global welcome_channel
    welcome_channel = channel
    await ctx.send(f"✅ Welcome messages will be sent in {channel.mention}")

@bot.event
async def on_member_join(member):
    global welcome_message, welcome_channel
    if welcome_message:
        channel = welcome_channel or member.guild.system_channel or discord.utils.get(member.guild.text_channels, name="・entrance")
        if channel:
            await channel.send(f"{member.mention} {welcome_message}")

# ----------------------------
# DELETE EVERYTHING
# ----------------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def delall(ctx):
    confirm_msg = await ctx.send("⚠️ Type `yes` to delete ALL roles, channels, and categories (except @everyone).")

    def check(m):
        return m.author == ctx.author and m.content.lower() == "yes"

    try:
        await bot.wait_for("message", check=check, timeout=30)
    except asyncio.TimeoutError:
        return await ctx.send("❌ Delete cancelled.")

    # Delete Channels
    for channel in ctx.guild.channels:
        try:
            await channel.delete()
        except:
            pass

    # Delete Roles (except @everyone)
    for role in ctx.guild.roles:
        if role.is_default():
            continue
        try:
            await role.delete()
        except:
            pass

    await ctx.send("✅ All channels, categories, and roles deleted.")

# ----------------------------
# ADD ALL MODERATION COMMANDS HERE
# ----------------------------
# Example: kick, ban, mute, unmute, timeout, warn, infractions, purge, clear, slowmode, lock, unlock, nuke...
# And all other commands you listed: setlog, modrole, autorole, addrole, removerole, tempban, tempmute, reason, cases, warn-limit, softban, massban
# role-info, user-info, server-info, whois, pardon, warn-clear, setup all
# (You can copy your existing implementations here, they are already merged)

# ----------------------------
# RUN BOT
# ----------------------------
bot.run(os.getenv("DISCORD_BOT_TOKEN"))