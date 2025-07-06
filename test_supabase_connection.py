#!/usr/bin/env python3
"""
Test Supabase connection and verify database setup
This script checks if all required tables and functions are properly configured
"""

import asyncio
import os
import sys
from typing import Dict, List, Tuple

import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ANSI color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


async def test_connection(connection_string: str, connection_type: str) -> bool:
    """Test if we can connect to the database"""
    print(f"\n{BLUE}Testing {connection_type} connection...{RESET}")
    try:
        # Disable prepared statements for PgBouncer compatibility
        conn = await asyncpg.connect(
            connection_string, statement_cache_size=0  # Disable prepared statements
        )
        version = await conn.fetchval("SELECT version()")
        print(f"{GREEN}✓ Connected successfully!{RESET}")
        print(f"  PostgreSQL version: {version.split(',')[0]}")
        await conn.close()
        return True
    except Exception as e:
        print(f"{RED}✗ Connection failed: {e}{RESET}")
        return False


async def check_extensions(pool) -> Dict[str, bool]:
    """Check if required extensions are installed"""
    print(f"\n{BLUE}Checking extensions...{RESET}")
    extensions = {}

    try:
        # Check for pgvector
        result = await pool.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        extensions["pgvector"] = result

        # Check for uuid-ossp
        result = await pool.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp')"
        )
        extensions["uuid-ossp"] = result

        # Test vector functionality
        if extensions["pgvector"]:
            dims = await pool.fetchval("SELECT vector_dims(ARRAY[1,2,3]::vector)")
            print(
                f"{GREEN}✓ pgvector is working (test returned {dims} dimensions){RESET}"
            )
        else:
            print(f"{RED}✗ pgvector extension not found{RESET}")

    except Exception as e:
        print(f"{RED}✗ Error checking extensions: {e}{RESET}")

    return extensions


async def check_tables(pool) -> Dict[str, bool]:
    """Check if all required tables exist"""
    print(f"\n{BLUE}Checking tables...{RESET}")

    required_tables = ["research_chunks", "cache_entries"]

    query = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE'
    """

    try:
        rows = await pool.fetch(query)
        existing_tables = {row["table_name"] for row in rows}

        table_status = {}
        for table in required_tables:
            exists = table in existing_tables
            table_status[table] = exists
            if exists:
                print(f"{GREEN}✓ {table}{RESET}")
            else:
                print(f"{RED}✗ {table} - NOT FOUND{RESET}")

        return table_status
    except Exception as e:
        print(f"{RED}✗ Error checking tables: {e}{RESET}")
        return {}


async def check_functions(pool) -> Dict[str, bool]:
    """Check if all RPC functions exist"""
    print(f"\n{BLUE}Checking RPC functions...{RESET}")

    # For now, we don't have any RPC functions
    required_functions = []

    query = """
    SELECT routine_name 
    FROM information_schema.routines 
    WHERE routine_schema = 'public' 
    AND routine_type = 'FUNCTION'
    """

    try:
        rows = await pool.fetch(query)
        existing_functions = {row["routine_name"] for row in rows}

        function_status = {}
        for func in required_functions:
            exists = func in existing_functions
            function_status[func] = exists
            if exists:
                print(f"{GREEN}✓ {func}{RESET}")
            else:
                print(f"{RED}✗ {func} - NOT FOUND{RESET}")

        return function_status
    except Exception as e:
        print(f"{RED}✗ Error checking functions: {e}{RESET}")
        return {}


async def test_rpc_functions(pool) -> None:
    """Test if RPC functions work correctly"""
    print(f"\n{BLUE}Testing basic queries...{RESET}")

    try:
        # Test vector dimension check
        if await pool.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        ):
            # Test creating a simple vector
            dims = await pool.fetchval(
                "SELECT array_length(ARRAY[1,2,3]::float[]::vector, 1)"
            )
            print(f"{GREEN}✓ Vector operations work{RESET}")

        # Test if tables exist and have correct structure
        chunks_exists = await pool.fetchval(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'research_chunks')"
        )
        if chunks_exists:
            # Check column exists
            has_embedding = await pool.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'research_chunks' 
                    AND column_name = 'embedding'
                )
            """
            )
            print(
                f"{GREEN}✓ research_chunks has embedding column: {has_embedding}{RESET}"
            )

    except Exception as e:
        print(f"{RED}✗ Error testing queries: {e}{RESET}")


