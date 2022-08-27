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
        db.commit()
    else:
        await ctx.send(result)


@commands.has_permissions(administrator=True)  # TODO: Update database, not reset
@bot.command(description='**[ADMIN ONLY]** Updates the database', aliases=['reset-database'])
async def update_users(ctx):
    guild = bot.get_guild(606208697328467969)
    for member in guild.members:
        if member.bot:
            continue
        cursor.execute(f"""
            INSERT INTO users(User_id, Nickname, Balance, Level)
            SELECT {member.id}, '{member}', 0, 0
            WHERE NOT EXISTS(SELECT User_id FROM users WHERE User_id = {member.id})
        """)
        cursor.execute(f"""CREATE TABLE IF NOT EXISTS 'u{member.id}' (
            Item_id integer,
            Type text,
            Item_name text,
            Item_description text,
            Quantity int
        )""")
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
    embed = discord.Embed(title='Server stats', description='All budget of the server', color=0xFFD700)
    embed.add_field(name='Bank', value=f'{COIN} {"{:,}".format(bank_bal)}', inline=True)
    embed.add_field(name='Members', value=f'{COIN} {"{:,}".format(members_bal)}', inline=True)
    embed.add_field(name='Both', value=f'{COIN} {"{:,}".format(both_bal)}', inline=True)
    await ctx.send(embed=embed)


@bot.command(description='Know your balance', aliases=['bal', 'ифд', 'ифдфтсу'])
async def balance(ctx, user: discord.Member = 0):
    cursor.execute(f"SELECT Balance FROM users WHERE User_id = {user.id if user != 0 else ctx.author.id}")
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
    cursor.execute(f"UPDATE users set Balance = Balance + {amount} WHERE User_id = {user.id}")
    cursor.execute(f"UPDATE server set Bank = Bank - {amount}")
    db.commit()


def pay_money(payer: discord.Member, receiver: discord.Member, amount: int):
    amount = abs(amount)
    cursor.execute(f"UPDATE users set Balance = Balance - {amount} WHERE User_id = {payer.id}")
    cursor.execute(f"UPDATE users set Balance = Balance + {amount} WHERE User_id = {receiver.id}")

    db.commit()


def get_bal(user: discord.Member):
    cursor.execute(f"SELECT Balance FROM users WHERE User_id = {user.id}")
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
    answer = ''
    await ctx.send(solve)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    valid = False
    while not valid:
        try:
            answer = await bot.wait_for('message', timeout=60, check=check)
            answer = int(answer.content)
            valid = True
        except ValueError:
            await ctx.send('Invalid value!')
        except asyncio.TimeoutError:
            await ctx.send('Timeout')
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


# Items and shop
def give_items(receiver: discord.Member, item_id: int, quantity: int):
    item = cursor.execute(f"SELECT * FROM shop WHERE item_id = {item_id}").fetchall()[0]
    id, name, description, price, item_type = item[0], item[1], item[2], item[3], item[5]
    cursor.execute(f"INSERT INTO 'u{receiver.id}' VALUES (?, ?, ?, ?, ?)", (id, item_type, name, description, quantity))
    db.commit()


@bot.command(description='Shows all items in the server')
async def shop(ctx):
    embed = discord.Embed(title='Items', description='Buy an item with the `buy-item <id> [quantity]` command.',
                          color=0)
    all_items = cursor.execute("SELECT * FROM shop").fetchall()

    for item in all_items:
        id = item[0]
        name = item[1]
        description = item[2]
        price = item[3]
        stock = item[4]
        embed.add_field(name=f'[{id}] {COIN} {price} — {name}',
                        value=f'{description}',
                        inline=False)
    await ctx.send(embed=embed)


@bot.command(description='Show your inventory', aliases=['inv'])
async def inventory(ctx, user: discord.Member = 0):
    if user == 0:
        user = ctx.author
    inv_items = cursor.execute(f"SELECT * FROM 'u{user.id}'").fetchall()  # TODO: Something with quotes
    embed = discord.Embed(title='Inventory', description=f'There are {len(inv_items)} items',
                          color=0)
    for inv_item in inv_items:
        inv_item_id = inv_item[0]
        inv_item_type = inv_item[1]
        inv_item_name = inv_item[2]
        inv_item_description = inv_item[3]
        inv_item_quantity = inv_item[4]
        embed.add_field(name=f'[{inv_item_id}] [{inv_item_type}] {inv_item_name}, `{inv_item_quantity}` шт',
                        value=f'{inv_item_description}',
                        inline=False)
    await ctx.send(embed=embed)


@bot.command(desciption="Let's purchase some stuff", aliases=['buy-item'])
async def buy_item(ctx, item_id, quantity: int = 1):
    quantity = abs(quantity)
    if quantity == 0:
        await ctx.send("You can't buy zero items")
        return
    item_price = cursor.execute(f"SELECT Price FROM shop WHERE item_id = {item_id}").fetchone()[0] * quantity
    if check_bal(ctx.author, item_price):
        await not_enough_money(ctx)
        return
    trans_money(ctx.author, -item_price)
    give_items(ctx.author, item_id, quantity)
    embed = discord.Embed(title="Successful purchase",
                          description=f'You bought {quantity} items for {COIN} {item_price}')
    await ctx.send(embed=embed)


bot.run(cfg.TOKEN)
