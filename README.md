# discord-dm-searcher
OpenAI Utility for indexing your DMs with a friend from a Discord Data package, and making them searchable via a Chat Interface

## Example Usage
* Acquire the messages from Discord:
  * First, have you and your friend both download your Discord Data package. Request this in Settings -> Privacy and Safety -> Request All of My Data
  * Wait like a week for it to arrive
  * Download and unzip the file. Under `messages`, open `index.json`. Ctrl+F for the discord username of your friend (the loweercase unique username, not Display Name), and copy the number of the DM with them which will be right before the name
  * Open the folder in messages called `cNUMBER` where NUMBER is the number you found
  * Copy the file called `messages.json` into this repository. Name it "YourNameHere.json" to keep it distinct
  * Have your friend repeat the previous steps, but finding their file of messages from their perspective, using your username
* Set up the repository (Linux or WSL for Windows or MacOS)
  * Run `make virtualenv_run`
  * Copy `config.json.example` to `config.json` (`cp config.json.example config.json`). Edit this file to have the name you want your bot to refer to your friend as next to their user ID (right click their name -> copy ID). Repeat for yourself, and save the file
  * Set up your OpenAI key. Make an account at https://platform.openai.com/api-keys, create an org/project and a key that has at the least:
    * Write Access to "Model Capabilities" 
    * On the Project -> Limits page, give it access to `gpt4-o` (Used for everything) and `text-embedding-3-large` (used for searching). 
    * Note your rate limits. At the start you're limited to a 30k token limit, so you'll need to pass --window <some number below that> for it to work.
* Import the data: Run  
  * `virtualenv_run/bin/python -m src.ingest_messages YOUR_MESSAGES.JSON YOUR_FRIENDS_MESSAGES.json`
  * All the data will be imported, it will print how many messages both you and your friend sent
* Now you're set up, you can either search for messages or summarize. 
* To Summarize: `virtualenv_run/bin/python -m src.summarize_discord --start-date 2020-04-15 --days 15`
* To Search: `virtualenv/run/bin/python -m src.search_messages "What are the two friends opinion about programming?"`

