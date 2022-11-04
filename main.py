import discord
import config as cfg
from config import cursor, db, bot
from config import CURRENCY_SYMBOL as COIN
from discord.ext import tasks, commands
import random
import asyncio
import io
import aiohttp


# Commands
def trans_money(user: discord.Member, amount: int):
    cursor.execute(f"UPDATE users set Balance = Balance + {amount} WHERE User_id = {user.id}")
    cursor.execute(f"UPDATE server set Bank = Bank - {amount}")
    db.commit()


def pay_money(payer: discord.Member, receiver: discord.Member, amount: int):
    amount = abs(amount)
    trans_money(payer, -amount)
    trans_money(receiver, amount)


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


async def confirm_act(ctx):
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


# General
@bot.command(description='Latency', aliases=['latency'])
async def ping(ctx):
    print("Bot latency:", bot.latency)
    await ctx.send(f"{round(bot.latency * 1000)}ms")


@bot.command(description='Returns your message')
async def echo(ctx, *msg):
    await ctx.send(' '.join(msg))


@commands.cooldown(1, 300, commands.BucketType.user)
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


@commands.has_permissions(administrator=True)
@bot.command(description="Add role(s) to all members")
async def add_roles_to_all(ctx, *roles: discord.Role):
    print('add role to all users')
    for u in ctx.guild.members:
        await u.add_roles(*roles)
        await asyncio.sleep(1)
    await ctx.send('Success')


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


@commands.has_permissions(administrator=True)
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


@bot.command(description='The best users!')
async def top(ctx, users: int = 10):
    embed = discord.Embed(title=f'Top {users} members', description='All time', color=0xFFD700)
    cursor.execute(f"SELECT Nickname, Balance, Exp, Level FROM users ORDER BY Exp DESC, Balance DESC LIMIT {users}")
    users_stats = cursor.fetchall()
    for user, user_bal, user_exp, user_level in users_stats:
        embed.add_field(name=f'{user}',
                        value=f'{user_level} 🔰 {"{:,}".format(user_exp)} | {COIN} {"{:,}".format(user_bal)}',
                        inline=False)
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


# Legal money income
@commands.cooldown(1, cfg.CD_WORK, commands.BucketType.user)
@bot.command(description='Legal way to earn money')
async def work(ctx):
    problem = get_random_calc()
    solve = '{} {} {} {} {} = ?'.format(problem[0], problem[1], problem[2], problem[3], problem[4])
    answer = ''
    if -100 < problem[5] < 100:  # problem[5] is correct answer on math problem
        income = random.randint(1900, 2100)
    else:
        income = random.randint(2100, 2300)
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
    trans_money(ctx.author, income)
    author_bal = get_bal(ctx.author)
    embed = discord.Embed(title=':hammer_pick: Work',
                          description=f'You earned {COIN} {"{:,}".format(income)} \n'
                                      f'Balance: {COIN} {"{:,}".format(author_bal)}')
    await ctx.send(embed=embed)


@bot.command(description='Give your money to friend!')
async def pay(ctx, user: discord.Member, amount):
    if amount == 'all':
        if not await confirm_act(ctx):
            return
        amount = get_bal(ctx.author)
    amount = int(amount)
    if check_bal(ctx.author, amount):
        await not_enough_money(ctx)
        return
    pay_money(ctx.author, user, amount)
    embed = discord.Embed(title=f"{user.name} :arrow_right: {ctx.author.name}",
                          description=f'Balances:\n'
                                      f'**{ctx.author.name}**\n'
                                      f'{COIN} {get_bal(ctx.author)}\n'
                                      f'**{user.name}**\n'
                                      f'{COIN} {get_bal(user)}')
    await ctx.send(embed=embed)