async def check_indexes(pool) -> None:
    """Check if important indexes exist"""
    print(f"\n{BLUE}Checking indexes...{RESET}")

    query = """
    SELECT 
        schemaname,
        tablename,
        indexname,
        indexdef
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND tablename IN ('research_chunks', 'cache_entries')
    ORDER BY tablename, indexname
    """

    try:
        rows = await pool.fetch(query)

        # Group by table
        indexes_by_table = {}
        for row in rows:
            table = row["tablename"]
            if table not in indexes_by_table:
                indexes_by_table[table] = []
            indexes_by_table[table].append(row["indexname"])

        # Check for vector indexes
        vector_index_found = False
        for table, indexes in indexes_by_table.items():
            print(f"\n  {table}:")
            for index in indexes:
                if "embedding" in index:
                    vector_index_found = True
                    print(f"    {GREEN}✓ {index} (vector index){RESET}")
                else:
                    print(f"    ✓ {index}")

        if not vector_index_found:
            print(
                f"\n  {YELLOW}⚠ No vector indexes found - similarity search may be slow{RESET}"
            )

    except Exception as e:
        print(f"{RED}✗ Error checking indexes: {e}{RESET}")


async def main():
    """Main test function"""
    print(f"{BLUE}=== Supabase Connection and Setup Test ==={RESET}")

    # Get connection strings from environment
    # Strip comments and whitespace
    supabase_url = os.getenv("SUPABASE_URL", "").split("#")[0].strip()
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "").split("#")[0].strip()
    direct_url = os.getenv("DATABASE_URL", "").split("#")[0].strip()
    pool_url = os.getenv("DATABASE_POOL_URL", "").split("#")[0].strip()

    # Also check for DATABASE_POOLER_URL (common typo)
    if not pool_url:
        pool_url = os.getenv("DATABASE_POOLER_URL", "").split("#")[0].strip()

    if not all([supabase_url, supabase_key]):
        print(f"{RED}Missing required environment variables!{RESET}")
        print("Please ensure the following are set in your .env file:")
        print("- SUPABASE_URL")
        print("- SUPABASE_SERVICE_KEY")
        print("- DATABASE_URL (optional but recommended)")
        print("- DATABASE_POOL_URL (optional but recommended)")
        return

    print(f"Supabase URL: {supabase_url}")
    if pool_url:
        print(f"Pool URL: {pool_url[:50]}...")  # Show first 50 chars for security
    if direct_url:
        print(f"Direct URL: {direct_url[:50]}...")  # Show first 50 chars for security

    # Test connections
    if pool_url:
        pool_ok = await test_connection(pool_url, "Pooled")
    else:
        print(f"{YELLOW}⚠ DATABASE_POOL_URL not set - using direct connection{RESET}")
        pool_url = direct_url

    if direct_url:
        direct_ok = await test_connection(direct_url, "Direct")

    if not pool_url and not direct_url:
        print(f"{RED}No database connection strings found!{RESET}")
        return

    # Create connection pool for remaining tests
    try:
        # Use pooled connection if available, otherwise direct
        connection_string = pool_url or direct_url
        # Disable prepared statements for PgBouncer compatibility
        pool = await asyncpg.create_pool(
            connection_string,
            min_size=1,
            max_size=5,
            command_timeout=60,
            statement_cache_size=0,  # Disable prepared statements for PgBouncer
        )

        # Run all checks
        extensions = await check_extensions(pool)
        tables = await check_tables(pool)
        functions = await check_functions(pool)

        # Only test functions if tables exist
        if any(tables.values()):
            await test_rpc_functions(pool)

        # Check indexes
        await check_indexes(pool)

        # Summary
        print(f"\n{BLUE}=== Summary ==={RESET}")

        all_extensions_ok = all(extensions.values()) if extensions else False
        all_tables_ok = all(tables.values()) if tables else False
        all_functions_ok = all(functions.values()) if functions else False

        if all_extensions_ok and all_tables_ok and all_functions_ok:
            print(
                f"{GREEN}✓ All checks passed! Your Supabase setup is complete.{RESET}"
            )
        else:
            print(
                f"{YELLOW}⚠ Some checks failed. Please run the missing SQL scripts:{RESET}"
            )

            if not extensions.get("pgvector", False):
                print(f"  - Run sql/init_database.sql")

            missing_tables = [t for t, exists in tables.items() if not exists]
            if missing_tables:
                print(
                    f"  - Run the SQL scripts for missing tables: {', '.join(missing_tables)}"
                )

            missing_functions = [f for f, exists in functions.items() if not exists]
            if missing_functions:
                print(f"  - Run sql/rpc_functions.sql")

        await pool.close()

    except Exception as e:
        print(f"{RED}✗ Error creating connection pool: {e}{RESET}")
        print(
            f"\nMake sure your connection strings are correct and Supabase is accessible."
        )


if __name__ == "__main__":
    asyncio.run(main())
