"""
Local development server for testing Azure Functions
This script creates a simple HTTP server to test the search functions locally
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

import azure.functions as func

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.search_functions.functions import search_openalex_list


class MockHttpRequest(Mock):
    """Mock Azure Functions HttpRequest for local testing"""

    def __init__(self, headers=None, method="GET", url="", params=None, body=b""):
        super().__init__(spec=func.HttpRequest)
        self.headers = headers or {}
        self.method = method
        self.url = url
        self.params = params or {}
        self._body = body

    def get_body(self):
        return self._body

    def get_json(self):
        if self._body:
            return json.loads(self._body.decode())
        return None


class SearchFunctionHandler(BaseHTTPRequestHandler):
    """HTTP request handler for testing search functions locally"""

    def do_GET(self):
        """Handle GET requests"""
        parsed_url = urlparse(self.path)

        if parsed_url.path == "/cite/search":
            self.handle_search_request()
        elif parsed_url.path == "/":
            self.serve_test_page()
        elif parsed_url.path == "/health":
            self.send_json_response(
                {"status": "healthy", "message": "Server is running"}
            )
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests"""
        parsed_url = urlparse(self.path)

        if parsed_url.path == "/cite/search":
            self.handle_search_request()
        else:
            self.send_error(404, "Not Found")

    def handle_search_request(self):
        """Handle search requests by calling the Azure Function"""
        try:
            # Get search query from header or query parameter
            search_query = None

            # Try to get from x-search-query header
            if "x-search-query" in self.headers:
                search_query = self.headers.get("x-search-query")

            # If not in header, try query parameter
            if not search_query:
                parsed_url = urlparse(self.path)
                query_params = parse_qs(parsed_url.query)
                if "q" in query_params:
                    search_query = query_params["q"][0]

            # Create mock Azure Function request
            headers = dict(self.headers)
            if search_query and "x-search-query" not in headers:
                headers["x-search-query"] = search_query

            mock_req = MockHttpRequest(headers=headers, method=self.command)

            # Call the Azure Function
            response = search_openalex_list(mock_req)

            # Send response
            self.send_response(response.status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header(
                "Access-Control-Allow-Headers", "Content-Type, x-search-query"
            )
            self.end_headers()

            self.wfile.write(response.get_body())

        except Exception as e:
            error_response = {"error": f"Server error: {str(e)}"}
            self.send_json_response(error_response, status_code=500)

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, x-search-query")
        self.end_headers()

    def serve_test_page(self):
        """Serve a simple HTML test page"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Search Functions Test Page</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 800px; margin: 0 auto; }
                .search-box { margin: 20px 0; }
                input[type="text"] { padding: 10px; width: 400px; font-size: 16px; }
                button { padding: 10px 20px; font-size: 16px; margin-left: 10px; }
                .results { margin: 20px 0; }
                .result-item { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .result-title { font-weight: bold; color: #0066cc; }
                .result-authors { color: #666; margin: 5px 0; }
                .result-venue { color: #888; font-style: italic; }
                .error { color: red; background: #ffe6e6; padding: 10px; border-radius: 5px; }
                .success { color: green; background: #e6ffe6; padding: 10px; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔍 Search Functions Test Page</h1>
                <p>Test the OpenAlex search functionality locally.</p>
                
                <div class="search-box">
                    <input type="text" id="searchQuery" placeholder="Enter search query or DOI..." />
                    <button onclick="performSearch()">Search</button>
                </div>
                
                <div class="search-box">
                    <h3>Quick Test Queries:</h3>
                    <button onclick="testQuery('machine learning')">Machine Learning</button>
                    <button onclick="testQuery('10.1038/nature12373')">Nature DOI</button>
                    <button onclick="testQuery('BERT transformer')">BERT Transformer</button>
                    <button onclick="testQuery('')">Empty Query (Error Test)</button>
                </div>
                
                <div id="status" class="results"></div>
                <div id="results" class="results"></div>
            </div>
            
            <script>
                function testQuery(query) {
                    document.getElementById('searchQuery').value = query;
                    performSearch();
                }
                
                function performSearch() {
                    const query = document.getElementById('searchQuery').value;
                    const statusDiv = document.getElementById('status');
                    const resultsDiv = document.getElementById('results');
                    
                    // Clear previous results
                    statusDiv.innerHTML = '<p>Searching...</p>';
                    resultsDiv.innerHTML = '';
                    
                    // Make request
                    fetch('/cite/search', {
                        method: 'GET',
                        headers: {
                            'x-search-query': query
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        // Show status
                        if (data.error) {
                            statusDiv.innerHTML = `<div class="error">Error: ${data.error}</div>`;
                        } else {
                            const statusClass = data.statusMessage === 'SUCCESS' ? 'success' : 'error';
                            statusDiv.innerHTML = `
                                <div class="${statusClass}">
                                    Status: ${data.statusMessage}<br>
                                    Message: ${data.message}<br>
                                    Query: "${data.query}"
                                </div>
                            `;
                        }
                        
                        // Show results
                        if (data.results && data.results.length > 0) {
                            let html = '<h3>Results:</h3>';
                            data.results.forEach((result, index) => {
                                html += `
                                    <div class="result-item">
                                        <div class="result-title">${result.title || 'No title'}</div>
                                        <div class="result-authors">Authors: ${result.authors.join(', ') || 'No authors'}</div>
                                        <div class="result-venue">Venue: ${result.venue || 'No venue'}</div>
                                        <div>Year: ${result.year || 'No year'}</div>
                                        <div>DOI: ${result.doi ? '<a href="' + result.doi + '" target="_blank">' + result.doi + '</a>' : 'No DOI'}</div>
                                    </div>
                                `;
                            });
                            resultsDiv.innerHTML = html;
                        }
                    })
                    .catch(error => {
                        statusDiv.innerHTML = `<div class="error">Network Error: ${error.message}</div>`;
                    });
                }
            </script>
        </body>
        </html>
        """

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def send_json_response(self, data, status_code=200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        json_data = json.dumps(data, ensure_ascii=False)
        self.wfile.write(json_data.encode())

    def log_message(self, format, *args):
        """Custom log message format"""
        print(f"[{self.date_time_string()}] {format % args}")


def run_server(port=8000):
    """Run the development server"""
    server_address = ("localhost", port)
    httpd = HTTPServer(server_address, SearchFunctionHandler)

    print(f"🚀 Starting development server at http://localhost:{port}")
    print(f"📊 Test page: http://localhost:{port}/")
    print(f"🔍 Search endpoint: http://localhost:{port}/cite/search")
    print(f"❤️  Health check: http://localhost:{port}/health")
    print("\nAPI Usage Examples:")
    print(
        f"  curl -H 'x-search-query: machine learning' http://localhost:{port}/cite/search"
    )
    print(f"  curl http://localhost:{port}/cite/search?q=BERT")
    print("\nPress Ctrl+C to stop the server\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
        httpd.shutdown()


if __name__ == "__main__":
    import sys

    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Invalid port number. Using default port 8000.")

    run_server(port)