# Crime money income
# TODO: Rob Command: improve rob chance system
@commands.cooldown(1, 5, commands.BucketType.user)
@bot.command(description='Steal the money from user. It has high level of risk!')
async def rob(ctx, user: discord.Member):
    user_bal = get_bal(user)
    success = random.choice([True, False])
    robbed = random.randrange(user_bal)
    if success:
        trans_money(ctx.author, robbed)
        trans_money(user, -robbed)
        embed = discord.Embed(title="Success",
                              description=f"Robbed for {COIN} {'{:,}'.format(robbed)}", color=0x00AA00)
        await ctx.send(embed=embed)
    else:
        trans_money(ctx.author, -robbed)
        embed = discord.Embed(title="Success",
                              description=f"You've been fined for {COIN} {'{:,}'.format(robbed)}", color=0xAA0000)
        await ctx.send(embed=embed)


# Games
@commands.cooldown(1, cfg.CD_TOSS, commands.BucketType.user)
@bot.command(description='Toss the coin, 50% chance')
async def toss(ctx, bet):
    if bet == 'all':
        if not await confirm_act(ctx):
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


# TODO: Roulette command


# TODO: Slot-Machine command with Jackpot


# Items and shop
def give_items(receiver: discord.Member, item_id: int, quantity: int, **store):
    store_type = ''
    if store == 'market':
        store_type = 'market'
    elif store == 'shop':
        store_type = 'shop'
    item = cursor.execute(f"SELECT * FROM {store_type} WHERE Item_id = {item_id}").fetchall()[0]
    shop_id, shop_name, shop_description, shop_price, shop_type = item[0], item[1], item[2], item[3], item[5]
    inv_item = cursor.execute(f"SELECT * FROM 'u{receiver.id}' WHERE Item_id = {shop_id}").fetchall()
    if not inv_item:
        cursor.execute(
            f"""INSERT INTO 'u{receiver.id}'
                VALUES ({shop_id}, '{shop_type}', '{shop_name}', '{shop_description}', {quantity})""")
    else:
        cursor.execute(
            f"UPDATE 'u{receiver.id}' set Quantity = Quantity + {quantity} WHERE Item_id = {shop_id}")
    db.commit()


@bot.command(description='Shows all items in the server')
async def shop(ctx):
    embed = discord.Embed(title='Shop', description='Buy an item with the `buy-item <id> [quantity]` command.',
                          color=0)
    all_items = cursor.execute("SELECT * FROM shop").fetchall()

    for item in all_items:
        id = item[0]
        name = item[1]
        description = item[2]
        price = item[3]
        embed.add_field(name=f'[{id}] {COIN} {price} — {name}',
                        value=f'{description}',
                        inline=False)
    await ctx.send(embed=embed)


