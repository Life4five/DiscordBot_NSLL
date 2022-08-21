from config import client
from discord.ext import commands
import config as cfg
import discord


@client.command(description='Disconnects the bot')
async def shut():
    await client.close()


@commands.cooldown(1, 3, commands.BucketType.user)
@client.command(description='Returns your message')
async def echo(ctx, *msg):
    await ctx.send(' '.join(msg))


@client.command(name='commands', description='Show all available commands')
async def cmds(ctx):
    embed = discord.Embed(title='All available commands', color=0)
    for command in client.commands:
        name = f'`{command.name}`'
        description = command.description if command.description != '' else 'Description is missing'
        embed.add_field(name=f'{name}', value=f'{description}', inline=False)

    await ctx.send(embed=embed)


client.run(cfg.TOKEN)
