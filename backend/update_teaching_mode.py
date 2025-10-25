from app.db import engine
from app.models import Base
from sqlalchemy import text

def update_schema():
    """Add teaching_mode and min_confidence_threshold to UserProfile"""
    with engine.connect() as conn:
        # Add teaching_mode column
        try:
            conn.execute(text("""
                ALTER TABLE user_profiles 
                ADD COLUMN teaching_mode VARCHAR DEFAULT 'guided'
            """))
            print("✓ Added teaching_mode column")
        except Exception as e:
            print(f"teaching_mode column might already exist: {e}")
        
        # Add min_confidence_threshold column
        try:
            conn.execute(text("""
                ALTER TABLE user_profiles 
                ADD COLUMN min_confidence_threshold INTEGER DEFAULT 70
            """))
            print("✓ Added min_confidence_threshold column")
        except Exception as e:
            print(f"min_confidence_threshold column might already exist: {e}")
        
        conn.commit()
    
    print("\n✅ Database updated successfully!")

if __name__ == "__main__":
    update_schema()
