import discord
from discord.ext import commands, tasks
import datetime
import asyncio
import os
import re

# ----------------------------
# BOT SETUP
# ----------------------------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")  # Remove default help

OWNER_ID = None
log_channel_id = None
maintenance_mode = False
spam_users = {}
whitelist = set()
welcome_message = None
mod_role_id = None
auto_roles = []

badwords_filter = True
anti_link = True

# ----------------------------
# SERVER TEMPLATE SETUP DATA
# ----------------------------
TEMPLATE_CATEGORIES = [
    {"name": "SERVER SPAWN", "channels": ["・entrance", "・overview", "・server-boost"]},
    {"name": "GATEWAY", "channels": ["・self-role", "・updates", "・starboard"]},
    {"name": "IMPORTANT", "channels": ["・announces", "・giveaway", "・invite"]},
    {"name": "YOUTUBE ZONE", "channels": ["・yt-notification", "・suggestions"]},
    {"name": "CHILL ZONE", "channels": ["・chill-chat", "・gaming-chat", "・toxic-chat"]},
    {"name": "GAMING ZONE", "channels": ["・owo", "・aki", "・poki"]},
    {"name": "LEVEL ZONE", "channels": ["・level-up", "・level-chack"]},
    {"name": "EVENT ZONE", "channels": ["・event", "・event-announces"]},
    {"name": "VOICE ZONE", "channels": ["・General Vc", "・Chill Vc", "・Duo Vc", "・Trio Vc", "・SQuad Vc"]},
    {"name": "MUSIC ZONE", "channels": ["・music-chat", "・Music Vc"]},
    {"name": "APPLICATION", "channels": ["・report", "・staff-apply"]},
    {"name": "STAFF ZONE", "channels": ["・staff-chat", "・staff-announces"]}
]

TEMPLATE_ROLES = [
    {"name": "RUDRA ✦", "color": discord.Color.red(), "position": 100},
    {"name": "Creator", "color": discord.Color.dark_grey(), "position": 99},
    {"name": "ADMIN ✦", "color": discord.Color.blue(), "position": 98},
    {"name": "MOD ✦", "color": discord.Color.blue(), "position": 97},
    {"name": "TRIAL MOD ✦", "color": discord.Color.green(), "position": 96},
    {"name": "YOUTUBER ✦", "color": discord.Color.gold(), "position": 95},
    {"name": "Verified Girl ✦", "color": discord.Color.magenta(), "position": 94},
    # Add more roles as needed
]

# ----------------------------
# BOT READY
# ----------------------------
@bot.event
async def on_ready():
    global OWNER_ID
    OWNER_ID = (await bot.application_info()).owner.id
    print(f"✅ Moderation Bot Online as {bot.user}")
    print(f"👑 Owner ID: {OWNER_ID}")

# ----------------------------
# ANTI-SPAM + BADWORDS + ANTI-LINK
# ----------------------------
@bot.event
async def on_message(message):
    if message.author.bot or (maintenance_mode and message.author.id != OWNER_ID):
        return

    user_id = message.author.id

    # Badwords
    badwords = ["fuck","bitch","asshole"]
    if badwords_filter and any(word in message.content.lower() for word in badwords):
        await message.delete()
        until = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        await message.author.edit(timeout=until)
        await message.channel.send(f"🚨 {message.author.mention} Badword detected! Timeout 5 min.", delete_after=5)
        return

    # Anti-Link
    if anti_link and re.search(r"(https?://|discord\.gg/)", message.content):
        await message.delete()
        await message.channel.send(f"🚫 {message.author.mention} Links not allowed!", delete_after=5)
        return

    # Anti-Spam
    if user_id not in spam_users:
        spam_users[user_id] = {"count": 1, "time": datetime.datetime.utcnow()}
    else:
        spam_users[user_id]["count"] += 1
        diff = (datetime.datetime.utcnow() - spam_users[user_id]["time"]).seconds
        if diff <= 5 and spam_users[user_id]["count"] >= 6:
            until = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
            await message.author.edit(timeout=until)
            await message.channel.send(f"🚨 {message.author.mention} Spam detected! Timeout 5 min.", delete_after=5)
            spam_users[user_id] = {"count": 0, "time": datetime.datetime.utcnow()}
        if diff > 5:
            spam_users[user_id] = {"count": 1, "time": datetime.datetime.utcnow()}

    await bot.process_commands(message)

# ----------------------------
# HELP MENU (OLD STYLE)
# ----------------------------
class HelpMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.pages = [
            "> Use `!help <command>` for details\n\n"
            "> !help\n!info\n!list\n!avatarinfo\n!bannerinfo\n!guildbannerinfo\n!guildiconinfo\n!guildmembercount\n!guildsplashinfo\n!stickerpackinfo\n!userinfo\n!casedelete\n!caseinfo\n!caselist\n!casesplit",
            "> Use `!help <command>` for details\n\n"
            "> !caseupdate\n!caseclose\n!mute\n!namewarn\n!purge\n!setslowmode\n!unmute\n!unwarn\n!warn\n!warns"
        ]
        self.page = 0

    async def update(self, interaction):
        embed = discord.Embed(
            title="Moderation Bot Help Menu",
            description=self.pages[self.page],
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Page {self.page+1}/{len(self.pages)}")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Previous Page", style=discord.ButtonStyle.primary)
    async def previous(self, interaction, button):
        self.page = (self.page - 1) % len(self.pages)
        await self.update(interaction)

    @discord.ui.button(label="Next Page", style=discord.ButtonStyle.primary)
    async def next(self, interaction, button):
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
# !SETUP ALL COMMAND
# ----------------------------
@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup(ctx, option: str):
    if option.lower() != "all":
        return await ctx.send("Usage: `!setup all`")

    # Create Roles
    for role_data in TEMPLATE_ROLES:
        existing = discord.utils.get(ctx.guild.roles, name=role_data["name"])
        if not existing:
            await ctx.guild.create_role(
                name=role_data["name"],
                color=role_data["color"],
                reason="Setup template"
            )
    await ctx.send("✅ Roles created")

    # Create Categories & Channels
    for category in TEMPLATE_CATEGORIES:
        existing_cat = discord.utils.get(ctx.guild.categories, name=category["name"])
        if not existing_cat:
            cat = await ctx.guild.create_category(category["name"])
        else:
            cat = existing_cat

        for ch_name in category["channels"]:
            existing_channel = discord.utils.get(ctx.guild.channels, name=ch_name)
            if not existing_channel:
                await ctx.guild.create_text_channel(ch_name, category=cat)
    await ctx.send("✅ Categories & Channels created")

# ----------------------------
# !GREETSET COMMAND
# ----------------------------
@bot.command(name="greetset")
@commands.has_permissions(administrator=True)
async def greetset(ctx, *, message=None):
    global welcome_message
    if message is None:
        return await ctx.send("Usage: `!greetset <message>`")
    welcome_message = message
    await ctx.send(f"✅ Welcome message set to:\n{message}")

@bot.event
async def on_member_join(member):
    if welcome_message:
        channel = member.guild.system_channel or discord.utils.get(member.guild.text_channels, name="・entrance")
        if channel:
            await channel.send(f"{member.mention} {welcome_message}")

# ----------------------------
# RUN BOT
# ----------------------------
bot.run(os.getenv("DISCORD_BOT_TOKEN"))