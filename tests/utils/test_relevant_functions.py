"""
Test suite for RelevantFunctions module
Tests the getRelevantWorks function with various scenarios
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import azure.functions as func
from modules.relevant_functions.functions import (
    getRelevantWorks,
    _extract_doi_id,
    _fetch_metadata_openalex,
    _query_pinecone_rest_by_text,
    getVectorById,
    mapVectorsToReferred
)


class TestRelevantWorks:
    """Test cases for relevant works functionality"""

    def create_mock_request(self, json_body=None, params=None):
        """Create a mock Azure Functions HttpRequest"""
        mock_req = Mock(spec=func.HttpRequest)
        
        if json_body is not None:
            mock_req.get_json.return_value = json_body
        else:
            mock_req.get_json.side_effect = ValueError("No JSON body")
        
        mock_req.params = params or {}
        return mock_req

    def test_get_relevant_works_success(self):
        """Test successful relevant works retrieval"""
        mock_req = self.create_mock_request(
            json_body={
                'doi': '10.1000/test123',
                'max_nodes': 10
            }
        )
        
        mock_metadata = {
            'title': 'Test Paper',
            'authors': ['Author 1'],
            'venue': 'Test Venue'
        }
        
        mock_matches = [
            {
                'id': 'work1',
                'score': 0.95
            }
        ]
        
        with patch('modules.relevant_functions.functions._fetch_metadata_openalex') as mock_fetch:
            mock_fetch.return_value = mock_metadata
            
            with patch('modules.relevant_functions.functions._query_pinecone_rest_by_text') as mock_query:
                mock_query.return_value = mock_matches
                
                with patch('modules.relevant_functions.functions.getVectorById') as mock_get_vectors:
                    mock_get_vectors.return_value = {}
                    
                    with patch('modules.relevant_functions.functions.mapVectorsToReferred') as mock_map:
                        mock_map.return_value = []
                        
                        response = getRelevantWorks(mock_req)
                        
                        assert response.status_code == 200
                        response_data = json.loads(response.get_body().decode())
                        assert response_data['statusMessage'] == 'SUCCESS'

    def test_missing_doi_parameter(self):
        """Test when DOI parameter is missing"""
        mock_req = self.create_mock_request(json_body={})
        
        response = getRelevantWorks(mock_req)
        
        assert response.status_code == 400
        response_data = json.loads(response.get_body().decode())
        assert response_data['statusMessage'] == 'ERROR'
        assert 'Missing doi' in response_data['message']

    def test_invalid_doi_parameter(self):
        """Test when DOI parameter is invalid"""
        mock_req = self.create_mock_request(
            json_body={'doi': 'invalid_doi'}
        )
        
        with patch('modules.relevant_functions.functions._extract_doi_id') as mock_extract:
            mock_extract.return_value = ''  # Invalid DOI
            
            response = getRelevantWorks(mock_req)
            
            assert response.status_code == 400
            response_data = json.loads(response.get_body().decode())
            assert response_data['statusMessage'] == 'ERROR'
            assert 'Unable to parse DOI' in response_data['message']

    def test_doi_from_params(self):
        """Test reading DOI from URL parameters"""
        mock_req = self.create_mock_request(
            params={'doi': '10.1000/test123', 'max_nodes': '5'}
        )
        
        mock_metadata = {'title': 'Test Paper'}
        mock_matches = []
        
        with patch('modules.relevant_functions.functions._fetch_metadata_openalex') as mock_fetch:
            mock_fetch.return_value = mock_metadata
            
            with patch('modules.relevant_functions.functions._query_pinecone_rest_by_text') as mock_query:
                mock_query.return_value = mock_matches
                
                with patch('modules.relevant_functions.functions.getVectorById') as mock_get_vectors:
                    mock_get_vectors.return_value = {}
                    
                    with patch('modules.relevant_functions.functions.mapVectorsToReferred') as mock_map:
                        mock_map.return_value = []
                        
                        response = getRelevantWorks(mock_req)
                        
                        assert response.status_code == 200
                        mock_query.assert_called_once_with('Test Paper', 5)

    def test_default_max_nodes_value(self):
        """Test default max_nodes value when not provided"""
        mock_req = self.create_mock_request(
            json_body={'doi': '10.1000/test123'}
        )
        
        mock_metadata = {'title': 'Test Paper'}
        
        with patch('modules.relevant_functions.functions._fetch_metadata_openalex') as mock_fetch:
            mock_fetch.return_value = mock_metadata
            
            with patch('modules.relevant_functions.functions._query_pinecone_rest_by_text') as mock_query:
                mock_query.return_value = []
                
                with patch('modules.relevant_functions.functions.getVectorById') as mock_get_vectors:
                    mock_get_vectors.return_value = {}
                    
                    with patch('modules.relevant_functions.functions.mapVectorsToReferred') as mock_map:
                        mock_map.return_value = []
                        
                        response = getRelevantWorks(mock_req)
                        
                        # Should use default max_nodes value (10, capped to 16)
                        mock_query.assert_called_once_with('Test Paper', 10)

    def test_invalid_max_nodes_parameter(self):
        """Test handling of invalid max_nodes parameter"""
        mock_req = self.create_mock_request(
            json_body={
                'doi': '10.1000/test123',
                'max_nodes': 'invalid_number'
            }
        )
        
        mock_metadata = {'title': 'Test Paper'}
        
        with patch('modules.relevant_functions.functions._fetch_metadata_openalex') as mock_fetch:
            mock_fetch.return_value = mock_metadata
            
            with patch('modules.relevant_functions.functions._query_pinecone_rest_by_text') as mock_query:
                mock_query.return_value = []
                
                with patch('modules.relevant_functions.functions.getVectorById') as mock_get_vectors:
                    mock_get_vectors.return_value = {}
                    
                    with patch('modules.relevant_functions.functions.mapVectorsToReferred') as mock_map:
                        mock_map.return_value = []
                        
                        response = getRelevantWorks(mock_req)
                        
                        # Should handle invalid number and use default
                        assert response.status_code == 200

    def test_metadata_fetch_failure(self):
        """Test when metadata fetch fails"""
        mock_req = self.create_mock_request(
            json_body={'doi': '10.1000/test123'}
        )
        
        with patch('modules.relevant_functions.functions._fetch_metadata_openalex') as mock_fetch:
            mock_fetch.return_value = {}  # No title
            
            response = getRelevantWorks(mock_req)
            
            assert response.status_code == 422
            response_data = json.loads(response.get_body().decode())
            assert response_data['statusMessage'] == 'ERROR'
            assert 'Could not extract a title' in response_data['message']

    def test_pinecone_query_failure(self):
        """Test when Pinecone query fails"""
        mock_req = self.create_mock_request(
            json_body={'doi': '10.1000/test123'}
        )
        
        mock_metadata = {'title': 'Test Paper'}
        
        with patch('modules.relevant_functions.functions._fetch_metadata_openalex') as mock_fetch:
            mock_fetch.return_value = mock_metadata
            
            with patch('modules.relevant_functions.functions._query_pinecone_rest_by_text') as mock_query:
                mock_query.side_effect = RuntimeError("Pinecone connection error")
                
                response = getRelevantWorks(mock_req)
                
                assert response.status_code == 502
                response_data = json.loads(response.get_body().decode())
                assert response_data['statusMessage'] == 'ERROR'
                assert 'Pinecone connection error' in response_data['message']

    def test_no_relevant_works_found(self):
        """Test when no relevant works are found"""
        mock_req = self.create_mock_request(
            json_body={'doi': '10.1000/test123'}
        )
        
        mock_metadata = {'title': 'Very Specific Paper'}
        
        with patch('modules.relevant_functions.functions._fetch_metadata_openalex') as mock_fetch:
            mock_fetch.return_value = mock_metadata
            
            with patch('modules.relevant_functions.functions._query_pinecone_rest_by_text') as mock_query:
                mock_query.return_value = []  # No matches
                
                with patch('modules.relevant_functions.functions.getVectorById') as mock_get_vectors:
                    mock_get_vectors.return_value = {}
                    
                    with patch('modules.relevant_functions.functions.mapVectorsToReferred') as mock_map:
                        mock_map.return_value = []
                        
                        response = getRelevantWorks(mock_req)
                        
                        assert response.status_code == 200
                        response_data = json.loads(response.get_body().decode())
                        assert response_data['statusMessage'] == 'SUCCESS'
                        assert response_data['count'] == 0

    def test_general_exception_handling(self):
        """Test handling of unexpected exceptions"""
        mock_req = self.create_mock_request()
        mock_req.get_json.side_effect = Exception("Unexpected error")
        
        response = getRelevantWorks(mock_req)
        
        assert response.status_code == 500
        response_data = json.loads(response.get_body().decode())
        assert response_data['statusMessage'] == 'ERROR'
        assert response_data['message'] == 'Internal server error'


class TestExtractDoiId:
    """Test cases for DOI extraction helper function"""

    def test_extract_doi_id_from_url(self):
        """Test extracting DOI ID from full URL"""
        result = _extract_doi_id('https://doi.org/10.1000/test123')
        assert result == '10.1000/test123'

    def test_extract_doi_id_from_plain_doi(self):
        """Test extracting DOI ID from plain DOI"""
        result = _extract_doi_id('10.1000/test123')
        assert result == '10.1000/test123'

    def test_extract_doi_id_empty_input(self):
        """Test with empty input"""
        result = _extract_doi_id('')
        assert result == ''
        
        result = _extract_doi_id(None)
        assert result == ''

    def test_extract_doi_id_malformed_url(self):
        """Test with malformed DOI URL"""
        result = _extract_doi_id('https://doi.org/')
        # Should return original string if no DOI after doi.org/
        assert result is not None


class TestFetchMetadataOpenAlex:
    """Test cases for OpenAlex metadata fetching helper function"""

    @patch('modules.relevant_functions.functions.requests.get')
    def test_fetch_metadata_success(self, mock_get):
        """Test successful metadata fetch"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'title': 'Test Paper',
            'authorships': [{'author': {'display_name': 'Test Author'}}]
        }
        mock_get.return_value = mock_response
        
        result = _fetch_metadata_openalex('10.1000/test123')
        
        assert 'title' in result
        mock_get.assert_called_once()

    @patch('modules.relevant_functions.functions.requests.get')
    def test_fetch_metadata_not_found(self, mock_get):
        """Test metadata fetch when paper not found"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = _fetch_metadata_openalex('10.1000/nonexistent')
        
        assert result == {}

    @patch('modules.relevant_functions.functions.requests.get')
    def test_fetch_metadata_api_error(self, mock_get):
        """Test metadata fetch API error"""
        mock_get.side_effect = Exception("API error")
        
        result = _fetch_metadata_openalex('10.1000/test123')
        
        # Should handle exceptions gracefully
        assert isinstance(result, dict)


class TestQueryPineconeRestByText:
    """Test cases for Pinecone REST text query helper function"""

    @patch('modules.relevant_functions.functions.requests.post')
    def test_query_pinecone_rest_success(self, mock_post):
        """Test successful Pinecone REST query"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'matches': [
                {'id': 'work1', 'score': 0.95}
            ]
        }
        mock_post.return_value = mock_response
        
        result = _query_pinecone_rest_by_text('machine learning', 10)
        
        assert len(result) == 1
        assert result[0]['score'] == 0.95

    @patch('modules.relevant_functions.functions.requests.post')
    def test_query_pinecone_rest_no_matches(self, mock_post):
        """Test Pinecone REST query with no matches"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'matches': []}
        mock_post.return_value = mock_response
        
        result = _query_pinecone_rest_by_text('very rare topic', 10)
        
        assert result == []

    @patch('modules.relevant_functions.functions.requests.post')
    def test_query_pinecone_rest_api_error(self, mock_post):
        """Test Pinecone REST API error"""
        mock_post.side_effect = Exception("Connection error")
        
        with pytest.raises(Exception):
            _query_pinecone_rest_by_text('test', 10)


class TestGetVectorById:
    """Test cases for vector retrieval helper function"""

    @patch('modules.relevant_functions.functions.requests.post')
    def test_get_vector_by_id_success(self, mock_post):
        """Test successful vector retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'vectors': {
                'work1': {'values': [0.1, 0.2, 0.3]}
            }
        }
        mock_post.return_value = mock_response
        
        result = getVectorById(['work1'])
        
        assert 'work1' in result
        assert 'values' in result['work1']

    @patch('modules.relevant_functions.functions.requests.post')
    def test_get_vector_by_id_empty_list(self, mock_post):
        """Test vector retrieval with empty ID list"""
        result = getVectorById([])
        
        assert result == {}
        # Should not make API call for empty list

    @patch('modules.relevant_functions.functions.requests.post')
    def test_get_vector_by_id_api_error(self, mock_post):
        """Test vector retrieval API error"""
        mock_post.side_effect = Exception("API error")
        
        result = getVectorById(['work1'])
        
        # Should handle errors gracefully
        assert isinstance(result, dict)


class TestMapVectorsToReferred:
    """Test cases for mapping vectors to referred papers helper function"""

    def test_map_vectors_to_referred_success(self):
        """Test successful mapping of vectors to referred papers"""
        referred = [
            {'id': 'work1', 'title': 'Paper 1'},
            {'id': 'work2', 'title': 'Paper 2'}
        ]
        vectors = {
            'work1': {'values': [0.1, 0.2]},
            'work2': {'values': [0.3, 0.4]}
        }
        
        result = mapVectorsToReferred(referred, vectors)
        
        assert len(result) == 2
        # Should add vector data to referred papers

    def test_map_vectors_to_referred_missing_vectors(self):
        """Test mapping when some vectors are missing"""
        referred = [
            {'id': 'work1', 'title': 'Paper 1'},
            {'id': 'work2', 'title': 'Paper 2'}
        ]
        vectors = {
            'work1': {'values': [0.1, 0.2]}
            # work2 vector missing
        }
        
        result = mapVectorsToReferred(referred, vectors)
        
        assert len(result) == 2
        # Should handle missing vectors gracefully

    def test_map_vectors_to_referred_empty_inputs(self):
        """Test mapping with empty inputs"""
        result = mapVectorsToReferred([], {})
        
        assert result == []


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
