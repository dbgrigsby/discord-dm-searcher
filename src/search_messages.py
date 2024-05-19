import argparse
import openai
import sqlite3
import os
import sys
import json

# Command-line argument parsing
parser = argparse.ArgumentParser(description="Search Discord DMs")
parser.add_argument('search_term', type=str, nargs='*', help='Search term')
parser.add_argument('--no-cost', action='store_true', help='Skip ChatGPT interaction')
args = parser.parse_args()

# Function to get OpenAI key
def get_openai_key():
    openai_key = os.getenv("OPENAI_KEY")
    if not openai_key:
        try:
            with open("OPENAI_KEY.txt", "r") as file:
                openai_key = file.read().strip()
        except FileNotFoundError:
            pass
    return openai_key

# Check if the OpenAI key is needed and set
if not args.no_cost:
    openai_key = get_openai_key()
    if not openai_key:
        print("Error: The OPENAI_KEY environment variable is not set and OPENAI_KEY.txt is missing.")
        print("Please set the key using 'export OPENAI_KEY=your_openai_key_here' or create an OPENAI_KEY.txt file.")
        sys.exit(1)

client = openai.OpenAI(api_key=get_openai_key())

DATABASE_PATH = 'database/messages.db'

def get_search_keywords(query):
    prompt = f"Given the query: '{query}', return with ONLY A JSON blob of keywords to search for specific chat history between two friends."
    print("Starting OpenAI call to get search keywords...")
    response = client.chat.completions.create(model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=50)
    print("Finished OpenAI call to get search keywords.")
    keywords = response.choices[0].message.content.strip()
    print("OpenAI response JSON for search keywords:\n", keywords)
    return keywords

def search_index(keywords):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Convert keywords to a SQL search query
    keyword_list = keywords.split()
    keyword_query = " OR ".join([f"contents LIKE '%{keyword}%'" for keyword in keyword_list])

    query = f'''
    SELECT message_id, name, timestamp, contents, attachments, link
    FROM messages
    WHERE {keyword_query}
    '''

    cursor.execute(query)
    results = cursor.fetchall()

    conn.close()

    return results

def process_results(results):
    # Summarize and format results
    summarized_results = ""
    for result in results:
        summarized_results += f"ID: {result[0]}\nUser: {result[1]}\nTimestamp: {result[2]}\nContents: {result[3]}\nLink: {result[5]}\n\n"
    return summarized_results

def no_cost_mode(query):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    keyword_query = " OR ".join([f"contents LIKE '%{query}%'" for query in query])

    query = f'''
    SELECT message_id, name, timestamp, contents, attachments, link
    FROM messages
    WHERE {keyword_query}
    LIMIT 10
    '''

    cursor.execute(query)
    results = cursor.fetchall()

    conn.close()

    return results

def summarize_conversation(original_query, results):
    messages = "\n\n".join([f"User: {result[1]}\nTimestamp: {result[2]}\nContents: {result[3]}\nLink: {result[5]}" for result in results])
    prompt = f"Given the original query: '{original_query}', and the following messages between two friends, provide a summary with relevant links:\n\n{messages}\n\nPlease return full Discord links, not hyperlinks."

    print("Starting OpenAI call to summarize conversation...")
    response = client.chat.completions.create(model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=500)
    print("Finished OpenAI call to summarize conversation.")
    summary = response.choices[0].message.content.strip()
    return summary

def main():
    if args.search_term:
        search_term = ' '.join(args.search_term)
        if args.no_cost:
            results = no_cost_mode(search_term)
            print(process_results(results))
        else:
            keywords = get_search_keywords(search_term)
            results = search_index(keywords)
            summary = summarize_conversation(search_term, results)
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
                keywords = get_search_keywords(query)
                results = search_index(keywords)
                summary = summarize_conversation(query, results)
                print(summary)

if __name__ == "__main__":
    main()

