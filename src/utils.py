import openai
import sqlite3
import os
import sys
import json

def load_config(config_path='config.json'):
    config = {}
    with open(config_path, 'r') as config_file:
        conf = json.load(config_file)
        # print(f"Config: {json.dumps(conf)}")
    config['id_to_name'] = {int(k): v for k, v in conf['id_to_name'].items()}
    config['allowed_servers'] = [int(server) for server in conf.get('allowed_servers', [])]
    config['allowed_users'] = [int(user) for user in conf.get('allowed_users', [])]
    return config

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

import sqlite3

def estimate_tokens(expanded_messages):
    total_characters = 0
    for msg_tuple in expanded_messages:
        for msg in msg_tuple:
            # print(f"Processing message: {msg}")
            try:
                user = msg[1]
                date = msg[2][:10]
                contents = msg[3]
                formatted_msg = f"User: {user}, Date: {date}, Contents: {contents}"
                msg_length = len(formatted_msg)
                total_characters += msg_length
            except IndexError as e:
                print(f"Error accessing elements in message: {msg} - {e}")
                raise
    estimated_tokens = total_characters / 4
    return estimated_tokens

def trim_messages(messages, max_tokens):
    while estimate_tokens(messages) > max_tokens:
        # Reduce the list by 5%
        reduction_count = max(1, int(len(messages) * 0.05))
        messages = messages[:-reduction_count]
    return messages

def query_messages_by_timestamp_range(db_path, start_timestamp, end_timestamp):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = f'''
    SELECT message_id, name, timestamp, contents, attachments link
    FROM messages
    WHERE timestamp >= ? AND timestamp <= ?
    ORDER BY timestamp
    '''

    cursor.execute(query, (start_timestamp, end_timestamp))
    results = cursor.fetchall()

    conn.close()
    return results

