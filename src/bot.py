import discord
from discord import app_commands
from discord.ext import commands
import os

from src.search_messages import process_query
from src.utils import load_config
from src.summarize_discord import main as summarize_main

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
    keyword_override="A comma separated list of specific keywords to search. Don't use spaces next to the commas",
    send_all_matches="Send all matches to OpenAI (may crash with too many matches)"
)
async def search(interaction: discord.Interaction, search_term: str, keyword_override: str = None, send_all_matches: bool = False):
    allowed_servers = config['allowed_servers']
    allowed_users = config['allowed_users']

    if interaction.guild_id not in allowed_servers or interaction.user.id not in allowed_users:
        await interaction.response.send_message("You aren't allowed to use this :)")
        return

    await interaction.response.send_message(f"Working on answering '{search_term}', please wait about 30 seconds...")

    try:
        summary = process_query(search_term, keyword_override, send_all_matches)

        if len(summary) > 1900:
            chunks = split_text(summary)
            for chunk in chunks:
                message = await interaction.followup.send(chunk)
        else:
            message = await interaction.followup.send(summary)
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")

# Create the summarize slash command
@bot.tree.command(name="summarize", description="Summarize Discord DM conversations")
@app_commands.describe(
    start_date="Start date for summarization in format YYYY-MM-DD",
    num_days="Number of days to summarize (default 30)",
)
async def summarize(interaction: discord.Interaction, start_date: str = None, num_days: int = 30):
    allowed_servers = config['allowed_servers']
    allowed_users = config['allowed_users']

    if interaction.guild_id not in allowed_servers or interaction.user.id not in allowed_users:
        await interaction.response.send_message("You aren't allowed to use this :)")
        return

    if num_days > 61:
        await interaction.response.send_message("The 'days' parameter cannot be greater than 61.")
        return

    await interaction.response.send_message(f"Summarizing conversations from '{start_date}' for {num_days} days, please wait about 30 seconds")

    try:
        summary = summarize_main(start_date, num_days, max_chunks=10, window=120000)
        if len(summary) > 1900:
            chunks = split_text(summary)
            for chunk in chunks:
                message = await interaction.followup.send(chunk)
        else:
            message = await interaction.followup.send(summary)
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()

def main():
    token = get_discord_token()
    if token:
        bot.run(token)
    else:
        print("Discord token not found. Please set it in DISCORD_TOKEN.txt or as an environment variable")

if __name__ == '__main__':
    main()