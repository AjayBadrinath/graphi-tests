"""
Flask server for testing Azure Functions with Postman
This creates endpoints that can be easily tested with Postman
"""

import os
import sys
from unittest.mock import Mock

import azure.functions as func
from flask import Flask, jsonify, request

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.search_functions.functions import search_openalex_list

app = Flask(__name__)


class MockHttpRequest:
    """Mock Azure Functions HttpRequest for local testing"""

    def __init__(self, headers):
        self.headers = dict(headers)


@app.route("/api/search", methods=["POST", "GET"])
def search_endpoint():
    """Main search endpoint that mimics Azure Function behavior"""
    try:
        # Get search query from header
        search_query = request.headers.get("x-search-query")

        # Create mock Azure Function request
        mock_req = MockHttpRequest(request.headers)

        # Call the actual Azure Function
        response = search_openalex_list(mock_req)

        # Return the response with proper headers
        return (
            response.get_body().decode(),
            response.status_code,
            {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, x-search-query",
            },
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return (
        jsonify(
            {
                "status": "healthy",
                "message": "Server is running",
                "endpoints": ["/api/search", "/health", "/"],
            }
        ),
        200,
    )


@app.route("/", methods=["GET"])
def home():
    """Home endpoint with usage instructions for Postman"""
    instructions = {
        "message": "Azure Functions Local Test Server for Postman",
        "base_url": "http://localhost:5000",
        "endpoints": {
            "/api/search": {
                "method": "POST or GET",
                "headers": {"x-search-query": "Your search query or DOI"},
                "description": "Search for academic papers using OpenAlex",
                "examples": {
                    "title_search": "machine learning healthcare",
                    "doi_search": "10.1038/nature12373",
                    "specific_search": "BERT transformer NLP",
                },
            },
            "/health": {"method": "GET", "description": "Health check endpoint"},
        },
        "postman_examples": [
            {
                "name": "Search by Title",
                "method": "POST",
                "url": "http://localhost:5000/api/search",
                "headers": {"x-search-query": "machine learning"},
                "expected_response": "200 OK with results array",
            },
            {
                "name": "Search by DOI",
                "method": "POST",
                "url": "http://localhost:5000/api/search",
                "headers": {"x-search-query": "10.1038/nature12373"},
                "expected_response": "200 OK with single result",
            },
            {
                "name": "Empty Query (Error Test)",
                "method": "POST",
                "url": "http://localhost:5000/api/search",
                "headers": {"x-search-query": ""},
                "expected_response": "400 Bad Request",
            },
        ],
    }
    return jsonify(instructions), 200


# CORS support for browser testing
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add(
        "Access-Control-Allow-Headers", "Content-Type,Authorization,x-search-query"
    )
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    return response


if __name__ == "__main__":
    print("🚀 Starting Flask server for Postman testing...")
    print("📍 Base URL: http://localhost:5000")
    print("🔍 Search endpoint: http://localhost:5000/api/search")
    print("❤️  Health check: http://localhost:5000/health")
    print("📖 Instructions: http://localhost:5000/")
    print("\n📮 Postman Testing Examples:")
    print("1. POST http://localhost:5000/api/search")
    print("   Header: x-search-query: machine learning")
    print("2. POST http://localhost:5000/api/search")
    print("   Header: x-search-query: 10.1038/nature12373")
    print("3. GET http://localhost:5000/health")
    print("\nPress Ctrl+C to stop\n")

    app.run(debug=True, host="0.0.0.0", port=5000)
