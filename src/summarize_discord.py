import sqlite3
import os
import argparse
import openai
from datetime import datetime, timedelta
from src.utils import initialize_openai

DATABASE_PATH = 'database/messages.db'

def fetch_messages(cursor, start_date, end_date):
    query = '''
    SELECT message_id, name, timestamp, contents
    FROM messages
    WHERE timestamp BETWEEN ? AND ?
    ORDER BY timestamp ASC
    '''
    cursor.execute(query, (start_date, end_date))
    return cursor.fetchall()

def get_first_date(cursor):
    query = '''
    SELECT MIN(timestamp) FROM messages
    '''
    cursor.execute(query)
    result = cursor.fetchone()
    return result[0] if result else None

def message_link_for(message_id: str):
    return f'https://discord.com/channels/@me/383761744830529537/{message_id}'

def chunk_messages(messages, chunk_size):
    chunked = []
    current_chunk = []
    current_length = 0
    total_length = 0

    for msg in messages:
        formatted_msg = f"User: {msg[1]}, Date: {msg[2][:10]}, Contents: {msg[3]}"
        msg_length = len(formatted_msg)  # length of the formatted message

        if current_length + msg_length > chunk_size:
            chunked.append(current_chunk)
            print(f"Chunk {len(chunked)}: {len(current_chunk)} messages, estimated size {current_length}")
            current_chunk = [msg]
            current_length = msg_length
        else:
            current_chunk.append(msg)
            current_length += msg_length

        total_length += msg_length

    if current_chunk:
        chunked.append(current_chunk)
        print(f"Chunk {len(chunked)}: {len(current_chunk)} messages, estimated size {current_length}")

    print(f"Total chunks: {len(chunked)}")
    print(f"Total estimated message text length: {total_length}")

    return chunked


def summarize_conversation(client, messages, start_date, end_date):
    conversations = "\n\n".join(
        [
            "\n".join(
                [
                    f"User: {msg[1]}, Date: {msg[2][:10]}, Contents: {msg[3]}"
                    for msg in msg_tuple
                ]
            )
            for msg_tuple in messages
        ]
    )

    # print(f"First message or so: {conversations[:150]}")

    prompt = (
        f"Given the messages between two friends from {start_date} to {end_date}, "
        "provide a factual and succinct summary of the main events and repeated topics discussed during this period. Start with '# <month> <year>'. "
        "Focus on concrete events, notable quotes, and specific recurring topics. Avoid general or flowery descriptions and transitional phrases. "
        "Describe the whole period as a *single* paragraph, only use two if it's very difficult to summarize. Never use more than two"
        "Only use names when necessary for clarity. "
        "Use proper Discord markdown formatting in the reply.\n\n Conversations follow:"
        f"{conversations}"
    )

    print(f"Actual prompt length: {len(prompt)}")
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=2048
    )
    
    summary = response.choices[0].message.content.strip()
    return summary

def save_to_file(summary_text, start_date, end_date, window_size):
    # Convert datetime objects to string in YYYY-MM-DD format
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    # Create summaries directory if it doesn't exist
    if not os.path.exists('summaries'):
        os.makedirs('summaries')

   
    # Generate base file name
    base_file_name = f"summaries/summary_{start_date_str}_{end_date_str}_window-{window_size}.txt"
    file_name = base_file_name
    
    # Append suffix if file already exists
    counter = 2
    while os.path.exists(file_name):
        file_name = f"{base_file_name[:-4]}-{counter}.txt"
        counter += 1

    # Write the summary text to the file
    with open(file_name, 'w') as file:
        file.write(summary_text)

    return file_name

def main(start_date, num_days, max_chunks, window):
    client = initialize_openai()
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    if start_date is None:
        start_date = get_first_date(cursor)
        if not start_date:
            print("No messages found in the database.")
            return
        start_date = start_date.split(' ')[0]  # Extract the date part

    current_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = current_date + timedelta(days=num_days)

    chunks_processed = 0

    messages = fetch_messages(cursor, current_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

    if not messages:
        return

    chunked_messages = chunk_messages(messages, window)

    for chunk in chunked_messages:
        chunk_start_date = datetime.strptime(chunk[0][2], '%Y-%m-%d %H:%M:%S')
        chunk_end_date = datetime.strptime(chunk[-1][2], '%Y-%m-%d %H:%M:%S')
        print(f"Processing chunk from {chunk_start_date} to {chunk_end_date}...")
        print(f"First message in chunk: {chunk[0]}")
        print(f"Last message in chunk: {chunk[-1]}")
        summary = summarize_conversation(client, [chunk], chunk_start_date, chunk_end_date)
        time_prefix = f"* Start of time period: {message_link_for(chunk[0][0])}\n* End of time period: {message_link_for(chunk[-1][0])}"
        summary_text = f"{time_prefix}\n{summary}\n"
        summary_text = summary
        file_name = save_to_file(summary_text, chunk_start_date, chunk_end_date, window)
        print(summary_text)

        # Fallback for if we go too far, unlikely
        chunks_processed += 1
        if chunks_processed >= max_chunks:
            print(f"######### Warning!!! We Exceeded the max chunk count and ended early at {chunk_end_date}")
            return

    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Summarize Discord DM conversations.')
    parser.add_argument('--start-date', type=str, default=None, help='Start date for summarization in format YYYY-MM-DD')
    parser.add_argument('--max-chunks', type=int, default=10, help='Maximum number of chunks to process')
    parser.add_argument('--window', type=int, default=120000, help='Context window size')
    parser.add_argument('--days', type=int, default=14, help="Number of days (default 14)")

    args = parser.parse_args()

    main(args.start_date, args.days, args.max_chunks, args.window)

