import argparse
from time import sleep
import os
import traceback
import sqlite3
import json
import math
from datetime import datetime, timedelta
from src.utils import initialize_openai, query_messages_by_timestamp_range, trim_messages
from src.utils import load_config
from src.utils import estimate_tokens


client = initialize_openai()
conf = load_config()
names = sorted(list(load_config()['id_to_name'].values()))
# print(f"Names: {names}")

DATABASE_PATH = 'database/messages.db'

def get_search_keywords(query):
    prompt = f"""Given the query: \'{query}\', return ONLY A JSON blob of keywords to search for specific chat history between two friends named {names[0]} and {names[1]}. This will be fed into a script to query from all the available Discord history for their DM, so pick messages based on how likely their nearby messages are have relevant content.  Sort the ~50 keywords by most likely to have correct hits that are not false positives.
    Focus on phrases and expressions that people might use in the context of the query. Exclude common words, and the names of the two friends. ONLY RESPOND WITH JSON in the form {{'keywords': ['keyword1', 'keyword2', 'etc']}}
    """
    print("Starting OpenAI call to get search keywords...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
    )
    print("Finished OpenAI call to get search keywords.")
    raw_content = response.choices[0].message.content.strip()
    if raw_content.startswith("```json"):
        raw_content = raw_content[7:-3].strip()
    keywords = json.loads(raw_content)
    print("OpenAI response JSON for search keywords:\n", json.dumps(keywords, indent=2))
    return keywords


def search_index(keywords):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    escaped_keywords = [keyword.replace("'", "''") for keyword in keywords]
    keyword_query = " OR ".join([f"contents LIKE '%{keyword}%'" for keyword in escaped_keywords])

    query = f'''
    SELECT message_id, name, timestamp, contents, attachments, link
    FROM messages
    WHERE {keyword_query}
    '''

    try:
        cursor.execute(query)
        results = cursor.fetchall()
    except Exception as e:
        traceback.print_exc()
        print(f"Failed on query {query}")
        raise e

    conn.close()
    return results

def get_message_embeddings(messages):
    max_tokens = 900000
    token_count = 0
    truncated_messages = []

    try:
        # Extract the text from the messages
        for msg in messages:
            text = msg[3]
            words = text.split()
            word_count = len(words)
            if token_count + word_count > max_tokens:
                break
            truncated_messages.append(text)
            token_count += word_count

        total_characters = sum(len(text) for text in truncated_messages)
        total_words = sum(len(text.split()) for text in truncated_messages)
        print(f"Submitting {len(truncated_messages)} messages to `text-embedding-3-large`, with a total length of {total_characters} characters and {total_words} words.")

        response = client.embeddings.create(input=truncated_messages, model="text-embedding-3-large")
        embeddings = [item.embedding for item in response.data]
        
    except Exception as e:
        traceback.print_exc()
        print(f"failed on calculating embeddings for {len(messages)} messages")
        raise e

    return embeddings

def get_query_embedding(query):
    response = client.embeddings.create(input=[query], model="text-embedding-3-large")
    embedding = response.data[0].embedding
    return embedding

def calculate_similarity(embeddings, query_embedding):
    def dot_product(v1, v2):
        return sum(x*y for x, y in zip(v1, v2))
    similarities = [dot_product(embed, query_embedding) for embed in embeddings]
    return similarities

def select_relevant_messages(search_term, messages):
    nmessage_texts = [msg[3] for msg in messages]
    message_ids = [msg[0] for msg in messages]
    messages_data = [{"id": msg[0], "author": msg[1], "text": msg[3]} for msg in messages]
    prompt = f"""Given the search term: '{search_term}', select the most relevant messages from the following list. Up to 30 if they do seem relevant. 
    The messages are between two friends named {names[0]} and {names[1]}. Return ONLY the IDs of the selected messages in JSON format:\n\n{json.dumps(messages_data, indent=2)}\n\nONLY RESPOND WITH THE MESSAGE IDs IN JSON."""
    print("Starting OpenAI call to select relevant messages...")
    # print(f"Prompt for selecting relevant messages:\n{prompt}")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=2000
    )
    print("Finished OpenAI call to select relevant messages.")
    raw_content = response.choices[0].message.content.strip()
    if raw_content.startswith("```json"):
        raw_content = raw_content[7:-3].strip()
    try:
        selected_message_ids = json.loads(raw_content)
        # print(f"OpenAI response JSON for {len(selected_message_ids)} relevant messages:\n", json.dumps(selected_message_ids, indent=2))
        return selected_message_ids
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        print("Raw content that caused JSONDecodeError:\n", raw_content)
        return []


def contextual_expansion(messages, minutes_nearby=60):
    expanded_messages = []
    for message in messages:
        message_id, timestamp = message[0], message[2]
        timestamp_dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        start_timestamp = (timestamp_dt - timedelta(minutes=minutes_nearby)).strftime("%Y-%m-%d %H:%M:%S")
        end_timestamp = (timestamp_dt + timedelta(minutes=minutes_nearby)).strftime("%Y-%m-%d %H:%M:%S")
        # print(f"Start timestamp is {start_timestamp} , end timestamp is {end_timestamp}")
        context = query_messages_by_timestamp_range(DATABASE_PATH, start_timestamp, end_timestamp)
        expanded_messages.append(context)
    return expanded_messages

