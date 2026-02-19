import discord
from discord.ext import commands
import os
import time

# ---------------- BOT SETUP ----------------

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ---------------- AFK SYSTEM STORAGE ----------------

afk_users = {}

# ---------------- BOT READY ----------------

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# ---------------- AFK COMMAND ----------------

@bot.command()
async def afk(ctx, action=None, *, reason="AFK"):
    if action != "set":
        return await ctx.send("❌ Use: `!afk set <reason>`")

    afk_users[ctx.author.id] = {
        "reason": reason,
        "time": int(time.time())
    }

    embed = discord.Embed(
        description=f"<:xieron_tick:1396339883131273407> You are now **AFK**: *{reason}*\n\n"
                    f"AFK since: <t:{int(time.time())}:R>",
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed)

# ---------------- REMOVE AFK ON MESSAGE ----------------

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(
            f"✅ Welcome back {message.author.mention}, your AFK has been removed!"
        )

    await bot.process_commands(message)

# ---------------- DELALL SERVER WIPE COMMAND ----------------

@bot.command()
@commands.has_permissions(administrator=True)
async def delall(ctx):
    embed = discord.Embed(
        title="⚠️ SERVER WIPE STARTED",
        description="Deleting all channels, categories and roles...",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

    guild = ctx.guild

    # DELETE CHANNELS + CATEGORIES
    for channel in guild.channels:
        try:
            await channel.delete()
        except:
            pass

    # DELETE ROLES (except @everyone and bot role)
    for role in guild.roles:
        if role.name != "@everyone" and role != guild.me.top_role:
            try:
                await role.delete()
            except:
                pass

    print("✅ Server wiped successfully")

# ---------------- BASIC MOD COMMANDS ----------------

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
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"✅ Cleared {amount} messages!", delete_after=3)

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int):
    duration = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
    await member.timeout(duration)
    await ctx.send(f"⏳ Timed out {member.mention} for {minutes} minutes!")

# ---------------- HELP COMMAND ----------------

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📜 Moderation Bot Commands",
        description="Here are all available commands:",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🛠 Moderation",
        value="""
`!kick <user> <reason>`
`!ban <user> <reason>`
`!timeout <user> <minutes>`
`!clear <amount>`
""",
        inline=False
    )

    embed.add_field(
        name="💤 AFK System",
        value="""
`!afk set <reason>`
(Removes AFK automatically when you chat)
""",
        inline=False
    )

    embed.add_field(
        name="⚠️ Dangerous Admin",
        value="""
`!delall` → Deletes all channels + roles
(Admin only)
""",
        inline=False
    )

    embed.set_footer(text="Moderation Bot | Working Help Menu ✅")
    await ctx.send(embed=embed)

# ---------------- RUN BOT ----------------

bot.run(os.getenv("DISCORD_TOKEN"))