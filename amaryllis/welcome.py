import discord
import asyncio
import random

msg_welcome=[
    "いらっしゃいませ @{} 様",
    "ようこそ @{} 様",
        ]

msg_remove=[
    "またいらしてください @{} 様",
    "いってらっしゃいませ @{} 様",
        ]


def on_ready():
    pass
    return

async def on_member_join_inner(client, member, channel_id):
    chObj = client.get_channel(channel_id)
    await client.send_message(chObj, random.choice(msg_welcome).format(member))

async def on_member_remove_inner(client, member, channel_id):
    chObj = client.get_channel(channel_id)
    await client.send_message(chObj, random.choice(msg_remove).format(member))



