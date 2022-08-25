import discord
import config as cfg
from config import bot
from config import cursor
from config import db
from config import CURRENCY_SYMBOL as COIN
from discord.ext import commands
import random
import asyncio


# Commands
# General
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
@bot.command(description='**[ADMIN ONLY]** Deletes last n-messages')
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount)
    await ctx.send(f'Cleared `{amount}` messages!', delete_after=3)


# Database and economy
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
    cursor.execute("UPDATE server set Bank = 1000000000 WHERE Bank != 1000000000")
    db.commit()
    await ctx.send("Economy restored!")


@bot.command(description='Shows budget of the server', aliases=['server-stats', 'stats'])
async def server_stats(ctx):
    bank_bal = cursor.execute("SELECT * FROM server").fetchone()[0]
    members_bal = sum([x[0] for x in cursor.execute("SELECT Balance FROM users").fetchall()])
    both_bal = bank_bal + members_bal
    embed = discord.Embed(title='Server stats', description='All budget of the server', color=0)
    embed.add_field(name='Bank', value=f'{COIN} {"{:,}".format(bank_bal)}', inline=True)
    embed.add_field(name='Members', value=f'{COIN} {"{:,}".format(members_bal)}', inline=True)
    embed.add_field(name='Both', value=f'{COIN} {"{:,}".format(both_bal)}', inline=True)
    await ctx.send(embed=embed)


@bot.command(description='Know your balance', aliases=['bal', 'ифд', 'ифдфтсу'])
async def balance(ctx, user: discord.Member = 0):
    cursor.execute(f"SELECT Balance FROM users WHERE id = {user.id if user != 0 else ctx.author.id}")
    user_bal = cursor.fetchone()[0]
    embed = discord.Embed(title='Your balance:', description=f'{COIN} {"{:,}".format(user_bal)}', color=0xFFD700)
    await ctx.send(embed=embed)


@bot.command(description='The most rich members')
async def top(ctx, users: int = 10):
    embed = discord.Embed(title=f'Top {users} members', description='All time', color=0xFFD700)
    cursor.execute(f"SELECT Nickname, Balance, Level FROM users ORDER BY Balance DESC, Level DESC LIMIT {users}")
    users_stats = cursor.fetchall()
    for user, user_bal, user_level in users_stats:
        embed.add_field(name=f'{user}', value=f'{COIN} {"{:,}".format(user_bal)} | 🔰 {user_level}', inline=False)
    await ctx.send(embed=embed)


@commands.has_permissions(administrator=True)
@bot.command(description='**[ADMIN ONLY]** Add / Remove money for user', aliases=['transfer-money', 't-m', 'tm'])
async def transfer_money(ctx, user: discord.Member, amount):
    trans_money(user, amount)
    user_bal = get_bal(user)
    embed = discord.Embed(title='Money was transferred!', description=f'Balance {user.mention}:\n'
                                                                      f'{COIN} {"{:,}".format(user_bal)}',
                          color=0xFFD700)
    await ctx.send(embed=embed)


def trans_money(user: discord.Member, amount: int):
    cursor.execute(f"UPDATE users set Balance = Balance + {amount} WHERE id = {user.id}")
    cursor.execute(f"UPDATE server set Bank = Bank - {amount}")
    db.commit()


def pay_money(payer: discord.Member, receiver: discord.Member, amount: int):
    amount = abs(amount)
    cursor.execute(f"UPDATE users set Balance = Balance - {amount} WHERE id = {payer.id}")
    cursor.execute(f"UPDATE users set Balance = Balance + {amount} WHERE id = {receiver.id}")

    db.commit()


def get_bal(user: discord.Member):
    cursor.execute(f"SELECT Balance FROM users WHERE id = {user.id}")
    return cursor.fetchone()[0]


def check_bal(user: discord.Member, amount):
    user_bal = get_bal(user)
    if user_bal < amount or user_bal == 0:
        return True  # True, not enough money
    else:
        return False  # False, money is enough


