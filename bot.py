import discord
from discord.ext import commands, tasks
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Event: Bot ready ---
@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")

# --- Simple placeholder command generator ---
def register_placeholder(cmd_name):
    @bot.command(name=cmd_name)
    async def _placeholder(ctx, *args):
        await ctx.send(f"✅ Command `{cmd_name}` executed with arguments: {args}")
    return _placeholder

# --- List of commands (all 80+ commands you wanted) ---
all_commands = [
    "nick", "me", "spoiler", "giphy", "tenor", "shrug", "tableflip", "unflip", "msg", "thread",
    "kick", "ban", "timeout", "warn", "warnings", "clear", "mute", "unmute", "softban",
    "lock", "unlock", "slowmode", "modlogs", "notes", "addnote", "case", "roleinfo",
    "serverinfo", "userinfo", "tempban", "play", "skip", "pause", "resume", "queue",
    "clear-queue", "stop", "loop", "shuffle", "volume", "nowplaying", "seek", "join",
    "leave", "lyrics", "8ball", "coinflip", "diceroll", "cat", "dog", "meme", "rps",
    "slots", "urbandictionary", "insult", "rank", "leaderboard", "giveaway", "poll",
    "avatar", "imagine", "blend", "describe", "ping", "help", "weather", "translate",
    "calc", "remindme", "search", "vote", "invite", "id", "clean", "uptime", "latency",
    "setprefix", "diagnose", "perms", "setnick", "application", "status", "afk", "profile",
    "reminder", "urban", "dictionary", "joke", "fact", "quote", "roll", "flip", "choose",
    "hug", "kiss", "pat", "slap", "highfive", "dance", "cry", "laugh", "smile", "angry", "think"
]

# --- Register all commands dynamically ---
for cmd in all_commands:
    register_placeholder(cmd)

# --- Working help command (single embed) ---
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="📜 Bot Commands",
        description="All commands are prefixed with `!`.",
        color=discord.Color.green()
    )
    commands_per_line = 6
    cmd_list = [f"`!{c}`" for c in all_commands]
    lines = [" • ".join(cmd_list[i:i+commands_per_line]) for i in range(0, len(cmd_list), commands_per_line)]
    embed.description = "\n".join(lines)
    await ctx.send(embed=embed)

# --- Setup example command ---
@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup_all(ctx):
    guild = ctx.guild
    categories = {
        "SERVER SPAWN": ["entrance", "overview", "server-boost"],
        "VOICE ZONE": ["General Vc", "Chill Vc", "Duo Vc", "Trio Vc", "SQuad Vc"],
        "TEXT ZONE": ["chill-chat", "gaming-chat", "toxic-chat"]
    }
    for cat_name, channels in categories.items():
        cat = discord.utils.get(guild.categories, name=cat_name)
        if not cat:
            cat = await guild.create_category(cat_name)
        for ch_name in channels:
            if "vc" in ch_name.lower():
                if not discord.utils.get(cat.voice_channels, name=ch_name):
                    await guild.create_voice_channel(ch_name, category=cat)
            else:
                if not discord.utils.get(cat.text_channels, name=ch_name):
                    await guild.create_text_channel(ch_name, category=cat)
    await ctx.send("✅ Server setup done!")

# --- Delete all command ---
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

# --- Greetchannel set ---
@bot.command(name="greetchannelset")
@commands.has_permissions(administrator=True)
async def greet_channel(ctx, channel: discord.TextChannel):
    bot.greet_channel = channel
    await ctx.send(f"✅ Welcome messages will be sent in {channel.mention}")

@bot.event
async def on_member_join(member):
    if hasattr(bot, "greet_channel"):
        await bot.greet_channel.send(f"👋 Welcome {member.mention} to {member.guild.name}!")

# --- Run the bot ---
bot.run(os.getenv("DISCORD_BOT_TOKEN"))