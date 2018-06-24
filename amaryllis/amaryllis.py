import discord
import testnet
import airdrop
#import private
import welcome

client = discord.Client()

TOKEN="SERVER_ID"

CH_ID_TESTNET='450680522327195658'
CH_ID_AIRDROP='452338707173998612'
CH_ID_WELCOME='451762997644230656'

# testbotnet
# CH_ID_WELCOME ='455754856427290624'


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

    # chObj = client.get_channel(CH_ID_WELCOME)
    # await client.send_message(chObj, '皆様おはようございます')

    airdrop.on_ready()
    welcome.on_ready()

@client.event
async def on_member_join(member):
    if client.user == message.author:
        return
    await welcome.on_member_join_inner(client, member, CH_ID_WELCOME) # welcome

@client.event
async def on_member_join(member):
    if client.user == message.author:
        return
    await welcome.on_member_join_inner(client, member, CH_ID_WELCOME) # welcome


@client.event
async def on_message(message):
    if client.user == message.author:
        return
    if message.content.startswith(","):
        print("channel name={0} id={1}".format(message.channel, message.channel.id))
        if message.channel.type == discord.ChannelType.private :
            # await private.on_message_inner(client, message)
            pass
        else :
            if message.channel.id == CH_ID_TESTNET:    # testnet
                await testnet.on_message_inner(client, message)
            elif message.channel.id == CH_ID_AIRDROP:    # airdrop
                await airdrop.on_message_inner(client, message)
            elif message.channel.id == CH_ID_WELCOME:    # welcome
                await welcome.on_message_inner(client, message)


if __name__ == '__main__':
    client.run(TOKEN)
    pass

main()


