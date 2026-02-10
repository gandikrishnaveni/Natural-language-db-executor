import sqlite3

# Define the path to your Spider database
DB_PATH = "data/college_2.sqlite"

def get_schema_context():
    """Fetches table names and columns so the AI knows what it's looking at."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
    schemas = cursor.fetchall()
    conn.close()
    return "\n".join([s[0] for s in schemas])

def translate_and_run(user_query):
    # This is where your LLM (GPT/Llama) logic will eventually go.
    # For now, let's just prove we can talk to the database.
    schema = get_schema_context()
    print(f"I found these tables:\n{schema}")
    return "NLP Engine is ready for the demo!"

if __name__ == "__main__":
    print(translate_and_run("Show me all students"))