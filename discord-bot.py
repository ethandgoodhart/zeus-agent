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
import json
import random
import string

logger = logging.getLogger(__name__)

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1345727973550067802

class LocalUserAuth:
    def __init__(self, config_file="local_auth.json"):
        self.config_file = config_file
        self.authorized_id = None
        self.auth_code = None
        self.is_waiting_for_auth = False
        self.load_config()
    
    def load_config(self):
        """Load authorized user ID from config file if it exists"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.authorized_id = config.get('authorized_id')
                    return True
        except Exception as e:
            print(f"Error loading config: {e}")
        return False
    
    def save_config(self):
        """Save authorized user ID to config file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump({'authorized_id': self.authorized_id}, f)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def generate_auth_code(self):
        """Generate a random 6-digit auth code"""
        self.auth_code = ''.join(random.choices(string.digits, k=6))
        self.is_waiting_for_auth = True
        return self.auth_code
    
    def verify_auth_code(self, user_id, code):
        """Verify auth code and authorize user if correct"""
        if self.is_waiting_for_auth and code == self.auth_code:
            self.authorized_id = str(user_id)
            self.is_waiting_for_auth = False
            self.save_config()
            return True
        return False
    
    def is_authorized(self, user_id):
        """Check if a user is authorized"""
        return str(user_id) == self.authorized_id

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
auth = LocalUserAuth()  # Create auth instance

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
            # Check if user is authorized
            if not auth.is_authorized(str(interaction.user.id)):
                await interaction.response.send_message("❌ You are not authorized to control this bot.", ephemeral=True)
                return
                
            await interaction.response.defer()
            logger.info(f"Processing button click for: {message}")
            response = agent.run(message, debug=False, speak=False)
            await interaction.followup.send(response, ephemeral=False)
        return callback

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    # If no authorized user is set, generate auth code
    if not auth.authorized_id:
        auth_code = auth.generate_auth_code()
        print("\n" + "="*50)
        print(f"⚠️ NO AUTHORIZED USER FOUND ⚠️")
        print(f"One-time authentication code: {auth_code}")
        print("Send this code to the bot with !auth [code]")
        print("="*50 + "\n")
    else:
        print(f"✅ Authorized user ID: {auth.authorized_id}")
        
        # Optionally notify the authorized user
        try:
            user = await bot.fetch_user(int(auth.authorized_id))
            await user.send("I'm now running on your computer and will only accept commands from you.")
        except Exception as e:
            print(f"Could not notify authorized user: {e}")

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

@bot.command(name="auth")
async def auth_command(ctx, code: str = None):
    if not code:
        await ctx.send("Please provide the authentication code: !auth [code]")
        return
        
    if auth.verify_auth_code(ctx.author.id, code):
        await ctx.send(f"✅ Authentication successful! You ({ctx.author.name}) are now the authorized user.")
        print(f"User authorized: {ctx.author.name} (ID: {ctx.author.id})")
    else:
        # Don't tell unauthorized users that they're unauthorized
        await ctx.send("❌ Invalid authentication code.")

async def listen_for_commands():
    """Continuously listens for speech and processes commands in parallel."""
    while True:

        command = await asyncio.to_thread(speech.get_speech_command)  # Run speech recognition in a separate thread

        if command:
            # Clean up the command by removing leading commas and spaces
            command = command.lstrip(', ')
            
            print(f"✅ Running command: {command}")
            response = await asyncio.to_thread(agent.run, command, False, False)
            print(f"✅ Task completed: {response}")
            
            # Send the response to Discord channel
            channel = bot.get_channel(CHANNEL_ID)
            if channel:
                await channel.send(f"Voice command: '{command}'\n\nResults:\n{response}")
            
        else:
            print("🔇 Restarting listener...")

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
    
    # Check if user is authorized
    if not auth.is_authorized(str(message.author.id)):
        await message.reply("❌ You are not authorized to control this bot.")
        return
    
    logger.info(f"Processing message from {message.author}: {message.content}")
    response = agent.run(message.content, debug=False, speak=False)

    # Send the response back to the channel
    await message.reply(response)

bot.run(TOKEN)