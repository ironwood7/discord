import discord
import testnet
import airdrop

client = discord.Client()

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

    airdrop.on_ready()

@client.event
async def on_message(message):
    if message.content.startswith(","):
        if client.user != message.author:
            print("channel name={0} id={1}".format(message.channel, message.channel.id))
            if message.channel.id == '450680522327195658':    # testnet
                await testnet.on_message_inner(client, message)
            elif message.channel.id == '452338707173998612':    # airdrop
                await airdrop.on_message_inner(client, message)


client.run()