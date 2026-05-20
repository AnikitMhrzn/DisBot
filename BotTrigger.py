import os
import random
import time
from pathlib import Path
from threading import Thread
from dotenv import load_dotenv
from flask import Flask
import discord
from discord.ext import commands, tasks
from datetime import timedelta

# ==========================================
# 1. BACKGROUND FLASK WEB SERVER FOR RENDER
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "LOL BOT is Online!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

keep_alive()

# ==========================================
# 2. AUTOMATIC PATH RESOLUTION FOR .ENV
# ==========================================
base_dir = Path(__file__).resolve().parent
env_path = base_dir / '.env'
load_dotenv(dotenv_path=env_path)
TOKEN = os.getenv('DISCORD_TOKEN')

if TOKEN is None:
    print("❌ ERROR: Unable to read 'DISCORD_TOKEN' from environment.")
    exit()

# ==========================================
# 3. INTENTS & BOT SETUP
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True  # Needed for game activity tracking

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ==========================================
# 4. IN-MEMORY CACHE STORAGE
# ==========================================
vc_join_times = {}       # {user_id: timestamp when they joined VC}
vc_total_times = {}      # {user_id: total seconds spent in VC}
last_game = {}           # {user_id: {"name": "Game Name", "time": timestamp}}

def format_duration(seconds):
    td = timedelta(seconds=int(seconds))
    hours, remainder = divmod(td.seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if td.days > 0:
        return f"{td.days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

# ==========================================
# 5. ROTATING STATUS LOOP
# ==========================================
@tasks.loop(seconds=20)
async def change_status():
    statuses = [
        discord.Game(name="!help | Having fun 🎉"),
        discord.Activity(type=discord.ActivityType.watching, name="over the chat channels"),
        discord.Game(name="Testing random IQs 🧠")
    ]
    await bot.change_presence(activity=random.choice(statuses))

@bot.event
async def on_ready():
    print(f'Success! Bot is online as {bot.user.name}')
    if not change_status.is_running():
        change_status.start()

    # Cache any members already in VC when bot starts
    for guild in bot.guilds:
        for vc in guild.voice_channels:
            for member in vc.members:
                if not member.bot:
                    vc_join_times[member.id] = time.time()

# ==========================================
# 6. ERROR HANDLER
# ==========================================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Slow down! You can use this command again in **{error.retry_after:.1f}** seconds.", delete_after=5)
    elif isinstance(error, commands.BadArgument) or isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing inputs! Look closely at `!help` for correct command usage.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("🔒 You do not possess the required moderation permissions to use this feature.")
    else:
        print(f"Ignored runtime exception tracker logs: {error}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if 'hi' in message.content.lower() or 'hello' in message.content.lower():
        await message.channel.send(f'Hey there, {message.author.mention}! 👋')
    await bot.process_commands(message)

# ==========================================
# 7. VC TRACKING EVENTS
# ==========================================
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    # Member joined a VC
    if before.channel is None and after.channel is not None:
        vc_join_times[member.id] = time.time()

    # Member left a VC
    elif before.channel is not None and after.channel is None:
        if member.id in vc_join_times:
            elapsed = time.time() - vc_join_times.pop(member.id)
            vc_total_times[member.id] = vc_total_times.get(member.id, 0) + elapsed

    # Member switched channels — keep tracking
    elif before.channel is not None and after.channel is not None:
        if member.id not in vc_join_times:
            vc_join_times[member.id] = time.time()

# ==========================================
# 8. GAME ACTIVITY TRACKING
# ==========================================
@bot.event
async def on_presence_update(before, after):
    if after.bot:
        return

    before_game = next((a for a in before.activities if isinstance(a, discord.Game)), None)
    after_game = next((a for a in after.activities if isinstance(a, discord.Game)), None)

    # They just started playing something
    if after_game and after_game != before_game:
        last_game[after.id] = {
            "name": after_game.name,
            "time": time.time()
        }
    # They stopped playing — keep the last game stored but mark end time
    elif before_game and not after_game:
        if after.id in last_game:
            last_game[after.id]["ended"] = time.time()

# ==========================================
# 9. CUSTOM HELP COMMAND
# ==========================================
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🎉 LOL BOT Entertainment Hub",
        description="Here is your updated list of all active fun commands:",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="🎭 Interactive Fun Modules",
        value="`!roast [@user]` - Drops a funny burn with a GIF\n`!slap [@user]` - Playfully slaps someone\n`!dadjoke` - Tells a terrible dad joke\n`!yomama [@user]` - Drops a classic mom joke burn",
        inline=False
    )
    embed.add_field(
        name="🔮 Scanners & Fortune Games",
        value="`!iqtest [@user]` - Scans and reveals their IQ\n`!whoisgay` - Calls out a random server member\n`!gayrate [@user]` - Rates your target's percentage",
        inline=False
    )
    embed.add_field(
        name="🎲 Simple Guessing Games",
        value="`!coinflip [heads/tails]` - Guess a coin toss\n`!dice [1-6]` - Guess a dice roll",
        inline=False
    )
    embed.add_field(
        name="📊 Activity Tracker",
        value="`!vctime [@user]` - See how long someone has been in VC\n`!topsession` - VC time leaderboard\n`!lastgame [@user]` - See the last game someone played",
        inline=False
    )
    embed.add_field(
        name="👤 Profile & Utilities",
        value="`!avatar [@user]` - View high-res avatar\n`!userinfo [@user]` - Displays account details\n`!clear [number]` - Purges chat messages (Staff Only)",
        inline=False
    )
    embed.set_footer(text="Anti-Spam active: All commands carry a standard 2-second cooldown.")
    await ctx.send(embed=embed)

# ==========================================
# 10. FUN COMMANDS
# ==========================================

@bot.command()
@commands.cooldown(1, 2, commands.BucketType.user)
async def roast(ctx, member: discord.Member = None):
    target = member or ctx.author
    roasts = [
        f"Hey {target.mention}, I'd agree with you, but then we'd both be completely wrong. 💀",
        f"{target.mention} is the reason the shampoo bottle has instructions written on it. 🧴",
        f"You bring so much joy to this server, {target.mention}... every time you log off. 👋",
        f"If I wanted to kill myself, I'd climb up {target.mention}'s ego and jump down to their actual IQ. 📉",
        f"{target.mention}, light travels faster than sound. That's why you seemed bright until you opened your mouth. ☀️",
        f"I can explain it to you, {target.mention}, but I can't understand it for you. 🧠",
        f"{target.mention}, you're not stupid, you just have bad luck thinking. 🍀",
        f"If brains were dynamite, {target.mention} couldn't blow their nose. 💥",
        f"{target.mention} is proof that even evolution makes mistakes sometimes. 🦖",
        f"Somewhere out there, {target.mention}, a tree is working very hard producing oxygen for you. Go apologize to it. 🌳"
    ]
    burn_gif = "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExb2cwNHQzc2Z1dmV6Y2p0cHh3bXB1YjJlZnExamJ2OGwzY2hnOXMwbSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/11hVniWaqh17Q4/giphy.gif"
    embed = discord.Embed(description=random.choice(roasts), color=discord.Color.orange())
    embed.set_image(url=burn_gif)
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 2, commands.BucketType.user)
async def slap(ctx, member: discord.Member):
    if member == ctx.author:
        await ctx.send("❌ Why are you hitting yourself? Slap someone else!")
        return
    items = [
        "a wet, slippery trout 🐟",
        "a giant fuzzy slipper 🥿",
        "a keyboard from 1995 ⌨️",
        "a squeaky rubber chicken 🐔",
        "a giant cluster of bananas 🍌"
    ]
    slap_gifs = [
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExd2E2Nml0YnNmbjczb2JidmJ0Ymg0cjd2aHBmdW5wbms2Z3BybDhxYyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/jauNHUg3yB9ZmDtzOv/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExd2E2Nml0YnNmbjczb2JidmJ0Ymg0cjd2aHBmdW5wbms2Z3BybDhxYyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/pfGBhQSaYAO5y/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3eXc0aG1kZHd6ajRtdmR6OTZidjU3dGJucHhsZXkzZXF1NW5xanFveCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/q570XlaWquRdf1DAQ1/giphy.gif"
    ]
    embed = discord.Embed(
        description=f"🎬 {ctx.author.mention} winds up and slaps {member.mention} right across the face with **{random.choice(items)}**! OUCH! 💥",
        color=discord.Color.red()
    )
    embed.set_image(url=random.choice(slap_gifs))
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 2, commands.BucketType.user)
async def dadjoke(ctx):
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything! ⚛️",
        "What do you call a factory that makes okay products? A satisfactory! 🏭",
        "Why did the scarecrow win an award? Because he was outstanding in his field! 🌾",
        "How do you make a tissue dance? You put a little boogie in it! 💃",
        "What did the ocean say to the beach? Nothing, it just waved! 🌊",
        "I'm reading a book on anti-gravity. I just can't put it down! 📕",
        "What do you call a fake noodle? An impasta! 🍝",
        "Why do melons have weddings? Because they cantaloupe! 🍈",
        "What do you call a belt made out of watches? A waist of time! ⏳",
        "How does a penguin build its house? Igloos it together! 🐧",
        "Why did the gym close down? It just wasn't working out! 🏋️",
        "What do you call a sleeping dinosaur? A dino-snore! 🦖",
        "Why did the math book look so sad? Because it had too many problems! 📐",
        "How do celebrities stay cool? They have a lot of fans! 💨",
        "Did you hear about the guy who invented the knock-knock joke? He won the no-bell prize! 🔔"
    ]
    dad_gifs = [
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExN3p4a2MyeWdwOGsxdW4zanlmaHM3N2VvNTl5ZnAzdWk4emlwdmcwciZlcD12MV9naWZzX3NlYXJjaCZjdD1n/3i7zenReaUuI0/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExN3p4a2MyeWdwOGsxdW4zanlmaHM3N2VvNTl5ZnAzdWk4emlwdmcwciZlcD12MV9naWZzX3NlYXJjaCZjdD1n/wWue0rCDOphOE/giphy.gif"
    ]
    embed = discord.Embed(title="👨 Dad Joke of the Day", description=f"*{random.choice(jokes)}*", color=discord.Color.blue())
    embed.set_image(url=random.choice(dad_gifs))
    await ctx.send(embed=embed)

