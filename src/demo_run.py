import pandas as pd
from nlp_engine import NLPEngine 

def run_complete_demo():
    db_path = "data/college_2.sqlite" 
    engine = NLPEngine(db_path)
    
    print("=== LegalBrain AI: End-to-End Demo ===")
    print(f"Connected to: {db_path}")
    
    while True:
        user_input = input("\n[Enter Command] (or type 'exit' to quit): ")
        
        if user_input.lower() == 'exit':
            break

        # --- NEW STEP: Ambiguity/Clarification Check ---
        print("\n--- Step 1: Checking Intent Clarity ---")
        status = engine.get_clarification(user_input)
        
        if "AMBIGUOUS" in status:
            print(f"🤖 AI needs clarification: {status.replace('AMBIGUOUS:', '').strip()}")
            # Get specific instructions from the user
            user_input = input("Please clarify your request: ")
        else:
            print("✅ Intent is clear. Proceeding...")

        # --- Step 2: Generate SQL ---
        print("\n--- Step 2: NLP Generation ---")
        generated_sql = engine.generate_sql(user_input)
        print(f"Generated SQL: {generated_sql}")
        
        # --- Step 3: Safety Check ---
        if any(word in generated_sql.upper() for word in ["DELETE", "UPDATE", "DROP"]):
            confirm = input(f"⚠️ DANGER: This query modifies data. Run it? (y/n): ")
            if confirm.lower() != 'y':
                print("Execution cancelled.")
                continue

        # --- Step 4: Execute ---
        print("\n--- Step 3: Database Execution ---")
        result = engine.execute_query(generated_sql)
        
        # --- Step 5: Display results ---
        if isinstance(result, pd.DataFrame):
            if result.empty:
                print("Query successful, but no data was found.")
            else:
                print("Results Found:")
                print(result.to_string(index=False)) 
        else:
            print(result) 

if __name__ == "__main__":
    run_complete_demo()