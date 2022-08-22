import discord
import config as cfg
from config import bot
from config import cursor
from config import db
from config import CURRENCY_SYMBOL as COIN
from discord.ext import commands
import random


@bot.command(description='Returns your message')
async def echo(ctx, *msg):
    await ctx.send(' '.join(msg))


@bot.command(name='commands', description='Show all available commands', aliases=['cmds', 'ඞ'])
async def cmds(ctx):
    embed = discord.Embed(title='All available commands', color=0)
    for cmd in bot.commands:
        name = f'`{cmd.name}`'
        description = cmd.description if cmd.description != '' else 'Description is missing'
        embed.add_field(name=f'{name}', value=f'{description}', inline=False)

    await ctx.send(embed=embed)


@commands.has_permissions(administrator=True)
@bot.command(description='**[ADMIN ONLY]** SQL queries executing')
async def sql(ctx, *query):
    result = ""
    for i in cursor.execute(f"{' '.join(query)}"):
        result += str(i) + '\n'
    if result == '':
        await ctx.send("Query success")
    else:
        await ctx.send(result)


@commands.has_permissions(administrator=True)  # TODO: Update database, not reset
@bot.command(description='**[ADMIN ONLY]** Updates the database', aliases=['reset-database'])
async def reset_database(ctx):
    guild = bot.get_guild(606208697328467969)
    for member in guild.members:
        if member.bot:
            continue
        cursor.execute(f"INSERT INTO users VALUES (?, ?, ?, ?)", (member.id, member.name, 0, 0))
    db.commit()
    await ctx.send("Database successfully restored!")


@commands.has_permissions(administrator=True)
@bot.command(description='**[ADMIN ONLY]** Zero balance to all members', aliases=['reset-economy'])
async def reset_economy(ctx):
    cursor.execute("UPDATE users set Balance = 0 WHERE  Balance != 0")
    cursor.execute("UPDATE server set Bank = 1000000000")
    db.commit()
    await ctx.send("Economy restored!")


@bot.command(description='Shows budget of the server', aliases=['server-stats'])
async def server_stats(ctx):
    embed = discord.Embed(title='Title', description='description', color=0)
    cursor.execute("SELECT * FROM server")
    embed.add_field(name='Bank', value='', inline=True)
    embed.add_field(name='Members', value='', inline=True)
    embed.add_field(name='Both', value='', inline=True)


@bot.command(description='Know your balance', aliases=['bal', 'ифд', 'ифдфтсу'])
async def balance(ctx, user: discord.Member = 0):
    cursor.execute(f"SELECT Balance FROM users WHERE id = {user.id if user != 0 else ctx.author.id}")
    user_bal = cursor.fetchone()[0]
    embed = discord.Embed(title='Your balance:', description=f'{COIN} {"{:,}".format(user_bal)}', color=0xFFD700)
    await ctx.send(embed=embed)


@bot.command(description='The most rich members', aliases=['top-money', 'top-m'])
async def top_money(ctx, users: int = 10):
    embed = discord.Embed(title='Top members by', description='**Money**', color=0xFFD700)
    cursor.execute(f"SELECT Nickname, Balance FROM users ORDER BY Balance DESC LIMIT {users}")
    for user, user_bal in cursor.fetchall():
        embed.add_field(name=f'{user}', value=f'{COIN} {user_bal}', inline=False)
    await ctx.send(embed=embed)


@bot.command(description='The most big members', aliases=['top-level', 'top-l'])
async def top_level(ctx, users: int = 10):
    embed = discord.Embed(title='Top members by', description='**Level**', color=0xFFD700)
    cursor.execute(f"SELECT Nickname, Level FROM users ORDER BY Balance DESC LIMIT {users}")
    for user, user_level in cursor.fetchall():
        embed.add_field(name=f'{user}', value=f'🔰 {user_level}', inline=False)
    await ctx.send(embed=embed)


@commands.has_permissions(administrator=True)
@bot.command(description='**[ADMIN ONLY]** Add / Remove money for user', aliases=['transfer-money', 't-m'])
async def transfer_money(ctx, user: discord.Member, amount):
    trans_money(user, amount)
    user_bal = get_bal(user)
    embed = discord.Embed(title='Money was transferred!', description=f'Balance {user.mention}:\n {COIN} {user_bal}',
                          color=0xFFD700)
    await ctx.send(embed=embed)


def trans_money(user: discord.Member, amount: int):
    cursor.execute(f"UPDATE users set Balance = Balance + {amount} WHERE id = {user.id}")
    cursor.execute(f"UPDATE server set Bank = Bank - {amount}")
    db.commit()


def pay_money(payer: discord.Member, receiver: discord.Member, amount: int):
    cursor.execute(f"UPDATE users set Balance = Balance - {amount} WHERE id = {payer.id}")
    cursor.execute(f"UPDATE users set Balance = Balance + {amount} WHERE id = {receiver.id}")

    db.commit()


def get_bal(user: discord.Member):
    cursor.execute(f"SELECT Balance FROM users WHERE id = {user.id}")
    return cursor.fetchone()[0]


# Money income
@commands.cooldown(1, 10, commands.BucketType.user)
@bot.command(description='Legal way to earn money')
async def work(ctx):
    income = random.randint(1900, 2100)
    trans_money(ctx.author, income)
    embed = discord.Embed(title='Work',
                          description=f'You earned {COIN} {income} \n Balance: {COIN} {get_bal(ctx.author)}')
    await ctx.send(embed=embed)


@bot.command(description='Give your money to friend!') # TODO: Make embed
async def pay(ctx, user: discord.Member, amount):
    pay_money(ctx.author, user, amount)
    embed = discord.Embed(title=f"Paid to {user} from {ctx.author}",
                          description=f'Balances:\n'
                                      f'**{ctx.author}**\n'
                                      f'{COIN} {get_bal(ctx.author)}\n'
                                      f'**{user}**\n'
                                      f'{COIN} {get_bal(user)}')
    await ctx.send(embed=embed)


# Games
@commands.cooldown(1, 5, commands.BucketType.user)
@bot.command(description='Toss the coin, 50% chance')
async def toss(ctx, bet):
    if bet == 'all':
        bet = get_bal(ctx.author)
    bet = abs(int(bet))
    user_bal = get_bal(ctx.author)
    if user_bal < bet or user_bal == 0:
        await ctx.send('Not enough money!')
        return
    success = random.randint(0, 1)
    if success == 1:
        trans_money(ctx.author, bet)
        user_bal = get_bal(ctx.author)
        embed = discord.Embed(title=f"Toss the coin",
                              description=f'You win! \n\n **Your balance:**\n {COIN} {"{:,}".format(user_bal)}',
                              color=0x00aa00)
        await ctx.send(embed=embed)
    else:
        trans_money(ctx.author, -bet)
        user_bal = get_bal(ctx.author)
        embed = discord.Embed(title=f"Toss the coin",
                              description=f'You lost.. \n\n **Your balance:**\n {COIN} {"{:,}".format(user_bal)}',
                              color=0xaa0000)
        await ctx.send(embed=embed)


bot.run(cfg.TOKEN)
