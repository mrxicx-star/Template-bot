import discord
from discord.ext import commands
import datetime
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
greet_channel = None
welcome_msg = "Welcome to the server!"

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
    global maintenance_mode
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
# HELP MENU
# ----------------------------
class HelpMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.pages = [
            "> Use !help <command> to get more information\n\n"
            "> !help\n"
            "> !info\n"
            "> !avatarinfo\n"
            "> !user-info\n"
            "> !server-info\n"
            "> !kick\n"
            "> !ban\n"
            "> !mute\n"
            "> !unmute\n"
            "> !timeout\n"
            "> !warn\n"
            "> !infractions\n"
            "> !purge\n"
            "> !clear\n"
            "> !slowmode\n"
            "> !lock\n"
            "> !unlock\n"
            "> !nuke\n"
            "> !setlog\n"
            "> !modrole\n"
            "> !autorole\n"
            "> !addrole\n"
            "> !removerole\n"
            "> !tempban\n"
            "> !tempmute\n"
            "> !reason\n"
            "> !cases\n"
            "> !warn-limit\n"
            "> !softban\n"
            "> !massban\n"
            "> !role-info\n"
            "> !whois\n"
            "> !pardon\n"
            "> !warn-clear\n"
            "> !setupall\n"
            "> !greetchannelset"
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
# SETUP ALL
# ----------------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def setupall(ctx):
    guild = ctx.guild
    categories_channels = {
        "SERVER SPAWN": [("・entrance", "text"), ("・overview", "text"), ("・server-boost", "text")],
        "GATEWAY": [("・self-role", "text"), ("・updates", "text"), ("・starboard", "text")],
        "IMPORTANT": [("・announces", "text"), ("・giveaway", "text"), ("・invite", "text")],
        "YOUTUBE ZONE": [("・yt-notification", "text"), ("・suggestions", "text")],
        "CHILL ZONE": [("・chill-chat", "text"), ("・gaming-chat", "text"), ("・toxic-chat", "text")],
        "GAMING ZONE": [("・owo", "text"), ("・aki", "text"), ("・poki", "text")],
        "LEVEL ZONE": [("・level-up", "text"), ("・level-chack", "text")],
        "EVENT ZONE": [("・event", "text"), ("・event-announces", "text")],
        "VOICE ZONE": [("General Vc", "voice"), ("Chill Vc", "voice"), ("Duo Vc", "voice"), ("Trio Vc", "voice"), ("SQuad Vc", "voice")],
        "MUSIC ZONE": [("music-chat", "text"), ("Music Vc", "voice")],
        "APPLICATION": [("report", "text"), ("staff-apply", "text")],
        "STAFF ZONE": [("staff-chat", "text"), ("staff-announces", "text")],
    }

    for cat_name, channels in categories_channels.items():
        category = discord.utils.get(guild.categories, name=cat_name)
        if not category:
            category = await guild.create_category(cat_name)
        for ch_name, ch_type in channels:
            existing = discord.utils.get(guild.channels, name=ch_name)
            if existing:
                continue
            if ch_type == "text":
                await guild.create_text_channel(ch_name, category=category)
            elif ch_type == "voice":
                await guild.create_voice_channel(ch_name, category=category)

    await ctx.send("✅ Setup complete! All channels created correctly.")

# ----------------------------
# DELETE ALL CHANNELS / ROLES
# ----------------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def deleteall(ctx):
    for channel in ctx.guild.channels:
        try:
            await channel.delete()
        except:
            continue
    for role in ctx.guild.roles:
        if role.is_default():
            continue
        try:
            await role.delete()
        except:
            continue
    await ctx.send("✅ All channels and roles deleted!")

# ----------------------------
# GREET CHANNEL SET
# ----------------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def greetchannelset(ctx, channel: discord.TextChannel = None):
    global greet_channel
    if channel:
        greet_channel = channel
        await ctx.send(f"✅ Welcome messages will be sent in {channel.mention}")
    else:
        await ctx.send("❌ Please specify a text channel.")

@bot.event
async def on_member_join(member):
    if greet_channel:
        await greet_channel.send(f"{member.mention} {welcome_msg}")

# ----------------------------
# RUN BOT
# ----------------------------
bot.run(os.getenv("DISCORD_BOT_TOKEN"))