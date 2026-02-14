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

# ----------------------------
# BOT READY
# ----------------------------
@bot.event
async def on_ready():
    print(f"✅ Bot Online: {bot.user}")

# ----------------------------
# LOG SYSTEM
# ----------------------------
async def send_log(guild, msg):
    global log_channel_id
    if log_channel_id:
        channel = guild.get_channel(log_channel_id)
        if channel:
            await channel.send(msg)

# ----------------------------
# ANTI-SPAM + ANTI-LINK + BADWORDS
# ----------------------------
@bot.event
async def on_message(message):
    global maintenance_mode

    if message.author.bot:
        return

    if maintenance_mode and message.author.id != bot.owner_id:
        return

    # Anti-Link
    if anti_link:
        if re.search(r"(https?://|discord\.gg/)", message.content):
            await message.delete()
            await message.channel.send(
                f"🚫 {message.author.mention} Links are not allowed!",
                delete_after=3
            )
            return

    # Anti-Badwords
    badwords = ["fuck", "bitch", "asshole"]
    if badwords_filter:
        if any(word in message.content.lower() for word in badwords):
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
        try:
            await message.author.timeout(datetime.timedelta(minutes=2))
            await message.channel.send(
                f"🚨 {message.author.mention} Spamming detected! Muted 2 min."
            )
            await send_log(message.guild, f"🚨 Spam muted: {message.author}")
        except:
            pass

        spam_users[user_id] = {"count": 0, "time": datetime.datetime.utcnow()}

    if diff > 5:
        spam_users[user_id] = {"count": 1, "time": datetime.datetime.utcnow()}

    await bot.process_commands(message)

# ----------------------------
# ANTI-NUKE SYSTEM
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
            await send_log(guild, f"🚨 Anti-Nuke banned: {user}")
        except:
            print("❌ Missing ban permissions")

@bot.event
async def on_guild_channel_delete(channel):
    await anti_nuke_action(channel.guild, discord.AuditLogAction.channel_delete)

@bot.event
async def on_guild_role_delete(role):
    await anti_nuke_action(role.guild, discord.AuditLogAction.role_delete)

# ----------------------------
# WELCOME SYSTEM
# ----------------------------
@bot.event
async def on_member_join(member):
    if auto_role_id:
        role = member.guild.get_role(auto_role_id)
        if role:
            await member.add_roles(role)

    await send_log(member.guild, f"👋 Welcome {member.mention} joined!")

