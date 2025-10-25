"""
Migration script to add self-correction tracking fields to agent_traces table.
Run this once to update existing database.
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def migrate():
    DATABASE_URL = os.getenv("DATABASE_URL")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("Adding correction tracking fields to agent_traces...")
        
        # Add new columns
        conn.execute(text("""
            ALTER TABLE agent_traces 
            ADD COLUMN IF NOT EXISTS correction_attempts INTEGER DEFAULT 0;
        """))
        
        conn.execute(text("""
            ALTER TABLE agent_traces 
            ADD COLUMN IF NOT EXISTS original_confidence INTEGER;
        """))
        
        conn.execute(text("""
            ALTER TABLE agent_traces 
            ADD COLUMN IF NOT EXISTS final_confidence INTEGER;
        """))
        
        conn.execute(text("""
            ALTER TABLE agent_traces 
            ADD COLUMN IF NOT EXISTS improvement_delta INTEGER;
        """))
        
        conn.commit()
        print("✅ Migration complete!")
        print("\nNew fields added:")
        print("  - correction_attempts (default: 0)")
        print("  - original_confidence")
        print("  - final_confidence")
        print("  - improvement_delta")

if __name__ == "__main__":
    migrate()
