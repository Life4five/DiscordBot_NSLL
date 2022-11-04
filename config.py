from discord.ext import commands
import sqlite3
import discord
from asyncio import sleep

db = sqlite3.connect('server.db')
cursor = db.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    id INT,
    Nickname TEXT,
    Balance INT
)""")
db.commit()

TOKEN = 'There was a token' # old token was changed

PREFIX = ['!', '$']
GUILD_ID = 0
SUPERADMIN_ID = 0  # For superpower commands
SYSTEM_CHANNEL_ID = 0  # channel where the messages will be sent ## admin-chat
CURRENCY_SYMBOL = ':coin:'

# Economy and commands cooldown (s)
CD_WORK = 120
CD_TOSS = 5
#

bot = commands.Bot(command_prefix=PREFIX, intents=discord.Intents.all(), case_insensitive=True)


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)


@bot.event
async def on_ready():
    sys_channel = bot.get_channel(SYSTEM_CHANNEL_ID)

    print(f'{bot.user} is working!')
    await sys_channel.send(f'{bot.user.mention} is working!', delete_after=120)


@bot.event
async def on_disconnect():
    print(f'{bot.user} was disconnected')


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("```You are missing Administrator permission(s) to run this command.```")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'You are missing some arguments. Type `$help {ctx.command.name}` for more info')
    elif isinstance(error, TypeError):
        await ctx.send(f"Error: Object not found")
    elif isinstance(error, commands.CommandOnCooldown):
        time_left = error.retry_after
        bot_reply = await ctx.send(f"Cooldown. Try again in `{round(time_left)}s`")
        await sleep(time_left)
        await bot_reply.edit(content='Cooldown is over', delete_after=5)
    else:
        await ctx.send(error)
        print(error)