# ----------------------------
# CUSTOM HELP MENU
# ----------------------------
help_pages = [
    {
        "title": "🛡 Moderation Commands",
        "description":
        "`!kick @user reason`\n"
        "`!ban @user reason`\n"
        "`!unban user_id`\n"
        "`!timeout @user 10m`\n"
        "`!purge 10`\n"
        "`!slowmode 5`\n"
        "`!lock / !unlock`\n"
    },
    {
        "title": "⚠ Warning + Strike System",
        "description":
        "`!warn @user reason`\n"
        "`!warns @user`\n"
        "`!clearwarns @user`\n\n"
        "`!strike @user reason`\n"
        "`!strikes @user`\n"
        "`!clearstrikes @user`\n"
        "⚡ 3 strikes = Auto Ban\n"
    },
    {
        "title": "🔒 Security Commands",
        "description":
        "✅ Anti-Spam Auto Timeout\n"
        "✅ Anti-Link Protection\n"
        "✅ Anti-Badwords Filter\n"
        "✅ Anti-Nuke Auto Ban\n"
    },
    {
        "title": "👑 Owner Commands",
        "description":
        "`!wl add/remove/list`\n"
        "`!maintenance on/off`\n"
        "`!setlog #channel`\n"
        "`!autorole @role`\n"
    },
    {
        "title": "ℹ Info Commands",
        "description":
        "`!ping`\n"
        "`!serverinfo`\n"
        "`!userinfo @user`\n"
        "`!avatar @user`\n"
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
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = (self.page - 1) % len(help_pages)
        await self.update(interaction.message)
        await interaction.response.defer()

    @discord.ui.button(label="Next ➡", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
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
    embed.set_footer(text="Page 1")
    await ctx.send(embed=embed, view=view)

# ----------------------------
# MODERATION COMMANDS
# ----------------------------
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    await member.kick(reason=reason)
    await ctx.send(f"✅ Kicked {member.mention}")
    await send_log(ctx.guild, f"👢 Kick: {member} | {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    await member.ban(reason=reason)
    await ctx.send(f"✅ Banned {member.mention}")
    await send_log(ctx.guild, f"⛔ Ban: {member} | {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"✅ Unbanned {user}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, time: str):
    unit = time[-1]
    amount = int(time[:-1])

    if unit == "m":
        duration = datetime.timedelta(minutes=amount)
    elif unit == "h":
        duration = datetime.timedelta(hours=amount)
    elif unit == "d":
        duration = datetime.timedelta(days=amount)
    else:
        return await ctx.send("❌ Example: 10m")

    await member.timeout(duration)
    await ctx.send(f"✅ Timed out {member.mention}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    await ctx.channel.purge(limit=amount)
    await ctx.send(f"✅ Deleted {amount} messages", delete_after=3)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"✅ Slowmode set {seconds}s")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Channel Locked")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Channel Unlocked")

# ----------------------------
# WARNINGS
# ----------------------------
@bot.command()
async def warn(ctx, member: discord.Member, *, reason="No reason"):
    warnings.setdefault(member.id, [])
    warnings[member.id].append(reason)
    await ctx.send(f"⚠ Warned {member.mention}")

@bot.command()
async def warns(ctx, member: discord.Member):
    user_warns = warnings.get(member.id, [])
    if not user_warns:
        return await ctx.send("✅ No warnings.")
    await ctx.send("\n".join(user_warns))

@bot.command()
async def clearwarns(ctx, member: discord.Member):
    warnings[member.id] = []
    await ctx.send("✅ Cleared warnings")

# ----------------------------
# STRIKES
# ----------------------------
@bot.command()
async def strike(ctx, member: discord.Member, *, reason="No reason"):
    strikes.setdefault(member.id, [])
    strikes[member.id].append(reason)

    count = len(strikes[member.id])
    await ctx.send(f"⚔ Strike {count}/3 for {member.mention}")

    if count >= 3:
        await member.ban(reason="3 Strikes reached")
        await ctx.send(f"⛔ Auto banned {member.mention}")

# ----------------------------
# WHITELIST OWNER ONLY
# ----------------------------
@bot.group()
@commands.is_owner()
async def wl(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send("Usage: !wl add/remove/list")

@wl.command()
async def add(ctx, member: discord.Member):
    whitelist.add(member.id)
    await ctx.send("✅ Added to whitelist")

@wl.command()
async def remove(ctx, member: discord.Member):
    whitelist.discard(member.id)
    await ctx.send("❌ Removed from whitelist")

@wl.command()
async def list(ctx):
    await ctx.send(str(whitelist))

# ----------------------------
# MAINTENANCE MODE
# ----------------------------
@bot.command()
@commands.is_owner()
async def maintenance(ctx, mode: str):
    global maintenance_mode
    maintenance_mode = mode.lower() == "on"
    await ctx.send(f"🛠 Maintenance: {maintenance_mode}")

# ----------------------------
# SET LOG CHANNEL + AUTO ROLE
# ----------------------------
@bot.command()
@commands.is_owner()
async def setlog(ctx, channel: discord.TextChannel):
    global log_channel_id
    log_channel_id = channel.id
    await ctx.send("✅ Log channel set")

@bot.command()
@commands.is_owner()
async def autorole(ctx, role: discord.Role):
    global auto_role_id
    auto_role_id = role.id
    await ctx.send("✅ AutoRole set")

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