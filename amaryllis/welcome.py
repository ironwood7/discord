import discord
import random

msg_welcome=[
    "いらっしゃいませ{}様",
    "ようこそ{}様",
        ]

msg_remove=[
    "またいらしてください{}様",
    "いってらっしゃいませ{}様",
        ]


async def on_ready_inner():
    # print('welcome start')

async def on_member_join_inner(client, member, channel):
    await client.send_message(channel, random.choice(msg_remove).format(member))

async def on_member_remove_inner(client, member, channel):
    await client.send_message(channel, random.choice(msg_remove).format(member))

async def on_message_inner(client, message):
    # pass
    return


