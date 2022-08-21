import discord
import config as cfg
from config import bot
from config import cursor
from config import db
from discord.ext import commands
from asyncio import sleep


@bot.command(description='Returns your message')
async def echo(ctx, *msg):
    await ctx.send(' '.join(msg))


@bot.command(name='commands', description='Show all available commands')
async def cmds(ctx):
    embed = discord.Embed(title='All available commands', color=0)
    for command in bot.commands:
        name = f'`{command.name}`'
        description = command.description if command.description != '' else 'Description is missing'
        embed.add_field(name=f'{name}', value=f'{description}', inline=False)

    await ctx.send(embed=embed)


@commands.has_permissions(administrator=True)
@bot.command(description='SQL queries executing')
async def sql(ctx, *query):
    result = ""
    for i in cursor.execute(f"{' '.join(query)}"):
        result += str(i) + '\n'
    if result == '':
        await ctx.send("Query success")
    else:
        await ctx.send(result)


@commands.has_permissions(administrator=True)
@bot.command(description='Updates the database')
async def reset_economy(ctx):  # TODO: You should check all members in DB and insert if it is absent
    guild = bot.get_guild(606208697328467969)
    for member in guild.members:
        if member.bot:
            continue
        cursor.execute(f"INSERT INTO users VALUES (?, ?, ?)", (member.id, member.name, 0))
    db.commit()
    await ctx.send("Database successfully restored!")


@commands.has_permissions(administrator=True)
@bot.command(name='reset-economy', description='Zero balance to all members')
async def command(ctx):
    cursor.execute("UPDATE users set Balance = 0")
    db.commit()
    await ctx.send("Economy restored!")


@bot.command(description='Know your balance', aliases=['bal', 'ифд', 'ифдфтсу'])
async def balance(ctx):
    user_balance = cursor.execute(f"SELECT Balance FROM users WHERE id = {ctx.author.id}")
    await ctx.send(cursor.fetchone()[0])


@bot.command(description='The most rich members', aliases=['leaderboard'])
async def top(ctx):
    cursor.execute("SELECT Nickname, Balance FROM users ORDER BY Balance DESC LIMIT 10")
    msg = ''
    for row in cursor.fetchall():
        msg += str(row[0]) + ' ' + str(row[1]) + '\n'
    await ctx.send(f'{msg}')


bot.run(cfg.TOKEN)
