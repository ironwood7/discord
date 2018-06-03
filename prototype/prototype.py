import discord
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
            if message.channel.id == '450680470649176065':    # testchannel
                await airdrop.on_message_inner(client, message)

client.run()