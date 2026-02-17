import discord
from discord.ext import commands, tasks
import os
import random

# Intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ---- Events ----
@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")

# ---- HELP COMMAND ----
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="🛠️ Moderation Bot Commands",
        description="Here is the full command list. Use `!command` to run them.",
        color=discord.Color.blue()
    )

    commands_dict = {
        "Moderation": [
            "!kick", "!ban", "!timeout", "!warn", "!warnings", "!clear", "!mute", "!unmute",
            "!softban", "!lock", "!unlock", "!slowmode", "!modlogs", "!notes", "!addnote",
            "!case", "!roleinfo", "!serverinfo", "!userinfo", "!tempban", "!pardon", "!warn-clear"
        ],
        "Fun & Social": [
            "!8ball", "!coinflip", "!diceroll", "!cat", "!dog", "!meme", "!rps", "!slots",
            "!urbandictionary", "!insult", "!rank", "!leaderboard", "!poll", "!avatar",
            "!hug", "!kiss", "!pat", "!slap", "!highfive", "!dance", "!cry", "!laugh", "!smile", "!angry", "!think"
        ],
        "Music": [
            "!play", "!skip", "!pause", "!resume", "!queue", "!clear-queue", "!stop", "!loop",
            "!shuffle", "!volume", "!nowplaying", "!seek", "!join", "!leave", "!lyrics"
        ],
        "Utility / AI": [
            "!nick", "!me", "!spoiler", "!giphy", "!tenor", "!shrug", "!tableflip", "!unflip",
            "!msg", "!thread", "!imagine", "!blend", "!describe", "!ping", "!help", "!weather",
            "!translate", "!calc", "!remindme", "!search", "!vote", "!invite", "!id", "!clean",
            "!uptime", "!latency", "!setprefix", "!diagnose", "!perms", "!setnick", "!application",
            "!status", "!afk", "!profile", "!reminder", "!urban", "!dictionary", "!joke", "!fact",
            "!quote", "!roll", "!flip", "!choose"
        ],
        "Server Setup": [
            "!setup all", "!greetset", "!del", "!greetchannelset", "!autorole", "!addrole", "!removerole",
            "!modrole", "!setlog"
        ]
    }

    for category, cmds in commands_dict.items():
        embed.add_field(
            name=f"📌 {category} Commands",
            value=" • ".join(cmds),
            inline=False
        )

    embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    await ctx.send(embed=embed)

# ---- SETUP COMMAND ----
@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup_all(ctx):
    guild = ctx.guild

    # Example: create categories and channels
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

    for category_name, channels in categories.items():
        cat = discord.utils.get(guild.categories, name=category_name)
        if not cat:
            cat = await guild.create_category(category_name)
        for channel_name in channels:
            if "vc" in channel_name.lower():
                if not discord.utils.get(cat.voice_channels, name=channel_name):
                    await guild.create_voice_channel(channel_name, category=cat)
            else:
                if not discord.utils.get(cat.text_channels, name=channel_name):
                    await guild.create_text_channel(channel_name, category=cat)

    await ctx.send("✅ Server setup completed!")

# ---- DELETE ALL COMMAND ----
@bot.command(name="del")
@commands.has_permissions(administrator=True)
async def delete_all(ctx):
    guild = ctx.guild
    for channel in guild.channels:
        try:
            await channel.delete()
        except:
            pass
    for role in guild.roles:
        try:
            if role != guild.default_role:
                await role.delete()
        except:
            pass
    await ctx.send("✅ All channels and roles deleted!")

# ---- GREET CHANNEL SET ----
@bot.command(name="greetchannelset")
@commands.has_permissions(administrator=True)
async def greet_channel(ctx, channel: discord.TextChannel):
    # Store the channel in memory for demo purposes
    bot.greet_channel = channel
    await ctx.send(f"✅ Welcome messages will be sent in {channel.mention}")

# ---- Example Welcome Event ----
@bot.event
async def on_member_join(member):
    if hasattr(bot, "greet_channel"):
        channel = bot.greet_channel
        await channel.send(f"👋 Welcome {member.mention} to {member.guild.name}!")

# ---- PLACEHOLDER FOR OTHER COMMANDS ----
# You need to implement your 80+ other commands following your old logic
# e.g., !kick, !ban, !mute, !unmute, !warn, !tempban, !addrole, !removerole, etc.

# ---- RUN BOT ----
bot.run(os.getenv("DISCORD_BOT_TOKEN"))