@bot.command(name="yomama")
@commands.cooldown(1, 2, commands.BucketType.user)
async def yomama(ctx, member: discord.Member = None):
    target = member or ctx.author
    jokes = [
        "Yo mama's so fat, when she fell she made the Grand Canyon! 🏔️",
        "Yo mama's so old, her birth certificate says 'Expired' on it! 📜",
        "Yo mama's so poor, the ducks throw bread crumbs at her! 🦆",
        "Yo mama's so stupid, she stared at a juice carton for 2 hours because it said 'concentrate'! 🍊",
        "Yo mama's so ugly, when she looks in the mirror, the reflection ducks! 🪞",
        "Yo mama's so fat, she went to the cinema and sat next to everyone! 🎬",
        "Yo mama's so poor, she waves a popsicle around and calls it air conditioning! 🧊",
        "Yo mama's so stupid, she tried to drop-kick a wireless network! 📶",
        "Yo mama's so ugly, her portraits hang themselves! 🖼️",
        "Yo mama's so stupid, she threw a rock at the ground and missed! 🪨",
        "Yo mama's so ugly, when she joined an ugly contest they said 'No professionals allowed!'! 🏆",
        "Yo mama's so ugly, when she walks into a haunted house, she walks out with a job application! 👻"
    ]
    reaction_gifs = [
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExYWRrbG1qbjI5YWVkcG1tNnQ5M21mYnV5NGZ3aWNlNHJtbms5ZTVvNiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/1d7F9xyq6j7C1ojbC5/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3cWYzd3poY2dycGk2NnA1b3V5eW56N2tlYWViZm0xMWw4M2tpNjgybiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/xSM46ernAUN3y/giphy.gif",
        "https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3MGE3NjZ2bm1iYWJjcmlrcHgxcm5sMDRxOWo2NHI2b3dxYXBva2lhNCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/cM2CN5U99VVWdDGcSA/giphy.gif"
    ]
    prefix = f"Hey {target.mention}, " if member else ""
    embed = discord.Embed(title="💥 Yo Mama Burn!", description=f"{prefix}{random.choice(jokes)}", color=discord.Color.red())
    embed.set_image(url=random.choice(reaction_gifs))
    await ctx.send(embed=embed)

