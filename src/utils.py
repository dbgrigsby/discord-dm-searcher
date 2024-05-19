import openai
import os
import sys

def get_openai_key():
    openai_key = os.getenv("OPENAI_KEY")
    if not openai_key:
        try:
            with open("OPENAI_KEY.txt", "r") as file:
                openai_key = file.read().strip()
        except FileNotFoundError:
            pass
    return openai_key

def initialize_openai():
    openai_key = get_openai_key()
    if not openai_key:
        print("Error: The OPENAI_KEY environment variable is not set and OPENAI_KEY.txt is missing.")
        print("Please set the key using 'export OPENAI_KEY=your_openai_key_here' or create an OPENAI_KEY.txt file.")
        sys.exit(1)
    client = openai.OpenAI(api_key=openai_key)
    return client

