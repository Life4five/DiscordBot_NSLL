from discord.ext import commands
import sqlite3
import discord

db = sqlite3.connect('server.db')
cursor = db.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    id INT,
    Nickname TEXT,
    Balance INT
)""")
db.commit()

TOKEN = 'OTUwMDAyMDAzODg1NTU1Nzky.GhVKjz.PycQl0afPHDao6qXPWFWgjej9n74QUKmTV52kE'

PREFIX = ['!!', '$']
SYSTEM_CHANNEL_ID = 815611328323911721  # channel where the messages will be sent ## admin-chat
CURRENCY_SYMBOL = ':coin:'

# Economy and commands cooldown (s)
CD_WORK = 60
CD_TOSS = 5
#

bot = commands.Bot(command_prefix=PREFIX, intents=discord.Intents.all())


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)


@bot.event
async def on_ready():
    sys_channel = bot.get_channel(SYSTEM_CHANNEL_ID)

    print(f'{bot.user} is working!')
    await sys_channel.send(f'{bot.user.mention} is working!')


@bot.event
async def on_disconnect():
    print(f'{bot.user} was disconnected')


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("```You are missing Administrator permission(s) to run this command.```")
    else:
        await ctx.send(error)
