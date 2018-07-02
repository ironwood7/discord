import discord
import testnet
import airdrop
import private
import welcome
import myserver
import wallet

client = discord.Client()

# ,gettoken error message
CMD_ERROR_GETTOKEN =\
"\
For this comannd, please 'Direct Message' to Amaryllis.\
このコマンドは、Amaryllisにダイレクトメッセージしてください。\
"

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

    airdrop.on_ready()
    welcome.on_ready()
    wallet.on_ready()

#################
# welcome only
#################
@client.event
async def on_member_join(member):
    await welcome.on_member_join_inner(client, member, myserver.CH_ID_WELCOME) # welcome

@client.event
async def on_member_remove(member):
    await welcome.on_member_remove_inner(client, member, myserver.CH_ID_WELCOME) # welcome


@client.event
async def on_message(message):
    if client.user == message.author:
        return
    # command
    if message.content.startswith(","):
        print("channel name={0} id={1}".format(message.channel, message.channel.id))
        if message.channel.type == discord.ChannelType.private :
            await private.on_message_inner(client, message)
        else :
            # Provisional imp >>
            # none private message
            if message.content.startswith(",gettoken"):
                print(message.channel)
                await client.send_message(message.channel, CMD_ERROR_GETTOKEN)
                return
            # << Provisional imp
            # testnet
            if message.channel.id == myserver.CH_ID_TESTNET: await testnet.on_message_inner(client, message)
            # airdrop
            elif message.channel.id == myserver.CH_ID_AIRDROP: await airdrop.on_message_inner(client, message)
            # wallet
            elif message.channel.id == myserver.CH_ID_REGISTER: await wallet.on_message_inner(client, message)
            # address
            elif message.channel.id == myserver.CH_ID_ADDRESS: await wallet.on_message_inner(client, message)
            # wallet
            elif message.channel.id == myserver.CH_ID_WALLET: await wallet.on_message_inner(client, message)
            else:
                pass

        return


if __name__ == '__main__':
    client.run(myserver.TOKEN)
    pass

