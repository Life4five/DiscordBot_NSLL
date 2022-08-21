from discord.ext import commands

TOKEN = 'OTUwMDAyMDAzODg1NTU1Nzky.GhVKjz.PycQl0afPHDao6qXPWFWgjej9n74QUKmTV52kE'

PREFIX = '$'
SYSTEM_CHANNEL_ID = 815614417827397652  # channel where the messages will be sent ## admin-chat

client = commands.Bot(command_prefix=PREFIX)


@client.event
async def on_ready():
    print(f'{client.user} is working!')
    sys_channel = client.get_channel(SYSTEM_CHANNEL_ID)
    await sys_channel.send(f'{client.user.mention} is working!')


@client.event
async def on_disconnect():
    print(f'{client.user} was disconnected')


@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("```You are missing Administrator permission(s) to run this command.```")
    else:
        await ctx.send(error)