def summarize_conversation(original_query, expanded_messages):
    # print(f"First expanded message: {expanded_messages[0]}")
    # conversations = "\n\n".join(["\n".join([f"User: {msg[1]}\nTimestamp: {msg[2]}\nContents: {msg[3]}\nmessage_id: {msg[0]}" for msg in messages]) for messages in expanded_messages])
    total_tokens = 0
    conversations = ""
    average_word_length = 4.7  # Assuming average word length in English
    
    for msg_tuple in expanded_messages:
        group_messages = "\n".join([f"User: {msg[1]}, Date: {msg[2][:10]}, Contents: {msg[3]}" for msg in msg_tuple])
    
        num_words = len(group_messages.split())
        estimated_tokens = num_words * average_word_length + 100
    
        if total_tokens + estimated_tokens > 124000:
            break
    
        conversations += group_messages + "\n\n"
        total_tokens += estimated_tokens
    

    # print(f"First message or so: {conversations[:150]}")
    prompt = f"Given the original query: '{original_query}', and the following messages between two friends {names[0]} and {names[1]}, provide an answer to the search term, summarizing at least 1 but not more than 5 occurences of the search term. Make sure to provide a paragraph at the top summarizing, especially if the original query asked for it, before the links. Include links. Please return one discord link for each example to the most relevant message, considering who sent the message and what the initial query says, not hyperlinked, just raw links. Summarize the conversation's main point, don't just focus on the best message. Avoid flowery text in your descriptions. Quote messages from the conversations if they are especially funny or poignant.  Links are formatted as https://discord.com/channels/@me/383761744830529537/message_id , make sure that 383.../ is always there, or the link will not work. Do NOT use markdown formatted EVER for the message links! No parentheses or brackets around them, ever.  Include a year, month day and time of day description for each result. Here are the messages:\n:\n\n{conversations}\n\n"

    print("Starting OpenAI call to summarize conversation...")
    # print(f"Prompt: {prompt}")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=2000
    )
    print("Finished OpenAI call to summarize conversation.")
    summary = response.choices[0].message.content.strip()
    return summary

def save_to_file(summary_text, query):

  if not os.path.exists('searches'):
    os.makedirs('searches')

  sanitized_query = os.path.splitext(query)[0]  # Remove file extension if present
  sanitized_query = sanitized_query.replace("/", "_") 
  sanitized_query = sanitized_query[:100]  

  base_file_name = f"searches/summary_{sanitized_query}.txt"
  file_name = base_file_name

  counter = 2
  while os.path.exists(file_name):
    file_name = f"{base_file_name[:-4]}-{counter}.txt"
    counter += 1

  with open(file_name, 'w') as file:
    file.write(summary_text)
    print(f"Saved search result to {file_name}")

  return file_name

def process_query(search_term, keyword_override: str = None, send_all_matches=False):
    if keyword_override:
        keywords = [keyword.strip() for keyword in keyword_override.split(',')]
        print(f"Overriden keywords: {keywords}")
    else:
        keywords_dict = get_search_keywords(search_term)
        keywords = keywords_dict.get("keywords", []) 
    # Find messages related to the keywords
    initial_results = search_index(keywords)
    print(f"{len(initial_results)} total initial matching messages from {len(keywords)} keywords")
    if len(initial_results) == 0:
        print("No results found, exiting...")
        exit(1)
    if send_all_matches:
        selected_messages = initial_results
    else:
        # Turn the initial search into a vector
        query_embedding = get_query_embedding(search_term)
        # Turn search results into a vector
        message_embeddings = get_message_embeddings(initial_results)
        # FInd the messages with the most similarity (vector distance) of the query
        similarities = calculate_similarity(message_embeddings, query_embedding)
        # Get the top N most similar messages from the search
        number_of_potentially_relevant_messages = 200
        top_n = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)[:number_of_potentially_relevant_messages]
        print(f"Produced {len(top_n)} potentially more relevant messages")
        selected_messages = [initial_results[i] for i in top_n]
    relevant_message_ids = select_relevant_messages(search_term, selected_messages)
    relevant_messages = [msg for msg in selected_messages if msg[0] in relevant_message_ids]
    print(f"OpenAI Selected {len(relevant_messages)} relevant messages")
    expanded_messages = contextual_expansion(relevant_messages)
    total_expanded_messages_count = sum(len(messages) for messages in expanded_messages)
    print(f"Expanded surrounding messages: {total_expanded_messages_count} messages")
    estimated_tokens = estimate_tokens(expanded_messages)
    if estimated_tokens > 128000:
        print("### Trimmed search input, too many tokens!")
        print(f"Estimated # of tokens before trimming: {estimated_tokens}")
        expanded_messages = trim_messages(expanded_messages, 125000)
        estimated_tokens = estimate_tokens(expanded_messages)
        print(f"Estimated # of tokens after trimming: {estimated_tokens}")
    summary = summarize_conversation(search_term, expanded_messages)
    save_to_file(summary, search_term)
    return summary

def parse_args():
    parser = argparse.ArgumentParser(description="Search Discord DMs")
    parser.add_argument('search_term', type=str, nargs='*', help='Search term')
    parser.add_argument('--no-cost', action='store_true', help='Skip ChatGPT interaction')
    parser.add_argument('--keyword-override', action='append', type=str, help='Just search specific keywords with this prompt.')
    parser.add_argument('--send-all-matches', action='store_true', default=False, help='Send all matches to OpenAI, dont use text embeddings to do initial screening. May crash with too many matches!!')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    if args.search_term:
        search_term = ' '.join(args.search_term)
        summary = process_query(search_term, args.keyword_override, args.send_all_matches)
        print(summary)

if __name__ == "__main__":
    main()

