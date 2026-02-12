import os
import sqlite3
import re
import pandas as pd
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables
load_dotenv()

class NLPEngine:
    def __init__(self, db_path):
        """
        Initializes the NLP Engine with the efficient Qwen2.5-Coder-1.5B model.
        This model provides sub-second latency for SQL generation on most laptops.
        """
        self.db_path = db_path
        
        # Initialize the local LLM via Ollama
        self.llm = ChatOllama(
            model="qwen2.5-coder:1.5b",
            temperature=0,  # Zero temperature for deterministic/accurate SQL
            base_url="http://localhost:11434"
        )

    def get_database_schema(self):
        """
        Extracts the schema from SQLite to provide context for the model.
        """
        try:
            if not os.path.exists(self.db_path):
                return "Error: Database file not found."
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
            schemas = [row[0] for row in cursor.fetchall() if row[0]]
            conn.close()
            return "\n\n".join(schemas)
        except Exception as e:
            return f"Error reading schema: {str(e)}"

    def generate_sql(self, user_query):
        """
        Translates Natural Language to SQL using Qwen2.5-Coder.
        """
        schema = self.get_database_schema()

        # Custom Prompt for Qwen Coder efficiency
        system_template = """<|im_start|>system
You are a SQL expert. Use the provided database schema to write a valid SQLite query.
Output ONLY the SQL code. No explanation. No markdown backticks.

DATABASE SCHEMA:
{schema}
<|im_end|>
<|im_start|>user
{question}
<|im_end|>
<|im_start|>assistant
"""
        
        prompt = ChatPromptTemplate.from_template(system_template)
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "schema": schema, 
                "question": user_query
            })
            
            # Clean output: remove any markdown blocks if the model accidentally includes them
            sql_output = response.content.strip()
            sql_output = re.sub(r'```sql|```', '', sql_output).strip()
            
            return sql_output
        except Exception as e:
            return f"NLP Error: {str(e)}"

    def execute_query(self, sql_query):
        """
        Executes the generated SQL on the database and returns the result.
        """
        try:
            # Connect to the SQLite database
            conn = sqlite3.connect(self.db_path)
            
            # If it's a SELECT query, return a table (DataFrame)
            if sql_query.strip().upper().startswith("SELECT"):
                # Use pandas to read the SQL directly into a table format
                df = pd.read_sql_query(sql_query, conn)
                conn.close()
                return df
            
            # If it's CREATE, INSERT, UPDATE, or DELETE, execute and commit changes
            else:
                cursor = conn.cursor()
                cursor.execute(sql_query)
                conn.commit()
                rows_affected = cursor.rowcount
                conn.close()
                return f"Success! {rows_affected} row(s) affected."
                
        except Exception as e:
            return f"Execution Error: {str(e)}"

# --- QUICK TEST BLOCK ---
if __name__ == "__main__":
    # Ensure this path is correct for your local setup
    db_file = "data/college_2.sqlite" 
    engine = NLPEngine(db_file)
    
    print("--- QWEN ENGINE TEST ---")
    test_query = "List all students"
    
    # 1. Generate the SQL
    generated_sql = engine.generate_sql(test_query)
    print(f"Question: {test_query}")
    print(f"Generated SQL: {generated_sql}")
    
    # 2. Execute the SQL and print results
    print("\n--- EXECUTION TEST ---")
    result = engine.execute_query(generated_sql)
    print(result)