async def not_enough_money(ctx):
    embed = discord.Embed(title='Not enough money!',
                          description=f'Your balance:\n {COIN} {"{:,}".format(get_bal(ctx.author))}')
    await ctx.send(embed=embed)


def get_random_calc():
    ops = ['+', '-', '*']
    num1 = str(random.randint(1, 10))
    num2 = str(random.randint(5, 20))
    num3 = str(random.randint(1, 10))
    op1 = random.choice(ops)
    op2 = random.choice(ops)
    res = eval(num1 + op1 + num2 + op2 + num3)
    return num1, op1, num2, op2, num3, res


async def confirm_act(m, ctx):
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send('Are you sure? y / n')
    try:
        confirm = await bot.wait_for('message', timeout=60, check=check)
        confirm = confirm.content
    except asyncio.TimeoutError:
        await ctx.send('Timeout')
        confirm = 'n'
    return confirm == 'y'


# Legal money income
@commands.cooldown(1, cfg.CD_WORK, commands.BucketType.user)
@bot.command(description='Legal way to earn money')
async def work(ctx):
    problem = get_random_calc()
    solve = '{} {} {} {} {} = ?'.format(problem[0], problem[1], problem[2], problem[3], problem[4])
    await ctx.send(solve)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        answer = await bot.wait_for('message', timeout=60, check=check)
        answer = int(answer.content)
    except ValueError:
        await ctx.send('Invalid value!')
        ctx.command.reset_cooldown(ctx)
        return
    except asyncio.TimeoutError:
        ctx.send('Timeout')
        ctx.command.reset_cooldown(ctx)
        return

    if answer != problem[5]:
        await ctx.send(f'Wrong answer. It was `{problem[5]}`')
        return
    income = random.randint(1900, 2100)
    trans_money(ctx.author, income)
    author_bal = get_bal(ctx.author)
    embed = discord.Embed(title=':hammer_pick: Work',
                          description=f'You earned {COIN} {"{:,}".format(income)} \n'
                                      f'Balance: {COIN} {"{:,}".format(author_bal)}')
    await ctx.send(embed=embed)


@bot.command(description='Give your money to friend!')
async def pay(ctx, user: discord.Member, amount):
    if amount == 'all':
        if not await confirm_act(ctx.message, ctx):
            return
        amount = get_bal(ctx.author)
    amount = int(amount)
    if check_bal(ctx.author, amount):
        await not_enough_money(ctx)
        return
    pay_money(ctx.author, user, amount)
    embed = discord.Embed(title=f"Paid to {user} from {ctx.author}",
                          description=f'Balances:\n'
                                      f'**{ctx.author}**\n'
                                      f'{COIN} {get_bal(ctx.author)}\n'
                                      f'**{user}**\n'
                                      f'{COIN} {get_bal(user)}')
    await ctx.send(embed=embed)


# Crime money income

# TODO: Rob Command

# Games
@commands.cooldown(1, cfg.CD_TOSS, commands.BucketType.user)
@bot.command(description='Toss the coin, 50% chance')
async def toss(ctx, bet):
    if bet == 'all':
        if not await confirm_act(ctx.message, ctx):
            return
        bet = get_bal(ctx.author)
    bet = abs(int(bet))
    user_bal = get_bal(ctx.author)
    if user_bal < bet or user_bal == 0:
        await not_enough_money(ctx)
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


# shop
@bot.command(description='Shows all goods in the shop')
async def shop(ctx):
    embed = discord.Embed(title='Shop', description='All items', color=0)
    cursor.execute("SELECT * FROM shop")
    shop_items = cursor.fetchall()
    for item in shop_items:
        id = item[0]
        name = item[1]
        price = item[2]
        description = item[3]
        stock = item[4]
        embed.add_field(name=f'[{id}] {COIN} {price} — {name}. В наличии: `{stock}`',
                        value=f'{description}',
                        inline=False)
    await ctx.send(embed=embed)


@bot.command(desciption='')  # TODO: Need to write
async def buy_item(ctx):
    pass


bot.run(cfg.TOKEN)