# ==========================================
# 11. SCANNER COMMANDS
# ==========================================

@bot.command()
@commands.cooldown(1, 2, commands.BucketType.user)
async def iqtest(ctx, member: discord.Member = None):
    target = member or ctx.author
    iq = random.randint(50, 180)
    if iq < 75: rank = "Room Temperature Brain 🧊"
    elif iq < 110: rank = "Completely Average Human 😐"
    elif iq < 140: rank = "Certified Big Brain 🧠"
    else: rank = "Billionaire Mega-Mind Genius 👑"
    embed = discord.Embed(title="🧠 Advanced IQ Diagnostic Scanner", color=discord.Color.purple())
    embed.add_field(name="Target Individual", value=target.mention, inline=True)
    embed.add_field(name="Calculated IQ", value=f"**{iq}**", inline=True)
    embed.add_field(name="Official Ranking", value=f"`{rank}`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 2, commands.BucketType.user)
async def coinflip(ctx, choice: str):
    choice = choice.lower()
    if choice not in ['heads', 'tails', 'h', 't']:
        await ctx.send("❌ Choose `heads` or `tails`!")
        return
    result = random.choice(['heads', 'tails'])
    user_won = (result == choice) or (choice == 'h' and result == 'heads') or (choice == 't' and result == 'tails')
    if user_won:
        await ctx.send(f"🪙 The coin landed on **{result}**! You guessed right! 🎉")
    else:
        await ctx.send(f"🪙 The coin landed on **{result}**! Better luck next time! 😢")

@bot.command()
@commands.cooldown(1, 2, commands.BucketType.user)
async def dice(ctx, guess: int):
    if guess < 1 or guess > 6:
        await ctx.send("❌ Pick a number between 1 and 6!")
        return
    roll = random.randint(1, 6)
    if roll == guess:
        await ctx.send(f"🎲 A **{roll}** was cast! Exact match! Perfect guess! 🏆")
    else:
        await ctx.send(f"🎲 A **{roll}** was cast! Your guess was wrong.")

@bot.command()
async def whoisgay(ctx):
    all_members = [m for m in ctx.guild.members if not m.bot]
    targets = [m for m in all_members if m.id != ctx.author.id]
    if not targets:
        await ctx.send("There is no one else in this server to target! 😂")
        return
    random_member = random.choice(targets)
    await ctx.send(f"{random_member.mention} is gayy 🌈")

@bot.command()
async def gayrate(ctx, member: discord.Member = None):
    target = member or ctx.author
    rate = random.randint(0, 100)
    embed = discord.Embed(title="🌈 Gayrate Machine Scanner", description=f"Scanning {target.mention}'s metrics...", color=discord.Color.magenta())
    embed.add_field(name="Measurement Result", value=f"{target.name} is **{rate}%** gayy! 🏳️‍🌈", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    target = member or ctx.author
    embed = discord.Embed(title=f"🖼️ Profile Image Resource: {target.name}", color=discord.Color.blurple())
    avatar_url = target.display_avatar.replace(static_format="png").url
    embed.set_image(url=avatar_url)
    await ctx.send(embed=embed)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    target = member or ctx.author
    embed = discord.Embed(title=f"👤 Identity Metrics Summary: {target.name}", color=discord.Color.dark_gray())
    embed.set_thumbnail(url=target.display_avatar.replace(static_format="png").url)
    embed.add_field(name="Account ID Key", value=f"`{target.id}`", inline=True)
    embed.add_field(name="Top Role", value=f"{target.top_role.mention if target.top_role else 'None'}", inline=True)
    embed.add_field(name="Created On", value=target.created_at.strftime("%b %d, %Y"), inline=False)
    embed.add_field(name="Joined Server On", value=target.joined_at.strftime("%b %d, %Y"), inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f'🧹 Cleared {amount} messages!', delete_after=3)

# ==========================================
# 12. ACTIVITY TRACKER COMMANDS
# ==========================================

@bot.command()
@commands.cooldown(1, 2, commands.BucketType.user)
async def vctime(ctx, member: discord.Member = None):
    target = member or ctx.author
    total = vc_total_times.get(target.id, 0)

    # Add current live session if they're in VC right now
    if target.id in vc_join_times:
        total += time.time() - vc_join_times[target.id]

    if total == 0:
        await ctx.send(f"📭 {target.mention} hasn't spent any time in VC since I came online.")
        return

    embed = discord.Embed(title="🎙️ Voice Channel Time Tracker", color=discord.Color.blurple())
    embed.add_field(name="Member", value=target.mention, inline=True)
    embed.add_field(name="Total VC Time", value=f"**{format_duration(total)}**", inline=True)
    if target.id in vc_join_times:
        live = time.time() - vc_join_times[target.id]
        embed.add_field(name="🔴 Live Session", value=format_duration(live), inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 5, commands.BucketType.guild)
async def topsession(ctx):
    if not vc_total_times and not vc_join_times:
        await ctx.send("📭 No VC activity recorded yet since I came online.")
        return

    # Merge stored totals with any live sessions
    combined = dict(vc_total_times)
    for uid, join_time in vc_join_times.items():
        combined[uid] = combined.get(uid, 0) + (time.time() - join_time)

    sorted_members = sorted(combined.items(), key=lambda x: x[1], reverse=True)[:10]

    embed = discord.Embed(title="🏆 VC Time Leaderboard", color=discord.Color.gold())
    medals = ["🥇", "🥈", "🥉"]
    board = ""
    for i, (uid, seconds) in enumerate(sorted_members):
        member = ctx.guild.get_member(uid)
        name = member.display_name if member else f"Unknown ({uid})"
        medal = medals[i] if i < 3 else f"`#{i+1}`"
        live = " 🔴" if uid in vc_join_times else ""
        board += f"{medal} **{name}** — {format_duration(seconds)}{live}\n"

    embed.description = board
    embed.set_footer(text="🔴 = Currently in VC")
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 2, commands.BucketType.user)
async def lastgame(ctx, member: discord.Member = None):
    target = member or ctx.author

    # Check if they're currently playing something live
    current_game = next((a for a in target.activities if isinstance(a, discord.Game)), None)
    if current_game:
        embed = discord.Embed(title="🎮 Game Activity", color=discord.Color.green())
        embed.add_field(name="Member", value=target.mention, inline=True)
        embed.add_field(name="🟢 Currently Playing", value=f"**{current_game.name}**", inline=True)
        await ctx.send(embed=embed)
        return

    # Fall back to cached last game
    data = last_game.get(target.id)
    if not data:
        await ctx.send(f"🎮 No game activity recorded for {target.mention} since I came online.")
        return

    ended = data.get("ended")
    time_str = f"<t:{int(data['time'])}:R>" if not ended else f"<t:{int(ended)}:R>"
    status = "Last seen playing" if ended else "Was playing"

    embed = discord.Embed(title="🎮 Game Activity", color=discord.Color.purple())
    embed.add_field(name="Member", value=target.mention, inline=True)
    embed.add_field(name=status, value=f"**{data['name']}**", inline=True)
    embed.add_field(name="Last Seen", value=time_str, inline=False)
    await ctx.send(embed=embed)

bot.run(TOKEN)
