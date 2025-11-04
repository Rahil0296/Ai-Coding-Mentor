"""
Database Migration: Add Token Tracking Columns
Run this once to add token tracking to AgentTrace table
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def migrate_database():
    """Add token tracking columns to agent_traces table."""
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    if not DATABASE_URL:
        print("❌ ERROR: DATABASE_URL not found in .env file")
        return
    
    print("🔄 Connecting to database...")
    engine = create_engine(DATABASE_URL)
    
    # SQL commands to add new columns (safe - only adds if not exists)
    migrations = [
        """
        ALTER TABLE agent_traces 
        ADD COLUMN IF NOT EXISTS prompt_tokens INTEGER;
        """,
        """
        ALTER TABLE agent_traces 
        ADD COLUMN IF NOT EXISTS completion_tokens INTEGER;
        """,
        """
        ALTER TABLE agent_traces 
        ADD COLUMN IF NOT EXISTS estimated_cost_usd FLOAT;
        """
    ]
    
    try:
        with engine.connect() as connection:
            for i, migration in enumerate(migrations, 1):
                print(f"⏳ Running migration {i}/3...")
                connection.execute(text(migration))
                connection.commit()
                print(f"✅ Migration {i}/3 completed")
        
        print("\n🎉 SUCCESS! Token tracking columns added to database!")
        print("✅ Your database is now ready for token tracking.\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("Make sure your database is running and DATABASE_URL is correct.\n")

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE MIGRATION: Add Token Tracking")
    print("=" * 60)
    migrate_database()