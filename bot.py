import discord
from discord.ext import commands
import os
import json
import datetime
import asyncio

# ----------------------------
# BOT SETUP
# ----------------------------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")  # Remove default help

OWNER_ID = None
log_channel_id = None
whitelist = set()
maintenance_mode = False
spam_users = {}

# JSON files for storing server data
if not os.path.exists("server_data.json"):
    with open("server_data.json", "w") as f:
        json.dump({}, f)

with open("server_data.json", "r") as f:
    server_data = json.load(f)

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
# HELP MENU
# ----------------------------
class HelpMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.pages = [
            "> Use `!help <command>` for info\n\n"
            "> `!help`\n"
            "> `!info`\n"
            "> `!setupall`\n"
            "> `!deleteall`\n"
            "> `!greetchannelset`\n"
            "> `!greetset`\n"
            "> `!kick`\n"
            "> `!ban`\n"
            "> `!mute`\n"
            "> `!unmute`\n"
            "> `!timeout`\n"
            "> `!warn`\n"
            "> `!infractions`\n"
            "> `!purge`\n"
            "> `!clear`\n"
            "> `!slowmode`\n"
            "> `!lock`\n"
            "> `!unlock`\n"
            "> `!nuke`\n"
            "> `!setlog`\n"
            "> `!modrole`\n"
            "> `!autorole`\n"
            "> `!addrole`\n"
            "> `!removerole`\n"
            "> `!tempban`\n"
            "> `!tempmute`\n"
            "> `!reason`\n"
            "> `!cases`\n"
            "> `!warn-limit`\n"
            "> `!softban`\n"
            "> `!massban`\n"
            "> `!role-info`\n"
            "> `!user-info`\n"
            "> `!server-info`\n"
            "> `!whois`\n"
            "> `!pardon`\n"
            "> `!warn-clear`"
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
# SERVER DATA HELPER
# ----------------------------
def save_server_data():
    with open("server_data.json", "w") as f:
        json.dump(server_data, f, indent=4)

# ----------------------------
# WELCOME MESSAGE HANDLER
# ----------------------------
@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    if guild_id in server_data:
        greet_channel_id = server_data[guild_id].get("welcome_channel")
        greet_message = server_data[guild_id].get("welcome_message")
        if greet_channel_id and greet_message:
            channel = member.guild.get_channel(greet_channel_id)
            if channel:
                await channel.send(greet_message.replace("{user}", member.mention))

@bot.command()
async def greetchannelset(ctx, channel: discord.TextChannel):
    guild_id = str(ctx.guild.id)
    if guild_id not in server_data:
        server_data[guild_id] = {}
    server_data[guild_id]["welcome_channel"] = channel.id
    save_server_data()
    await ctx.send(f"✅ Welcome channel set to {channel.mention}")

@bot.command()
async def greetset(ctx, *, message):
    guild_id = str(ctx.guild.id)
    if guild_id not in server_data:
        server_data[guild_id] = {}
    server_data[guild_id]["welcome_message"] = message
    save_server_data()
    await ctx.send("✅ Welcome message updated!")

# ----------------------------
# SETUP ALL COMMAND
# ----------------------------
@bot.command()
async def setupall(ctx):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Only the owner can use this command!")

    categories = {
        "SERVER SPAWN": ["entrance", "overview", "server-boost"],
        "GATEWAY": ["self-role", "updates", "starboard"],
        "IMPORTANT": ["announces", "giveaway", "invite"],
        "YOUTUBE ZONE": ["yt-notification", "suggestions"],
        "CHILL ZONE": ["chill-chat", "gaming-chat", "toxic-chat"],
        "GAMING ZONE": ["owo", "aki", "poki"],
        "LEVEL ZONE": ["level-up", "level-chack"],
        "EVENT ZONE": ["event", "event-announces"],
        "VOICE ZONE": ["General Vc", "Chill Vc", "Duo Vc", "Trio Vc", "SQuad Vc"],
        "MUSIC ZONE": ["music-chat", "Music Vc"],
        "APPLICATION": ["report", "staff-apply"],
        "STAFF ZONE": ["staff-chat", "staff-announces"]
    }

    # Create categories and channels
    for cat_name, channels in categories.items():
        cat = discord.utils.get(ctx.guild.categories, name=cat_name)
        if not cat:
            cat = await ctx.guild.create_category(cat_name)
        for ch_name in channels:
            # Check if voice or text
            if "Vc" in ch_name or "vc" in ch_name or "Voice" in cat_name:
                if not discord.utils.get(ctx.guild.voice_channels, name=ch_name):
                    await ctx.guild.create_voice_channel(ch_name, category=cat)
            else:
                if not discord.utils.get(ctx.guild.text_channels, name=ch_name):
                    await ctx.guild.create_text_channel(ch_name, category=cat)
    await ctx.send("✅ Setup completed! All categories and channels created.")

# ----------------------------
# DELETE ALL
# ----------------------------
@bot.command()
async def deleteall(ctx):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ Only the owner can use this command!")
    for ch in ctx.guild.channels:
        try:
            await ch.delete()
        except:
            continue
    for role in ctx.guild.roles:
        if role != ctx.guild.default_role:
            try:
                await role.delete()
            except:
                continue
    await ctx.send("✅ Deleted all channels and roles!")

# ----------------------------
# ADD YOUR MODERATION COMMANDS HERE
# Example kick/ban
# ----------------------------
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    await member.kick(reason=reason)
    await ctx.send(f"✅ Kicked {member.mention} | Reason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    await member.ban(reason=reason)
    await ctx.send(f"✅ Banned {member.mention} | Reason: {reason}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member):
    await member.edit(mute=True)
    await ctx.send(f"✅ {member.mention} has been muted")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    await member.edit(mute=False)
    await ctx.send(f"✅ {member.mention} has been unmuted")

# ----------------------------
# RUN BOT
# ----------------------------
bot.run(os.getenv("DISCORD_BOT_TOKEN"))