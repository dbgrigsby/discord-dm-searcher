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

# Split text at last newline
def split_text(text, max_length=1900):
    chunks = []
    while len(text) > max_length:
        split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            split_pos = max_length
        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip('\n')
    chunks.append(text)
    return chunks

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

    if len(summary) > 1900:
        chunks = split_text(summary)
        for chunk in chunks:
            message = await interaction.followup.send(chunk)
            await message.edit(suppress=True)
    else:
        message = await interaction.followup.send(summary)
        await message.edit(suppress=True)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()

token = get_discord_token()
if token:
    bot.run(token)
else:
    print("Discord token not found. Please set it in DISCORD_TOKEN.txt or as an environment variable")