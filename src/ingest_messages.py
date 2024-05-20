import json
import sqlite3
import argparse
from src.utils import load_config
import os
from tqdm import tqdm


id_to_name = load_config()['id_to_name']

# Function to create the database
def create_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table schema
    cursor.execute('''
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            name TEXT,
            timestamp TEXT,
            contents TEXT,
            attachments TEXT,
            link TEXT
        )
    ''')
    cursor.execute('CREATE INDEX idx_name ON messages (name)')
    cursor.execute('CREATE INDEX idx_timestamp ON messages (timestamp)')
    cursor.execute('CREATE INDEX idx_message_id ON messages (message_id)')
    
    conn.commit()
    conn.close()

# Function to convert mentions
def convert_mentions(contents):
    for user_id, name in id_to_name.items():
        contents = contents.replace(f'<@{user_id}>', f'@{name}')
    return contents

# Function to insert data into the database
def insert_data(db_path, data_path):
    with open(data_path, 'r') as f:
        data = json.load(f)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Determine the name from the filename
    name = os.path.splitext(os.path.basename(data_path))[0]
    
    # The global channel ID (fixed for all messages)
    channel_id = 383761744830529537
    
    for message in tqdm(data, desc="Inserting messages"):
        message_id = message['ID']
        timestamp = message['Timestamp']
        contents = convert_mentions(message['Contents'])
        attachments = message['Attachments']
        link = f'https://discord.com/channels/@me/{channel_id}/{message_id}'
        
        cursor.execute('''
            INSERT INTO messages (message_id, name, timestamp, contents, attachments, link)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (message_id, name, timestamp, contents, attachments, link))
    
    conn.commit()
    
    # Print database stats
    cursor.execute('SELECT COUNT(*) FROM messages')
    row_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT name, COUNT(*) FROM messages GROUP BY name')
    user_counts = cursor.fetchall()
    
    print(f"\nDatabase Stats:\nTotal messages: {row_count}")
    for user, count in user_counts:
        print(f"Messages from {user}: {count}")
    
    conn.close()

# Main function
def main():
    parser = argparse.ArgumentParser(description="Ingest message data into SQLite database")
    parser.add_argument('data_path', type=str, help='Relative path to the message data JSON file')
    
    args = parser.parse_args()
    
    # Ensure database directory exists
    if not os.path.exists('database'):
        os.makedirs('database')
    
    db_path = 'database/messages.db'
    
    # Remove the existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
    
    create_database(db_path)
    insert_data(db_path, args.data_path)

if __name__ == "__main__":
    main()

