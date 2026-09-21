"""
Migration: Add user_id columns for multi-tenant data isolation.

Adds user_id (VARCHAR 255) to: suppliers, data_sources, schema_mappings, config_records.
Existing rows get user_id = 'legacy'.
Creates indexes for efficient tenant-scoped queries.

Usage:
    python scripts/add_user_id_columns.py
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


TABLES = ["suppliers", "data_sources", "schema_mappings", "config_records"]
DEFAULT_USER_ID = "legacy"


async def run_migration():
    try:
        from src.data.database import engine
    except ImportError:
        from data.database import engine
    from sqlalchemy import text

    print("[*] Starting multi-tenant migration...")
    print(f"   Database: {engine.url}\n")

    async with engine.begin() as conn:
        for table in TABLES:
            # Check if column already exists
            check_sql = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = :table AND column_name = 'user_id'
            """)
            result = await conn.execute(check_sql, {"table": table})
            exists = result.fetchone()

            if exists:
                print(f"  [OK] {table}.user_id already exists -- skipping")
                continue

            # Add column with default (DDL statements cannot take bind parameters in PostgreSQL)
            print(f"  [..] Adding user_id to {table}...")
            await conn.execute(text(
                f"ALTER TABLE {table} ADD COLUMN user_id VARCHAR(255) DEFAULT '{DEFAULT_USER_ID}' NOT NULL"
            ))

            # Update existing rows
            result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            if count and count > 0:
                print(f"     -> Set user_id='{DEFAULT_USER_ID}' on {count} existing rows")

            # Create index
            idx_name = f"ix_{table}_user_id"
            await conn.execute(text(
                f'CREATE INDEX IF NOT EXISTS {idx_name} ON {table} (user_id)'
            ))
            print(f"  [OK] {table}.user_id added + indexed")

    print("\n[OK] Migration complete!")
    print(f"   Note: Existing rows have user_id='{DEFAULT_USER_ID}' and won't appear")
    print("   for authenticated users. Each user starts with a clean slate.")


if __name__ == "__main__":
    asyncio.run(run_migration())
