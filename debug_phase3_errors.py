"""
Debug script for Phase 3 test errors.
Investigates why embedding dimensions and semantic search tests are failing.
"""

import asyncio
import json
import os
from supabase import Client, create_client
import numpy as np
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)


async def debug_vector_issues():
    """Debug the vector storage and search issues."""

    # Connect to Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        print(f"{Fore.RED}Missing environment variables{Style.RESET_ALL}")
        return

    supabase: Client = create_client(supabase_url, supabase_key)

    print(f"{Fore.CYAN}=== DEBUGGING PHASE 3 ERRORS ==={Style.RESET_ALL}\n")

    # Test 1: Check if vector extension is enabled
    print(f"{Fore.YELLOW}1. Checking vector extension...{Style.RESET_ALL}")
    try:
        result = supabase.rpc("test_vector_extension", {}).execute()
        print(f"{Fore.GREEN}✓ Vector extension is enabled{Style.RESET_ALL}")
    except Exception as e:
        # Extension check failed, let's create a simple test
        try:
            # Try to create a test vector
            test_query = "SELECT '[1,2,3]'::vector as test_vector"
            result = supabase.rpc("execute_sql", {"query": test_query}).execute()
            print(
                f"{Fore.GREEN}✓ Vector extension appears to be working{Style.RESET_ALL}"
            )
        except:
            print(f"{Fore.RED}✗ Vector extension might not be enabled{Style.RESET_ALL}")

    # Test 2: Insert and retrieve a test embedding
    print(f"\n{Fore.YELLOW}2. Testing embedding storage...{Style.RESET_ALL}")

    # Create a test source
    test_source = {
        "url": f"https://debug-test.com/article-debug",
        "domain": "debug-test.com",
        "title": "Debug Test Article",
        "full_content": "Debug content",
        "credibility_score": 0.5,
    }

    try:
        # Insert source
        source_result = supabase.table("research_sources").insert(test_source).execute()
        source_id = source_result.data[0]["id"]
        print(f"  Created test source: {source_id}")

        # Create a mock embedding
        embedding = np.random.randn(1536)
        embedding = (embedding / np.linalg.norm(embedding)).tolist()

        # Insert chunk with embedding
        chunk_data = {
            "source_id": source_id,
            "chunk_text": "Debug test chunk",
            "chunk_embedding": embedding,
            "chunk_number": 1,
        }

        chunk_result = supabase.table("content_chunks").insert(chunk_data).execute()
        print(f"  Inserted chunk: {chunk_result.data[0]['id']}")

        # Retrieve and check
        retrieve_result = (
            supabase.table("content_chunks")
            .select("*")
            .eq("source_id", source_id)
            .execute()
        )

        if retrieve_result.data:
            chunk = retrieve_result.data[0]
            print(f"  Retrieved chunk successfully")

            # Check embedding
            if "chunk_embedding" in chunk:
                embedding_data = chunk["chunk_embedding"]
                print(f"  Embedding type: {type(embedding_data)}")

                # Check if it's a string (might need parsing)
                if isinstance(embedding_data, str):
                    print(
                        f"  Embedding is stored as string, length: {len(embedding_data)}"
                    )
                    print(f"  First 50 chars: {embedding_data[:50]}")

                    # Try to parse it
                    try:
                        if embedding_data.startswith("["):
                            parsed = json.loads(embedding_data)
                            print(f"  Parsed as JSON array, length: {len(parsed)}")
                        else:
                            print(f"  String format: {embedding_data[:100]}")
                    except:
                        print(f"  Could not parse as JSON")

                elif isinstance(embedding_data, list):
                    print(f"  Embedding is a list, length: {len(embedding_data)}")
                else:
                    print(f"  Unexpected embedding type: {type(embedding_data)}")
            else:
                print(f"{Fore.RED}  No chunk_embedding field found!{Style.RESET_ALL}")
                print(f"  Available fields: {list(chunk.keys())}")

        # Cleanup
        supabase.table("research_sources").delete().eq("id", source_id).execute()

    except Exception as e:
        print(f"{Fore.RED}  Error during embedding test: {str(e)}{Style.RESET_ALL}")

    # Test 3: Check search function
    print(f"\n{Fore.YELLOW}3. Testing search function...{Style.RESET_ALL}")

    # Create test embedding for search
    query_embedding = np.random.randn(1536)
    query_embedding = (query_embedding / np.linalg.norm(query_embedding)).tolist()

    try:
        # Try the search function
        search_params = {
            "query_embedding": query_embedding,
            "match_threshold": 0.0,
            "match_count": 10,
        }

        search_result = supabase.rpc("search_similar_chunks", search_params).execute()

        print(f"  Search function called successfully")
        print(f"  Result type: {type(search_result.data)}")
        print(f"  Result data: {search_result.data}")

        if search_result.data is None:
            print(
                f"{Fore.YELLOW}  Search returned None (might be normal if no data){Style.RESET_ALL}"
            )
        elif isinstance(search_result.data, list):
            print(f"  Search returned {len(search_result.data)} results")
        else:
            print(f"  Unexpected result format")

    except Exception as e:
        print(f"{Fore.RED}  Error calling search function: {str(e)}{Style.RESET_ALL}")

    # Test 4: Check if functions exist
    print(f"\n{Fore.YELLOW}4. Checking if functions exist...{Style.RESET_ALL}")

    check_functions = [
        "search_similar_chunks",
        "find_related_sources",
        "calculate_optimal_lists",
    ]

    for func_name in check_functions:
        try:
            # Try to get function info
            query = f"""
            SELECT routine_name 
            FROM information_schema.routines 
            WHERE routine_schema = 'public' 
            AND routine_name = '{func_name}'
            """
            # Note: This would need a direct SQL execution method
            print(f"  Function '{func_name}': Would need to check via SQL")
        except:
            pass

    print(f"\n{Fore.CYAN}=== DEBUG COMPLETE ==={Style.RESET_ALL}")
    print("\nPossible issues:")
    print("1. Vector data might be stored as strings instead of arrays")
    print("2. Search function might expect different parameter format")
    print("3. Functions might not have been created in the migration")
    print("\nRecommended next steps:")
    print("1. Check Supabase dashboard for function definitions")
    print("2. Verify vector column type in content_chunks table")
    print("3. Test search function directly in Supabase SQL editor")


if __name__ == "__main__":
    asyncio.run(debug_vector_issues())
