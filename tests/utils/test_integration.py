"""
Integration test script for SearchFunctions
This script tests the actual function with real OpenAlex API calls (optional)
"""

import json
import os
import sys
from unittest.mock import Mock

import azure.functions as func

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.search_functions.functions import search_openalex_list


def create_mock_request(search_query):
    """Create a mock Azure Functions HttpRequest with search query"""
    mock_req = Mock(spec=func.HttpRequest)
    mock_req.headers = {"x-search-query": search_query}
    return mock_req


def test_search_functionality():
    """Test the search functionality with various queries"""
    print("=" * 60)
    print("TESTING SEARCH FUNCTIONS")
    print("=" * 60)

    # Test cases
    test_cases = [
        {
            "name": "Valid Title Search",
            "query": "machine learning",
            "expect_success": True,
        },
        {"name": "DOI Search", "query": "10.1038/nature12373", "expect_success": True},
        {"name": "Empty Query", "query": "", "expect_success": False},
        {
            "name": "Very Specific Query",
            "query": "BERT transformer natural language processing",
            "expect_success": True,
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"Query: '{test_case['query']}'")
        print("-" * 40)

        try:
            # Create mock request
            mock_req = create_mock_request(test_case["query"])

            # Call the function
            response = search_openalex_list(mock_req)

            # Parse response
            status_code = response.status_code
            body = response.get_body().decode()
            data = json.loads(body)

            print(f"Status Code: {status_code}")

            if status_code == 200:
                print(f"Status Message: {data.get('statusMessage', 'N/A')}")
                print(f"Results Count: {len(data.get('results', []))}")
                print(f"Message: {data.get('message', 'N/A')}")

                # Show first result if available
                results = data.get("results", [])
                if results:
                    first_result = results[0]
                    print(f"First Result Title: {first_result.get('title', 'N/A')}")
                    print(
                        f"First Result Authors: {len(first_result.get('authors', []))} authors"
                    )
                    print(f"First Result DOI: {first_result.get('doi', 'N/A')}")
                    print(f"First Result Venue: {first_result.get('venue', 'N/A')}")
                    print(f"First Result Year: {first_result.get('year', 'N/A')}")
            else:
                print(f"Error: {data.get('error', 'Unknown error')}")

            # Check if result matches expectation
            if test_case["expect_success"]:
                if status_code == 200 and data.get("statusMessage") == "SUCCESS":
                    print("✅ PASSED - Got expected success")
                else:
                    print("❌ FAILED - Expected success but got failure")
            else:
                if status_code != 200 or data.get("statusMessage") == "FAILURE":
                    print("✅ PASSED - Got expected failure")
                else:
                    print("❌ FAILED - Expected failure but got success")

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            import traceback

            traceback.print_exc()


def test_mapping_function():
    """Test the work mapping function"""
    from modules.search_functions.functions import _map_work_for_search_local

    print("\n" + "=" * 60)
    print("TESTING WORK MAPPING FUNCTION")
    print("=" * 60)

    # Test case 1: Complete work
    work1 = {
        "title": "Test Paper Title",
        "doi_url": "https://doi.org/10.1000/test123",
        "authorships": [
            {"author": {"display_name": "John Doe"}},
            {"author": {"display_name": "Jane Smith"}},
        ],
        "host_venue": {"display_name": "Nature"},
        "publication_year": 2023,
    }

    result1 = _map_work_for_search_local(work1)
    print("1. Complete Work Mapping:")
    print(f"   Title: {result1['title']}")
    print(f"   DOI: {result1['doi']}")
    print(f"   Authors: {result1['authors']}")
    print(f"   Venue: {result1['venue']}")
    print(f"   Year: {result1['year']}")

    # Test case 2: Empty work
    result2 = _map_work_for_search_local({})
    print("\n2. Empty Work Mapping:")
    print(f"   Title: '{result2['title']}'")
    print(f"   DOI: '{result2['doi']}'")
    print(f"   Authors: {result2['authors']}")
    print(f"   Venue: '{result2['venue']}'")
    print(f"   Year: {result2['year']}")

    # Test case 3: Work with alternative fields
    work3 = {
        "display_name": "Alternative Title",
        "ids": {"doi": "10.1000/alt123"},
        "authorships": [{"author": {"display_name": "Alt Author"}}],
        "publication_year": "2022",  # String year
    }

    result3 = _map_work_for_search_local(work3)
    print("\n3. Alternative Fields Mapping:")
    print(f"   Title: {result3['title']}")
    print(f"   DOI: {result3['doi']}")
    print(f"   Authors: {result3['authors']}")
    print(f"   Year: {result3['year']}")


if __name__ == "__main__":
    print("Starting SearchFunctions Integration Tests...")
    print(f"Python Path: {sys.executable}")
    print(f"Working Directory: {os.getcwd()}")

    try:
        test_mapping_function()
        test_search_functionality()
        print("\n" + "=" * 60)
        print("TESTS COMPLETED")
        print("=" * 60)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
