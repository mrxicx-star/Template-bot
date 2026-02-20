import discord
from discord.ext import commands
import asyncio
import aiosqlite
import random
import datetime
import aiohttp
from secrets import TOKEN, PEXELS_KEY

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

# ================= DATABASE =================

@bot.event
async def on_ready():
    print(f"EOF Moderate Bot Online as {bot.user}")
    async with aiosqlite.connect("database.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS warns(user_id INTEGER, guild_id INTEGER, reason TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS afk(user_id INTEGER, reason TEXT)")
        await db.commit()

# ================= AUTOMOD =================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    banned_words = ["badword1", "badword2"]

    for word in banned_words:
        if word in message.content.lower():
            await message.delete()
            await message.channel.send("🚫 Inappropriate language detected.")
            return

    await bot.process_commands(message)

# ================= MODERATION =================

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned {member} | {reason}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 Kicked {member}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount+1)
    await ctx.send(f"🗑 Deleted {amount} messages", delete_after=3)

@bot.command()
async def warn(ctx, member: discord.Member, *, reason="No reason"):
    async with aiosqlite.connect("database.db") as db:
        await db.execute("INSERT INTO warns VALUES (?, ?, ?)", (member.id, ctx.guild.id, reason))
        await db.commit()
    await ctx.send(f"⚠ Warned {member} | {reason}")

@bot.command()
async def warnings(ctx, member: discord.Member):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT reason FROM warns WHERE user_id=? AND guild_id=?", (member.id, ctx.guild.id)) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        return await ctx.send("No warnings found.")

    msg = "\n".join([r[0] for r in rows])
    await ctx.send(f"Warnings for {member}:\n{msg}")

# ================= AFK SYSTEM =================

@bot.command()
async def afk(ctx, *, reason="AFK"):
    async with aiosqlite.connect("database.db") as db:
        await db.execute("INSERT INTO afk VALUES (?, ?)", (ctx.author.id, reason))
        await db.commit()

    await ctx.send(f"💤 {ctx.author.mention} is now AFK: {reason}")

# ================= UTILITY =================

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author

    embed = discord.Embed(title="👤 User Info", color=discord.Color.blurple())
    embed.add_field(name="Username", value=member.name)
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined", value=member.joined_at)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.timestamp = datetime.datetime.utcnow()

    await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    embed = discord.Embed(title="🌍 Server Info", color=discord.Color.green())
    embed.add_field(name="Name", value=ctx.guild.name)
    embed.add_field(name="Members", value=ctx.guild.member_count)
    embed.add_field(name="Owner", value=ctx.guild.owner)
    embed.timestamp = datetime.datetime.utcnow()
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 {round(bot.latency * 1000)}ms")

# ================= FUN =================

@bot.command()
async def coinflip(ctx):
    await ctx.send(random.choice(["Heads", "Tails"]))

@bot.command()
async def dice(ctx):
    await ctx.send(f"🎲 {random.randint(1,6)}")

@bot.command()
async def meme(ctx):
    url = "https://api.pexels.com/v1/search?query=funny&per_page=20"
    headers = {"Authorization": PEXELS_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()

    if not data.get("photos"):
        return await ctx.send("No memes found.")

    photo = random.choice(data["photos"])
    image_url = photo["src"]["large"]

    embed = discord.Embed(title="😂 Random Meme", color=discord.Color.orange())
    embed.set_image(url=image_url)
    embed.set_footer(text=f"Requested by {ctx.author}")
    embed.timestamp = datetime.datetime.utcnow()

    await ctx.send(embed=embed)

# ================= TICKET SYSTEM =================

@bot.command()
async def ticket(ctx):
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True)
    }

    channel = await ctx.guild.create_text_channel(
        f"ticket-{ctx.author.name}",
        overwrites=overwrites
    )

    await channel.send("🎫 Support will be with you shortly.")

# ================= GIVEAWAY =================

@bot.command()
async def giveaway(ctx, time: int, *, prize):
    msg = await ctx.send(f"🎉 Giveaway: {prize}\nReact with 🎉")
    await msg.add_reaction("🎉")

    await asyncio.sleep(time)

    newmsg = await ctx.channel.fetch_message(msg.id)
    users = [user async for user in newmsg.reactions[0].users() if not user.bot]

    if not users:
        return await ctx.send("No valid participants.")

    winner = random.choice(users)
    await ctx.send(f"🏆 Winner: {winner.mention}")

# ================= HELP =================

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🛡️ EOF Moderate Bot",
        description="Advanced Moderation & Utility System\nPrefix: `!`",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🔨 Moderation",
        value="`ban` `kick` `clear` `warn` `warnings`",
        inline=False
    )

    embed.add_field(
        name="⚙ Utility",
        value="`userinfo` `serverinfo` `ping` `afk`",
        inline=False
    )

    embed.add_field(
        name="🎉 Fun",
        value="`coinflip` `dice` `meme`",
        inline=False
    )

    embed.add_field(
        name="🎫 Systems",
        value="`ticket` `giveaway` `automod`",
        inline=False
    )

    embed.set_footer(text=f"Requested by {ctx.author}")
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.timestamp = datetime.datetime.utcnow()

    await ctx.send(embed=embed)

# ================= RUN =================

bot.run(TOKEN)