import os
import discord
import logging
import sys
from pathlib import Path
from discord.ext import commands
from discord.ui import View, Button
from dotenv import load_dotenv
import agent
import utils.speech as speech
import asyncio

logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1345727973550067802

AUTHORIZED_USER_ID = input("Enter your Discord ID so we can ensure that only you can control your screen(instructions below):\n"
                           "1️⃣ Open Discord\n"
                           "2️⃣ Click on 'User Settings' (⚙️ icon)\n"
                           "3️⃣ Go to 'Advanced' and enable 'Developer Mode'\n"
                           "4️⃣ Right-click your server profile and select 'Copy ID'\n"
                           "5️⃣ Paste it here: ").strip()

try:
    AUTHORIZED_USER_ID = int(AUTHORIZED_USER_ID)  # Convert to integer
except ValueError:
    print("❌ Invalid Discord ID! Please enter a numeric ID.")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

class AppView(View):
    def __init__(self):
        super().__init__()

        apps = [
            ("YouTube Music", "Play a chill playlist for coding!", discord.ButtonStyle.primary),
            ("Calendar", "Set a dentist appointment for Thursday at 9:00 AM", discord.ButtonStyle.success),
            ("Messages", "Send a text message to the CS 153 group chat saying look at this test!", discord.ButtonStyle.secondary),
            ("Finder", "Create a folder called testing in my documents folder", discord.ButtonStyle.danger)
        ]

        for name, description, color in apps:
            button = Button(label=name, style=color)
            button.callback = self.create_callback(description)
            self.add_item(button)

    def create_callback(self, message):
        async def callback(interaction: discord.Interaction):
            await interaction.response.defer()
            logger.info(f"Processing button click for: {message}")
            response = agent.run(message, debug=False, speak=False)
            await interaction.followup.send(response, ephemeral=False)
        return callback

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="Welcome to FlowAgent! Tell us what to do, sit back, and see the magic happen. Note that you can move your mouse to the top left of the screen as a failsafe. Pick one of our prompts or create your own.",
            color=0x1DB954
        )
        embed.add_field(name="YouTube Music", value="Play a chill playlist for coding!", inline=False)
        embed.add_field(name="Reminders", value="Set a dentist appointment for Thursday at 9:00 AM", inline=False)
        embed.add_field(name="Messages", value="Send a text message to the CS 153 group chat saying look at this test!", inline=False)
        embed.add_field(name="Finder", value="Create a folder called testing in my documents folder", inline=False)

        embed.set_thumbnail(url="https://i.ibb.co/4g8QJ7z7/Adobe-Express-file-1-1.png")  

        await channel.send(embed=embed, view=AppView())
        print(f"📨 Sent message in #{channel.name}!")
    else:
        print("❌ ERROR: Could not find the channel.")
    
    bot.loop.create_task(listen_for_commands())

async def listen_for_commands():
    """Continuously listens for speech and processes commands in parallel."""
    while True:
        print("🎤 Listening for 'Hey Flow'...")

        command = await asyncio.to_thread(speech.get_speech_command)  # Run speech recognition in a separate thread

        if command:
            print(f"✅ Running command: {command}")
            response = await asyncio.to_thread(agent.run, command, False, False)
            print(f"✅ Task completed: {response}")
            
        else:
            print("🔇 No valid command detected. Restarting listener...")
    

@bot.event
async def on_message(message: discord.Message):
    """
    Called when a message is sent in any channel the bot can see.

    https://discordpy.readthedocs.io/en/latest/api.html#discord.on_message
    """
    # Don't delete this line! It's necessary for the bot to process commands.
    await bot.process_commands(message)

    # Ignore messages from self or other bots to prevent infinite loops.
    if message.author.bot or message.content.startswith("!"):
        return
    
    # check if user is the correct one prevent others from controlling your screen
    if message.author.id != AUTHORIZED_USER_ID:
        await message.reply("❌ You are not authorized to control this bot.")
        return
    
    logger.info(f"Processing message from {message.author}: {message.content}")
    response = agent.run(message.content, debug=False, speak=False)

    # Send the response back to the channel
    await message.reply(response)


bot.run(TOKEN)