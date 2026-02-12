import pandas as pd
from nlp_engine import NLPEngine # Assuming your class is in nlp_engine.py

def run_complete_demo():
    # 1. Initialize the system
    # Make sure this path points to your actual database file
    db_path = "data/college_2.sqlite" 
    engine = NLPEngine(db_path)
    
    print("=== LegalBrain AI: End-to-End Demo ===")
    print(f"Connected to: {db_path}")
    
    while True:
        # 2. Get user input
        user_input = input("\n[Enter Command] (or type 'exit' to quit): ")
        
        if user_input.lower() == 'exit':
            break
            
        # 3. Step 1: Generate SQL (Your NLP Part)
        print("\n--- Step 1: NLP Generation ---")
        generated_sql = engine.generate_sql(user_input)
        print(f"Generated SQL: {generated_sql}")
        
        # 4. Step 2: Safety Check (Damaris's logic idea)
        if any(word in generated_sql.upper() for word in ["DELETE", "UPDATE", "DROP"]):
            confirm = input(f"⚠️ DANGER: This query modifies data. Run it? (y/n): ")
            if confirm.lower() != 'y':
                print("Execution cancelled.")
                continue

        # 5. Step 3: Execute (The Final Step)
        print("--- Step 2: Database Execution ---")
        result = engine.execute_query(generated_sql)
        
        # 6. Step 4: Display results
        if isinstance(result, pd.DataFrame):
            if result.empty:
                print("Query successful, but no data was found.")
            else:
                print("Results Found:")
                print(result.to_string(index=False)) # Clean table view
        else:
            print(result) # Prints the "Rows affected" message

if __name__ == "__main__":
    run_complete_demo()