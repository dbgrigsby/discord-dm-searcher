import discord
from discord import app_commands
from discord.ext import commands
import os

from src.search_messages import process_query
from src.utils import load_config

config = load_config()
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

def get_discord_token():
    if os.path.isfile('DISCORD_TOKEN.txt'):
        with open('DISCORD_TOKEN.txt', 'r') as file:
            return file.read().strip()
    else:
        return os.getenv('DISCORD_TOKEN')

@bot.tree.command(name="search", description="Search Discord DMs")
@app_commands.describe(
    search_term="Search term",
    keyword_override="Specific keywords to search",
    send_all_matches="Send all matches to OpenAI (may crash with too many matches)"
)
async def search(interaction: discord.Interaction, search_term: str, keyword_override: str = None, send_all_matches: bool = False):
    allowed_servers = config['allowed_servers']
    allowed_users = config['allowed_users']

    if interaction.guild_id not in allowed_servers or interaction.user.id not in allowed_users:
        await interaction.response.send_message("You aren't allowed to use this :)")
        return

    await interaction.response.send_message(f"Processing your request to find '{search_term}', please wait about 30 seconds...")

    summary = process_query(search_term, keyword_override, send_all_matches)

    # Split the summary into chunks if it exceeds 2000 characters
    if len(summary) > 2000:
        chunks = [summary[i:i+2000] for i in range(0, len(summary), 2000)]
        for chunk in chunks:
            await interaction.followup.send(chunk)
    else:
        await interaction.followup.send(summary)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()

token = get_discord_token()
if token:
    bot.run(token)
else:
    print("Discord token not found. Please set it in DISCORD_TOKEN.txt or as an environment variable")