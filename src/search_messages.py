import argparse
import sqlite3
import json
import numpy as np
from src.utils import initialize_openai

# Command-line argument parsing
parser = argparse.ArgumentParser(description="Search Discord DMs")
parser.add_argument('search_term', type=str, nargs='*', help='Search term')
parser.add_argument('--no-cost', action='store_true', help='Skip ChatGPT interaction')
args = parser.parse_args()

client = initialize_openai()

DATABASE_PATH = 'database/messages.db'

def get_search_keywords(query):
    prompt = f"""Given the query: '{query}', return ONLY A JSON blob of keywords to search for specific chat history between two friends. 
    Focus on phrases and expressions that people might use in the context of the query. Exclude common words like 'Rave' and 'Cas'. ONLY RESPOND WITH JSON."""
    print("Starting OpenAI call to get search keywords...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=100
    )
    print("Finished OpenAI call to get search keywords.")
    # print(f"Raw response: {response}")
    raw_content = response.choices[0].message.content.strip()
    if raw_content.startswith("```json"):
        raw_content = raw_content[7:-3].strip()
    keywords = json.loads(raw_content)
    print("OpenAI response JSON for search keywords:\n", json.dumps(keywords, indent=2))
    return keywords


def search_index(keywords):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    keyword_query = " OR ".join([f"contents LIKE '%{keyword}%'" for keyword in keywords])

    query = f'''
    SELECT message_id, name, timestamp, contents, attachments, link
    FROM messages
    WHERE {keyword_query}
    '''

    cursor.execute(query)
    results = cursor.fetchall()

    conn.close()
    return results

def get_message_embeddings(messages):
    response = client.embeddings.create(input=[msg[3] for msg in messages], model="text-embedding-3-large")
    embeddings = [item.embedding for item in response.data]
    return embeddings

def get_query_embedding(query):
    response = client.embeddings.create(input=[query], model="text-embedding-3-large")
    embedding = response.data[0].embedding
    return embedding


def calculate_similarity(embeddings, query_embedding):
    similarities = [np.dot(embed, query_embedding) for embed in embeddings]
    return similarities

def contextual_expansion(selected_messages, num_context=10):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    expanded_messages = []
    for message in selected_messages:
        message_id = message[0]
        query = f'''
        SELECT message_id, name, timestamp, contents, attachments, link
        FROM messages
        WHERE message_id >= {message_id - num_context} AND message_id <= {message_id + num_context}
        ORDER BY message_id
        '''
        cursor.execute(query)
        context = cursor.fetchall()
        expanded_messages.append(context)

    conn.close()
    return expanded_messages

def summarize_conversation(original_query, expanded_messages):
    conversations = "\n\n".join(["\n".join([f"User: {msg[1]}\nTimestamp: {msg[2]}\nContents: {msg[3]}\nLink: {msg[5]}" for msg in messages]) for messages in expanded_messages])
    prompt = f"Given the original query: '{original_query}', and the following messages between two friends, provide a summary with relevant links:\n\n{conversations}\n\nPlease return full Discord links, not hyperlinks."

    print("Starting OpenAI call to summarize conversation...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500)
    print("Finished OpenAI call to summarize conversation.")
    summary = response.choices[0].message.content.strip()
    return summary

def process_query(search_term):
    keywords = get_search_keywords(search_term)
    initial_results = search_index(keywords)
    query_embedding = get_query_embedding(search_term)
    message_embeddings = get_message_embeddings(initial_results)
    similarities = calculate_similarity(message_embeddings, query_embedding)
    top_n = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)[:10]
    selected_messages = [initial_results[i] for i in top_n]
    expanded_messages = contextual_expansion(selected_messages)
    summary = summarize_conversation(search_term, expanded_messages)
    return summary

def main():
    if args.search_term:
        search_term = ' '.join(args.search_term)
        if args.no_cost:
            results = no_cost_mode(search_term)
            print(process_results(results))
        else:
            summary = process_query(search_term)
            print(summary)
    else:
        while True:
            query = input("Enter search query: ")
            if query.lower() == 'exit':
                break
            if args.no_cost:
                results = no_cost_mode(query)
                print(process_results(results))
            else:
                summary = process_query(query)
                print(summary)

if __name__ == "__main__":
    main()

