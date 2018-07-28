#!/usr/bin/python3

import discord
import private
import welcome
# import myserver
import myserver_test as myserver
import wallet
import sys
import os

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
            param = message.content.split()
            if param[0] == ",gettoken":
                print(message.channel)
                await client.send_message(message.channel, CMD_ERROR_GETTOKEN)
                return
            # << Provisional imp
            # elif message.channel.id == myserver.CH_ID_REGISTER \
            #     or message.channel.id == myserver.CH_ID_ADMIN \
            #     or message.channel.id == myserver.CH_ID_WALLET:
            else:
                await wallet.on_message_inner(client, message)
                pass
        return

def daemonize():
    pid = os.fork()
    if pid > 0:
        pid_file = open('./amaryllis_daemon.pid','w')
        pid_file.write(str(pid)+"\n")
        pid_file.close()
        sys.exit()
    if pid == 0:
        try:
            client.run(myserver.TOKEN)
        except:
            pass
        finally:
            print("client stop")


if __name__ == '__main__':
    # while True:
    #     daemonize()
    # # test
    client.run(myserver.TOKEN)

