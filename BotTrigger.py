import os
import random
from pathlib import Path
from threading import Thread
from dotenv import load_dotenv
from flask import Flask
import discord
from discord.ext import commands, tasks

# ==========================================
# 1. BACKGROUND FLASK WEB SERVER FOR RENDER
# ==========================================
# This creates a dummy webpage so Render doesn't shut down the bot.
app = Flask('')

@app.route('/')
def home():
    return "LOL BOT is Online!"

def run_web_server():
    # Render requires binding to port 10000 or the PORT env variable
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True # Allows clean script exit when stopped
    t.start()

# Start the web server background thread immediately
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

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# 🎨 CUSTOM ROTATING STATUS ACTIVITY LOOP
@tasks.loop(seconds=20)
async def change_status():
    statuses = [
        discord.Game(name="!help | Version 2.0"),
        discord.Activity(type=discord.ActivityType.watching, name="over the server"),
        discord.Game(name="Flashing status loops")
    ]
    await bot.change_presence(activity=random.choice(statuses))

@bot.event
async def on_ready():
    print(f'Success! Bot is online as {bot.user.name}')
    if not change_status.is_running():
        change_status.start()

# 🛡️ ANTI-SPAM COOLDOWN ERROR HANDLER ACTIONS
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Slow down! You can use this command again in **{error.retry_after:.1f}** seconds.", delete_after=5)
    elif isinstance(error, commands.BadArgument) or isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Invalid inputs! Use `!help` to see how to format the command.")
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
# 4. CUSTOM HELP COMMAND MENU SYSTEM
# ==========================================
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📜 LOL BOT Help Menu",
        description="Here is your updated list of all active commands:",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="🎲 Games (Just for Fun)", 
        value="`!coinflip [heads/tails]` - Wager a guess on a coin toss\n`!dice [1-6]` - Guess a six-sided dice roll outcome", 
        inline=False
    )
    embed.add_field(
        name="🎉 Fun Modules & Ratings", 
        value="`!whoisgay` - Calls out a random server member\n`!gayrate [@user]` - Rates your target's percentage meter\n`!hello` - Simple ping system tester", 
        inline=False
    )
    embed.add_field(
        name="👤 Profile Lookup Utilities", 
        value="`!avatar [@user]` - Pulls down profile avatar imagery\n`!userinfo [@user]` - Displays account timeline details", 
        inline=False
    )
    embed.add_field(
        name="🛠️ Moderation Staff Systems", 
        value="`!clear [number]` - Purges recent textual communication messages securely", 
        inline=False
    )
    embed.set_footer(text="Anti-Spam active: Commands share a localized 2-second cooldown.")
    await ctx.send(embed=embed)

# ==========================================
# 5. GAME COMMANDS (NO MONEY SYSTEM)
# ==========================================
@bot.command()
@commands.cooldown(1, 2, commands.BucketType.user)
async def coinflip(ctx, choice: str):
    choice = choice.lower()
    if choice not in ['heads', 'tails', 'h', 't']:
        await ctx.send("❌ You must choose `heads` or `tails`!")
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
        await ctx.send("❌ You must pick a number between 1 and 6!")
        return
        
    roll = random.randint(1, 6)
    
    if roll == guess:
        await ctx.send(f"🎲 A **{roll}** was cast! Exact match! Perfect guess! 🏆")
    else:
        await ctx.send(f"🎲 A **{roll}** was cast! Your guess was wrong.")

# ==========================================
# 6. FUN COMMAND MODULES
# ==========================================
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
    
    embed = discord.Embed(
        title="🌈 Gayrate Machine Scanner",
        description=f"Scanning {target.mention}'s metrics...",
        color=discord.Color.magenta()
    )
    embed.add_field(name="Measurement Result", value=f"{target.name} is **{rate}%** gayy! 🏳️‍🌈", inline=False)
    await ctx.send(embed=embed)

# ==========================================
# 7. PROFILE LOOKUP UTILITIES (STATIC PNG FIXED)
# ==========================================
@bot.command()
async def avatar(ctx, member: discord.Member = None):
    target = member or ctx.author
    embed = discord.Embed(title=f"🖼️ Profile Image Resource: {target.name}", color=discord.Color.blurple())
    
    # This forces Discord to convert the image link into a clean static PNG file format
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

# ==========================================
# 8. CORE UTILITY HANDLERS
# ==========================================
@bot.command()
async def hello(ctx):
    await ctx.send(f'Hello {ctx.author.name}! Your bot is working perfectly.')

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f'🧹 Cleared {amount} messages!', delete_after=3)

bot.run(TOKEN)
