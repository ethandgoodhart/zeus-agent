import os
import discord
from discord.ext import commands
from discord.ui import View, Button
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1345727973550067802

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

class AppView(View):
    def __init__(self):
        super().__init__()

        apps = [
            ("YouTube Music", "Play a chill playlist for coding!", discord.ButtonStyle.primary),
            ("Reminders", "Set a reminder tomorrow at 9:00 AM for a dentist appointment", discord.ButtonStyle.success),
            ("Messages", "Give me a summary of my unread messages", discord.ButtonStyle.secondary),
            ("Finder", "Create a python file called flow.py in my documents folder", discord.ButtonStyle.danger)
        ]

        for name, description, color in apps:
            button = Button(label=name, style=color)
            button.callback = self.create_callback(description)
            self.add_item(button)

    def create_callback(self, message):
        async def callback(interaction: discord.Interaction):
            await interaction.response.send_message(message, ephemeral=False)
        return callback

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="Use one of our prompts below or write your own",
            color=0x1DB954
        )
        embed.add_field(name="YouTube Music", value="Play a chill playlist for coding!", inline=False)
        embed.add_field(name="Reminders", value="Set a reminder tomorrow at 9:00 AM for a dentist appointment", inline=False)
        embed.add_field(name="Messages", value="Give me a summary of my unread messages", inline=False)
        embed.add_field(name="Finder", value="Create a python file called flow.py in my documents folder", inline=False)

        embed.set_thumbnail(url="https://i.ibb.co/4g8QJ7z7/Adobe-Express-file-1-1.png")  

        await channel.send(embed=embed, view=AppView())
        print(f"📨 Sent message in #{channel.name}!")
    else:
        print("❌ ERROR: Could not find the channel.")

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

    # Process the message with the agent you wrote
    # Open up the agent.py file to customize the agent
    logger.info(f"Processing message from {message.author}: {message.content}")
    response = await agent.run(message)

    # Send the response back to the channel
    await message.reply(response)


bot.run(TOKEN)