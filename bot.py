import discord
from discord.ext import commands
import datetime
import os
import re
import random

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
# PAGINATED HELP MENU (Fixed)
# ----------------------------
class HelpPages(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.page = 0
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

    async def update_embed(self, interaction):
        embed = discord.Embed(
            title="Moderation Bot Help Menu",
            description=self.pages[self.page],
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Page {self.page + 1}/{len(self.pages)}")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Previous Page", style=discord.ButtonStyle.primary)
    async def previous(self, interaction, button):
        self.page = (self.page - 1) % len(self.pages)
        await self.update_embed(interaction)

    @discord.ui.button(label="Next Page", style=discord.ButtonStyle.primary)
    async def next(self, interaction, button):
        self.page = (self.page + 1) % len(self.pages)
        await self.update_embed(interaction)

# ----------------------------
# FIXED HELP COMMAND
# ----------------------------
@bot.command()
async def help(ctx):
    view = HelpPages()
    embed = discord.Embed(
        title="Moderation Bot Help Menu",
        description=view.pages[0],  # Start with page 1 content
        color=discord.Color.blue()
    )
    embed.set_footer(text="Page 1/2")
    await ctx.send(embed=embed, view=view)

# ----------------------------
# INFO COMMANDS
# ----------------------------
@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency*1000)}ms")

@bot.command()
async def userinfo(ctx, member: discord.Member):
    await ctx.send(f"👤 {member} Joined: {member.joined_at.date()}")

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(member.avatar.url)

@bot.command()
async def si(ctx):
    g = ctx.guild
    embed = discord.Embed(
        title=f"📌 Server Info: {g.name}",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_thumbnail(url=g.icon.url if g.icon else None)
    embed.add_field(name="👑 Owner", value=g.owner.mention, inline=False)
    embed.add_field(name="🗓 Created On", value=g.created_at.strftime("%d %B %Y"), inline=False)
    embed.add_field(name="👥 Members", value=g.member_count, inline=False)
    embed.add_field(name="🎭 Roles", value=len(g.roles), inline=False)
    embed.add_field(name="📂 Channels", value=f"Text: {len(g.text_channels)}\nVoice: {len(g.voice_channels)}\nCategories: {len(g.categories)}", inline=False)
    embed.set_footer(text=f"Server ID: {g.id}")
    await ctx.send(embed=embed)

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
# FUN COMMANDS
# ----------------------------
@bot.command()
async def say(ctx, *, text):
    await ctx.send(text)

@bot.command()
async def ask(ctx, *, question):
    responses = ["Yes ✅", "No ❌", "Maybe 🤔", "Absolutely! 😎"]
    await ctx.send(f"{random.choice(responses)}")

@bot.command()
async def fight(ctx, member: discord.Member):
    outcomes = ["wins 🏆", "loses 💀", "ties 🤝"]
    await ctx.send(f"{ctx.author.mention} {random.choice(outcomes)} against {member.mention}")

@bot.command()
async def choose(ctx, *, options):
    opts = options.split()
    if len(opts) < 2:
        await ctx.send("Provide at least 2 options!")
    else:
        await ctx.send(f"I choose: {random.choice(opts)}")

# ----------------------------
# MUSIC PLACEHOLDER COMMANDS
# ----------------------------
@bot.command()
async def play(ctx, *, url):
    await ctx.send(f"Playing music from: {url}")

@bot.command()
async def stop(ctx):
    await ctx.send("Music stopped!")

@bot.command()
async def leaveadmin(ctx):
    await ctx.send("Leaving voice channel...")

# ----------------------------
# UTILITY
# ----------------------------
@bot.command()
async def invite(ctx):
    await ctx.send("Invite Sapphire Bot: <invite link>")

# ----------------------------
# RUN BOT
# ----------------------------
bot.run(os.getenv("DISCORD_BOT_TOKEN"))