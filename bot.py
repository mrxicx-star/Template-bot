import discord
from discord.ext import commands
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------- HELPER --------------------
def get_all_commands():
    """Returns a sorted list of all bot commands"""
    return sorted([cmd.name for cmd in bot.commands])

# -------------------- DYNAMIC HELP --------------------
@bot.command()
async def help(ctx):
    commands_list = get_all_commands()
    embed = discord.Embed(title="📜 Help - All Commands", color=discord.Color.blue())
    # Join all commands in a single string with commas
    embed.description = ", ".join(f"`{cmd}`" for cmd in commands_list)
    embed.set_footer(text=f"Total Commands: {len(commands_list)}")
    await ctx.send(embed=embed)

# -------------------- PLACEHOLDER COMMANDS --------------------
# Add your real command implementations below; placeholders for demonstration
@bot.command()
async def setup(ctx):
    await ctx.send("✅ Setup command works!")

@bot.command()
async def delall(ctx):
    await ctx.send("✅ Delall command works!")

# Example moderation commands
@bot.command()
async def kick(ctx, member: discord.Member):
    await ctx.send(f"✅ Kick placeholder works for {member}")

@bot.command()
async def ban(ctx, member: discord.Member):
    await ctx.send(f"✅ Ban placeholder works for {member}")

# -------------------- ADDITIONAL PLACEHOLDER COMMANDS --------------------
# List all your remaining 80+ commands here as placeholders
placeholder_cmds = [
    "nick","me","spoiler","giphy","tenor","shrug","tableflip","unflip","msg","thread",
    "timeout","warn","warnings","clear","mute","unmute","softban","lock","unlock",
    "slowmode","modlogs","notes","addnote","case","roleinfo","serverinfo","userinfo",
    "tempban","play","skip","pause","resume","queue","clear-queue","stop","loop",
    "shuffle","volume","nowplaying","seek","join","leave","lyrics","8ball","coinflip",
    "diceroll","cat","dog","meme","rps","slots","urbandictionary","insult","rank",
    "leaderboard","giveaway","poll","avatar","imagine","blend","describe","ping",
    "weather","translate","calc","remindme","search","vote","invite","id","clean",
    "uptime","latency","setprefix","diagnose","perms","setnick","application","status",
    "afk","profile","reminder","urban","dictionary","joke","fact","quote","roll","flip",
    "choose","hug","kiss","pat","slap","highfive","dance","cry","laugh","smile","angry",
    "think","greetchannelset"
]

for cmd_name in placeholder_cmds:
    @bot.command(name=cmd_name)
    async def placeholder(ctx):
        await ctx.send(f"✅ `{ctx.invoked_with}` command works!")

# -------------------- RUN BOT --------------------
bot.run(os.environ["DISCORD_BOT_TOKEN"])