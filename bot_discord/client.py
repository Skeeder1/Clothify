#!/usr/bin/env python3

import os
import discord
from pathlib import Path

from dotenv import load_dotenv


# Charger les variables d'environnement
load_dotenv(Path(__file__).parent.parent / ".env")

bot_token = os.getenv("bot_token")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.lower().startswith("bonjour bot"):
        await message.channel.send("Hello! I am Clothify Bot.")

client.run(token=bot_token)