@bot.command(description='All items offering by users', aliases=['store'])
async def market(ctx):
    embed = discord.Embed(title='Market', description='All items currently selling by users \n'
                                                      'Buy an item with the `buy-market-item <id> [quantity]` command.',
                          color=0)
    all_market_items = cursor.execute("SELECT * FROM market").fetchall()

    for item in all_market_items:
        id = item[0]
        name = item[1]
        description = item[2]
        price = item[3]
        i_type = item[5]
        seller = bot.get_user(int(item[6]))
        embed.add_field(name=f'[{id}] [{i_type}] {COIN} {price} — {name} `Seller: {seller}`',
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


@bot.command(description="Let's purchase some stuff", aliases=['buy-item'])
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


@bot.command(description="Buy item from market", aliases=['buy-market-item'])
async def buy_market_item(ctx, item_id, quantity: int = 1):
    quantity = abs(quantity)
    if quantity == 0:
        await ctx.send("You can't buy zero items")
        return
    item_price = cursor.execute(f"SELECT Price FROM market WHERE item_id = {item_id}").fetchone()[0] * quantity
    item_stock = cursor.execute(f"SELECT Stock FROM shop WHERE Item_id = {item_id}").fetchone()[0]
    if check_bal(ctx.author, item_price):
        await not_enough_money(ctx)
        return
    trans_money(ctx.author, -item_price)
    give_items(ctx.author, item_id, quantity, market=True)
    if item_stock >= quantity:
        cursor.execute(f"UPDATE market SET Stock = Stock - {quantity}")
    embed = discord.Embed(title="Successful purchase",
                          description=f'You bought {quantity} items for {COIN} {item_price}')
    await ctx.send(embed=embed)


# TODO: use-item command OR smth what uses items in inventory
@bot.command(description="Use item to get all its benefits", aliases=['use-item'])
async def use_item(ctx, item_id: int, amount: int):
    try:
        i_type = cursor.execute(f"SELECT Type FROM 'u{ctx.author.id}' WHERE Item_id = ?", [item_id]).fetchone()[0]
        i_count = cursor.execute(f"SELECT Quantity FROM 'u{ctx.author.id}' WHERE Item_id = ?", [item_id]).fetchone()[0]
    except TypeError:
        await ctx.send(f"Item not found")
        return
    match i_type:
        case 'EXP':
            trans_exp(ctx.author, amount * 100)
        case _:
            await ctx.send("You can't use this item")
            return
    if i_count >= amount:
        cursor.execute(f"UPDATE 'u{ctx.author.id}' SET Quantity = Quantity - {amount} WHERE Item_id = {item_id}")
        i_count -= amount
    else:
        await ctx.send("You don't have so many items")
        return
    if i_count == 0:
        cursor.execute(f"DELETE FROM 'u{ctx.author.id}' WHERE Item_id = {item_id}")
    db.commit()
    await ctx.send("Success")


# Level system
def get_exp(user: discord.Member):
    return cursor.execute(f"SELECT Exp FROM users WHERE User_id = {user.id}").fetchone()[0]


def trans_exp(receiver: discord.Member, amount: int):
    cursor.execute(f"UPDATE users set Exp = Exp + {amount} WHERE User_id = {receiver.id}")
    db.commit()


# TODO: Make embed more informative
@commands.has_permissions(administrator=True)
@bot.command(description='Know your experience', aliases=['exp'])
async def experience(ctx):
    user_exp = get_exp(ctx.author)
    embed = discord.Embed(title='Your experience:', description=f'🔰 {"{:,}".format(user_exp)}', color=0x800080)
    await ctx.send(embed=embed)


@commands.has_permissions(administrator=True)
@bot.command(description='Give / take experience to user', aliases=['transfer-exp', 'te'])
async def transfer_exp(ctx, user: discord.Member, amount: int):
    trans_exp(user, amount)
    user_exp = get_exp(user)
    embed = discord.Embed(title='Experience was transferred!', description=f'Experience {user.mention}:\n'
                                                                           f'🔰 {"{:,}".format(user_exp)}',
                          color=0x800080)
    await ctx.send(embed=embed)


# Music
@bot.command()
async def play(ctx):  # Some patriotic music
    # Gets voice channel of message author
    try:
        voice_channel = ctx.author.voice.channel
        channel = voice_channel.name
        vc = await voice_channel.connect()
        vc.play(discord.FFmpegPCMAudio(executable="ffmpeg51/bin/ffmpeg.exe",
                                       source=random.choice(['russia.ogg', 'ussr.oga', 'ukraine.ogg'])))
        # Sleep while audio is playing.
        while vc.is_playing():
            await asyncio.sleep(.5)
        await vc.disconnect()
    except AttributeError:
        await ctx.send("You must join in voice channel to use this command")


# graphics
@bot.command()
async def person(ctx):
    msg = await ctx.send("Getting image..")
    async with aiohttp.ClientSession() as session:
        async with session.get('https://thispersondoesnotexist.com/image') as resp:
            if resp.status != 200:
                return await ctx.send('Could not download file...')
            data = io.BytesIO(await resp.read())
            await ctx.send(file=discord.File(data, 'cool_image.png'))
            await msg.delete()


bot.run(cfg.TOKEN)
