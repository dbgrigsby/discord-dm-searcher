import discord
from discord import app_commands
from discord.ext import commands
import os

from src.search_messages import process_query

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
async def search(interaction: discord.Interaction, search_term: str, no_cost: bool = False, keyword_override: str = None, send_all_matches: bool = False):
    await interaction.response.send_message("Processing your request to find {search_term},  please wait...")

    summary = process_query(search_term, keyword_override, send_all_matches)
    
    await interaction.followup.send(summary)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()

token = get_discord_token()
if token:
    bot.run(token)
else:
    print("Discord token not found. Please set it in DISCORD_TOKEN.txt or as an environment variable.")