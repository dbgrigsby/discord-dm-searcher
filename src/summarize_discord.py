import sqlite3
import argparse
import openai
from datetime import datetime, timedelta
from src.utils import initialize_openai

DATABASE_PATH = 'database/messages.db'
MAX_CONTEXT_WINDOW = 128000  # 128k tokens
MAX_CONTEXT_WINDOW = 29500  # <30k tokens for 1 week

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

def chunk_messages(messages, chunk_size):
    chunked = []
    current_chunk = []
    current_length = 0

    for msg in messages:
        msg_length = len(msg[3])  # length of the message contents
        if current_length + msg_length > chunk_size:
            chunked.append(current_chunk)
            current_chunk = [msg]
            current_length = msg_length
        else:
            current_chunk.append(msg)
            current_length += msg_length

    if current_chunk:
        chunked.append(current_chunk)

    return chunked

def summarize_conversation(client, messages, start_date, end_date):
    conversations = "\n\n".join(["\n".join([f"User: {msg[1]}\nTimestamp: {msg[2]}\nContents: {msg[3]}\nmessage_id: {msg[0]}" for msg in msgs]) for msgs in messages])
    prompt = (
        f"Given the messages between two friends from {start_date} to {end_date}, "
        "provide a summary of the main things that went on in the time period. With one large paragraph overall for the time period. Focus on important things that occured, as well as repeat occurences"
        "Include year, month day only when necessary, generally describe the whole period as a single unit, although maintain sequentiality. But always include user names for clarity. Never mention hours/minutes/seconds unless relevant to when a conversation started.:\n\n"
        f"{conversations}\n\n"
    )
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000
    )
    
    summary = response.choices[0].message.content.strip()
    return summary

def main(start_date, max_chunks):
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
    end_date = current_date + timedelta(days=14)  # initially set to 2 weeks
    max_days = 14  # default chunk size in days

    chunks_processed = 0

    while chunks_processed < max_chunks:
        messages = fetch_messages(cursor, current_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

        if not messages:
            break

        chunked_messages = chunk_messages(messages, MAX_CONTEXT_WINDOW)
        for chunk in chunked_messages:
            chunk_start_date = chunk[0][2]
            chunk_end_date = chunk[-1][2]
            print(f"Processing chunk from {chunk_start_date} to {chunk_end_date}...")
            print(f"First message in chunk: {chunk[0]}")
            print(f"Last message in chunk: {chunk[-1]}")
            summary = summarize_conversation(client, [chunk], chunk_start_date, chunk_end_date)
            print(f"Summary for period {chunk_start_date} to {chunk_end_date}:\n{summary}\n")
            chunks_processed += 1
            if chunks_processed >= max_chunks:
                break

        current_date = end_date
        end_date = current_date + timedelta(days=max_days)
        if current_date >= datetime.now():
            break

    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Summarize Discord DM conversations.')
    parser.add_argument('--start-date', type=str, default=None, help='Start date for summarization in format YYYY-MM-DD')
    parser.add_argument('--max-chunks', type=int, default=1, help='Maximum number of chunks to process')
    args = parser.parse_args()

    main(args.start_date, args.max_chunks)

