import discord
import subprocess

AMOUNT = 1000000

async def on_message_inner(client, message):
    print("testnet {0}:{1}".format(message.author, message.content))

    if message.content.startswith(",get"):
        params = message.content.split()
        if (len(params) < 2):
            await client.send_message(message.channel, "申し訳ございません。アドレスがみつけられませんでした")
            return

        sant = False
        address = params[1]
        if (address.startswith("t")):
            if (len(address) == 34):
                res = res_cmd('~/selnd -testnet getbalance')
                balance = float(str(res).strip("b'").strip("\\n"))
                if (balance < 1000000):
                    await client.send_message(message.channel, "お暇を頂きます。長い間おせわになりました")
                else:
                    sendcommand = '~/selnd -testnet sendtoaddress ' + address + ' ' + str(AMOUNT)
                    res_cmd(sendcommand)
                    sant = True
                    await client.send_message(message.channel, "ご指示通り送金いたしました")
        if (not sant):
            await client.send_message(message.channel, "大変申し上げにくいのですがアドレスが不正ではございませんか・・？")
    else:
            await client.send_message(message.channel, "コマンドがあっておりますか・・？")

def res_cmd(cmd):
  return subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True).communicate()[0]