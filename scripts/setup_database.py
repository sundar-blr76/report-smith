#!/usr/bin/env python3
"""
Setup ReportSmith database and schema
"""
import os
import sys
from pathlib import Path
import psycopg2
from psycopg2 import sql

# Database configuration from environment variables
DB_CONFIG = {
    'host': os.getenv('REPORTSMITH_DB_HOST', 'localhost'),
    'port': int(os.getenv('REPORTSMITH_DB_PORT', '5432')),
    'user': os.getenv('REPORTSMITH_DB_USER', 'postgres'),
    'password': os.getenv('REPORTSMITH_DB_PASSWORD', 'postgres'),
    'database': 'postgres'  # Connect to postgres to create database
}

TARGET_DB = os.getenv('REPORTSMITH_DB_NAME', 'reportsmith')

def create_database():
    """Create the ReportSmith database if it doesn't exist."""
    print("=" * 60)
    print("Creating ReportSmith Database")
    print("=" * 60)
    print(f"Host: {DB_CONFIG['host']}")
    print(f"Port: {DB_CONFIG['port']}")
    print(f"Database: {TARGET_DB}")
    print(f"User: {DB_CONFIG['user']}")
    print()
    
    try:
        # Connect to postgres database
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (TARGET_DB,)
        )
        exists = cursor.fetchone()
        
        if exists:
            print(f"✅ Database '{TARGET_DB}' already exists")
        else:
            # Create database
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(TARGET_DB)
                )
            )
            print(f"✅ Database '{TARGET_DB}' created successfully")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def create_schema():
    """Create tables in the ReportSmith database."""
    print()
    print("Step 2: Creating tables...")
    print()
    
    try:
        # Connect to reportsmith database
        config = DB_CONFIG.copy()
        config['database'] = TARGET_DB
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        
        # Read SQL file
        sql_file = Path(__file__).parent / 'create_reportsmith_schema.sql'
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        # Execute SQL
        cursor.execute(sql_content)
        conn.commit()
        
        print("✅ Schema created successfully")
        
        # Verify tables
        cursor.execute("""
            SELECT count(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        table_count = cursor.fetchone()[0]
        
        print()
        print(f"Tables created: {table_count}")
        
        if table_count == 6:
            print("✅ Success! All 6 tables created.")
        else:
            print(f"⚠️  Warning: Expected 6 tables, found {table_count}")
        
        # List tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        print()
        print("Tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating schema: {e}")
        return False

def main():
    """Main setup function."""
    print()
    
    # Create database
    if not create_database():
        sys.exit(1)
    
    # Create schema
    if not create_schema():
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("Database setup complete!")
    print("=" * 60)
    print()

if __name__ == "__main__":
    main()
