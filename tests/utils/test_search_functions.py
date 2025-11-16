"""
Test suite for SearchFunctions module
Tests the search_openalex_list function with various scenarios
"""

import json
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import azure.functions as func
import pytest

from modules.search_functions.functions import (_map_work_for_search_local,
                                                search_openalex_list)


class TestSearchOpenAlexList:
    """Test cases for search_openalex_list function"""

    def create_mock_request(self, search_query=None, headers=None):
        """Create a mock Azure Functions HttpRequest"""
        mock_req = Mock(spec=func.HttpRequest)

        # Set up headers
        if headers is None:
            headers = {}
        if search_query:
            headers["x-search-query"] = search_query

        mock_req.headers = headers
        return mock_req

    def test_missing_search_query_header(self):
        """Test when x-search-query header is missing"""
        mock_req = self.create_mock_request()

        response = search_openalex_list(mock_req)

        assert response.status_code == 400
        response_data = json.loads(response.get_body().decode())
        assert "error" in response_data
        assert "x-search-query header is required" in response_data["error"]

    def test_empty_search_query(self):
        """Test when x-search-query header is empty"""
        mock_req = self.create_mock_request(search_query="")

        response = search_openalex_list(mock_req)

        assert response.status_code == 400
        response_data = json.loads(response.get_body().decode())
        assert "error" in response_data

    def test_whitespace_only_query(self):
        """Test when x-search-query header contains only whitespace"""
        mock_req = self.create_mock_request(search_query="   ")

        response = search_openalex_list(mock_req)

        assert response.status_code == 400
        response_data = json.loads(response.get_body().decode())
        assert "error" in response_data

    @patch("modules.search_functions.functions.requests.get")
    def test_successful_title_search(self, mock_get):
        """Test successful search by title"""
        # Mock OpenAlex API response
        mock_response_data = {
            "results": [
                {
                    "title": "Machine Learning in Healthcare",
                    "doi_url": "https://doi.org/10.1000/test123",
                    "authorships": [
                        {"author": {"display_name": "John Doe"}},
                        {"author": {"display_name": "Jane Smith"}},
                    ],
                    "host_venue": {"display_name": "Nature Medicine"},
                    "publication_year": 2023,
                }
            ]
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_get.return_value = mock_response

        mock_req = self.create_mock_request(search_query="machine learning healthcare")

        response = search_openalex_list(mock_req)

        assert response.status_code == 200
        response_data = json.loads(response.get_body().decode())

        assert response_data["statusMessage"] == "SUCCESS"
        assert len(response_data["results"]) == 1
        assert response_data["results"][0]["title"] == "Machine Learning in Healthcare"
        assert response_data["results"][0]["doi"] == "https://doi.org/10.1000/test123"
        assert len(response_data["results"][0]["authors"]) == 2

    @patch("modules.search_functions.functions.requests.get")
    def test_successful_doi_search(self, mock_get):
        """Test successful search by DOI"""
        # Mock OpenAlex API response for DOI search
        mock_response_data = {
            "title": "Specific Research Paper",
            "doi_url": "https://doi.org/10.1000/specific123",
            "authorships": [{"author": {"display_name": "Research Author"}}],
            "host_venue": {"display_name": "Science Journal"},
            "publication_year": 2022,
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_get.return_value = mock_response

        mock_req = self.create_mock_request(search_query="10.1000/specific123")

        response = search_openalex_list(mock_req)

        assert response.status_code == 200
        response_data = json.loads(response.get_body().decode())

        assert response_data["statusMessage"] == "SUCCESS"
        assert len(response_data["results"]) == 1
        assert response_data["results"][0]["title"] == "Specific Research Paper"

    @patch("modules.search_functions.functions.requests.get")
    def test_no_results_found(self, mock_get):
        """Test when no results are found"""
        mock_response_data = {"results": []}

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_get.return_value = mock_response

        mock_req = self.create_mock_request(
            search_query="nonexistent research topic xyz123"
        )

        response = search_openalex_list(mock_req)

        assert response.status_code == 200
        response_data = json.loads(response.get_body().decode())

        assert response_data["statusMessage"] == "FAILURE"
        assert len(response_data["results"]) == 0
        assert "no results found" in response_data["message"]

    @patch("modules.search_functions.functions.requests.get")
    def test_api_error_handling(self, mock_get):
        """Test handling of API errors"""
        mock_get.side_effect = Exception("Network error")

        mock_req = self.create_mock_request(search_query="test query")

        response = search_openalex_list(mock_req)

        assert response.status_code == 200
        response_data = json.loads(response.get_body().decode())

        assert response_data["statusMessage"] == "FAILURE"
        assert len(response_data["results"]) == 0

    @patch("modules.search_functions.functions.requests.get")
    def test_api_404_response(self, mock_get):
        """Test handling of 404 response from API"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        mock_req = self.create_mock_request(search_query="test query")

        response = search_openalex_list(mock_req)

        assert response.status_code == 200
        response_data = json.loads(response.get_body().decode())

        assert response_data["statusMessage"] == "FAILURE"
        assert len(response_data["results"]) == 0

    def test_request_headers_exception(self):
        """Test when request.headers raises an exception"""
        mock_req = Mock(spec=func.HttpRequest)
        # Make headers property raise an exception
        type(mock_req).headers = PropertyMock(side_effect=Exception("Headers error"))

        response = search_openalex_list(mock_req)

        assert response.status_code == 400
        response_data = json.loads(response.get_body().decode())
        assert "error" in response_data


class TestMapWorkForSearchLocal:
    """Test cases for _map_work_for_search_local function"""

    def test_empty_work(self):
        """Test mapping empty work"""
        result = _map_work_for_search_local({})

        assert result["title"] == ""
        assert result["doi"] == ""
        assert result["authors"] == []
        assert result["venue"] == ""
        assert result["year"] is None

    def test_none_work(self):
        """Test mapping None work"""
        result = _map_work_for_search_local(None)

        assert result["title"] == ""
        assert result["doi"] == ""
        assert result["authors"] == []
        assert result["venue"] == ""
        assert result["year"] is None

    def test_complete_work_mapping(self):
        """Test mapping complete work data"""
        work = {
            "title": "Test Research Paper",
            "doi_url": "https://doi.org/10.1000/test123",
            "authorships": [
                {"author": {"display_name": "John Doe"}},
                {"author": {"display_name": "Jane Smith"}},
                {"author": {"display_name": "Bob Johnson"}},
            ],
            "host_venue": {"display_name": "Nature"},
            "publication_year": 2023,
        }

        result = _map_work_for_search_local(work)

        assert result["title"] == "Test Research Paper"
        assert result["doi"] == "https://doi.org/10.1000/test123"
        assert result["authors"] == ["John Doe", "Jane Smith", "Bob Johnson"]
        assert result["venue"] == "Nature"
        assert result["year"] == 2023

    def test_work_with_display_name(self):
        """Test mapping work with display_name instead of title"""
        work = {
            "display_name": "Alternative Title Field",
            "doi_url": "https://doi.org/10.1000/test456",
        }

        result = _map_work_for_search_local(work)

        assert result["title"] == "Alternative Title Field"

    def test_work_with_doi_in_ids(self):
        """Test mapping work with DOI in ids field"""
        work = {"title": "Test Paper", "ids": {"doi": "10.1000/test789"}}

        result = _map_work_for_search_local(work)

        assert result["doi"] == "https://doi.org/10.1000/test789"

    def test_work_with_plain_doi(self):
        """Test mapping work with plain DOI field"""
        work = {"title": "Test Paper", "doi": "10.1000/plain_doi"}

        result = _map_work_for_search_local(work)

        assert result["doi"] == "https://doi.org/10.1000/plain_doi"

    def test_work_with_many_authors(self):
        """Test mapping work with more than 20 authors (should limit to 20)"""
        authorships = [{"author": {"display_name": f"Author {i}"}} for i in range(25)]
        work = {"title": "Paper with Many Authors", "authorships": authorships}

        result = _map_work_for_search_local(work)

        assert len(result["authors"]) == 20
        assert result["authors"][0] == "Author 0"
        assert result["authors"][19] == "Author 19"

    def test_work_with_invalid_year(self):
        """Test mapping work with invalid publication year"""
        work = {"title": "Test Paper", "publication_year": "invalid_year"}

        result = _map_work_for_search_local(work)

        assert result["year"] is None

    def test_work_with_missing_author_names(self):
        """Test mapping work with authorships missing display_name"""
        work = {
            "title": "Test Paper",
            "authorships": [
                {"author": {"display_name": "Valid Author"}},
                {"author": {}},  # Missing display_name
                {"author": {"display_name": "Another Valid Author"}},
            ],
        }

        result = _map_work_for_search_local(work)

        assert result["authors"] == ["Valid Author", "Another Valid Author"]


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
