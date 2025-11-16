"""
Test suite for ProcessFunctions module
Tests the getReferences and getCitating functions with various scenarios
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import azure.functions as func
from modules.process_functions.functions import (
    getReferences,
    getCitating,
    _handle_get_papers,
    _extract_doi_id
)


class TestProcessFunctions:
    """Test cases for process functions"""

    def create_mock_request(self, json_body=None, params=None, body_bytes=None):
        """Create a mock Azure Functions HttpRequest"""
        mock_req = Mock(spec=func.HttpRequest)
        
        # Set up JSON body
        if json_body is not None:
            mock_req.get_json.return_value = json_body
        else:
            mock_req.get_json.side_effect = ValueError("No JSON body")
        
        # Set up query parameters
        mock_req.params = params or {}
        
        # Set up raw body
        if body_bytes is not None:
            mock_req.get_body.return_value = body_bytes
        else:
            mock_req.get_body.return_value = b''
            
        return mock_req

    def test_get_references_delegates_correctly(self):
        """Test that getReferences delegates to _handle_get_papers with correct requestFor"""
        with patch('modules.process_functions.functions._handle_get_papers') as mock_handle:
            mock_req = self.create_mock_request()
            mock_response = Mock()
            mock_handle.return_value = mock_response
            
            result = getReferences(mock_req)
            
            mock_handle.assert_called_once_with(mock_req, requestFor='references')
            assert result == mock_response

    def test_get_citating_delegates_correctly(self):
        """Test that getCitating delegates to _handle_get_papers with correct requestFor"""
        with patch('modules.process_functions.functions._handle_get_papers') as mock_handle:
            mock_req = self.create_mock_request()
            mock_response = Mock()
            mock_handle.return_value = mock_response
            
            result = getCitating(mock_req)
            
            mock_handle.assert_called_once_with(mock_req, requestFor='citating')
            assert result == mock_response

    def test_missing_doi_in_request(self):
        """Test when DOI is missing from both JSON body and params"""
        mock_req = self.create_mock_request(json_body={}, params={})
        
        response = _handle_get_papers(mock_req, requestFor='references')
        
        assert response.status_code == 400
        response_data = json.loads(response.get_body().decode())
        assert response_data['statusMessage'] == 'ERROR'
        assert 'Missing doi in request' in response_data['message']

    def test_invalid_request_type(self):
        """Test when requestType is invalid"""
        mock_req = self.create_mock_request(
            json_body={
                'doi': '10.1000/test123',
                'requestType': 'invalid_type'
            }
        )
        
        response = _handle_get_papers(mock_req, requestFor='references')
        
        assert response.status_code == 400
        response_data = json.loads(response.get_body().decode())
        assert response_data['statusMessage'] == 'ERROR'
        assert 'Invalid requestType' in response_data['message']

    def test_valid_new_request_from_json(self):
        """Test valid 'new' request from JSON body"""
        mock_req = self.create_mock_request(
            json_body={
                'doi': '10.1000/test123',
                'requestType': 'new',
                'max_nodes': 50,
                'max_depth': 3
            }
        )
        
        with patch('modules.process_functions.functions._extract_doi_id') as mock_extract:
            mock_extract.return_value = '10.1000/test123'
            
            with patch('modules.process_functions.functions.redis_client') as mock_redis:
                mock_redis.get.return_value = None  # Not in Redis
                
                with patch('modules.process_functions.functions.cosmos_client') as mock_cosmos:
                    mock_cosmos.get_item.side_effect = Exception("Not found")  # Not in Cosmos
                    
                    with patch('modules.process_functions.functions.requests.post') as mock_post:
                        mock_post.return_value.status_code = 202
                        
                        response = _handle_get_papers(mock_req, requestFor='references')
                        
                        assert response.status_code == 202
                        response_data = json.loads(response.get_body().decode())
                        assert response_data['statusMessage'] == 'ACCEPTED'

    def test_valid_new_request_from_params(self):
        """Test valid 'new' request from query parameters"""
        mock_req = self.create_mock_request(
            params={
                'doi': '10.1000/test123',
                'requestType': 'new'
            }
        )
        
        with patch('modules.process_functions.functions._extract_doi_id') as mock_extract:
            mock_extract.return_value = '10.1000/test123'
            
            with patch('modules.process_functions.functions.redis_client') as mock_redis:
                mock_redis.get.return_value = None
                
                with patch('modules.process_functions.functions.cosmos_client') as mock_cosmos:
                    mock_cosmos.get_item.side_effect = Exception("Not found")
                    
                    with patch('modules.process_functions.functions.requests.post') as mock_post:
                        mock_post.return_value.status_code = 202
                        
                        response = _handle_get_papers(mock_req, requestFor='references')
                        
                        assert response.status_code == 202
                        response_data = json.loads(response.get_body().decode())
                        assert response_data['statusMessage'] == 'ACCEPTED'

    def test_follow_request_redis_found(self):
        """Test 'follow' request when data is found in Redis"""
        mock_req = self.create_mock_request(
            json_body={
                'doi': '10.1000/test123',
                'requestType': 'follow'
            }
        )
        
        redis_data = {
            'statusMessage': 'SUCCESS',
            'message': 'Processing complete',
            'result': {'paper1': {'title': 'Test Paper'}}
        }
        
        with patch('modules.process_functions.functions._extract_doi_id') as mock_extract:
            mock_extract.return_value = '10.1000/test123'
            
            with patch('modules.process_functions.functions.redis_client') as mock_redis:
                mock_redis.get.return_value = json.dumps(redis_data)
                
                response = _handle_get_papers(mock_req, requestFor='references')
                
                assert response.status_code == 200
                response_data = json.loads(response.get_body().decode())
                assert response_data['statusMessage'] == 'SUCCESS'
                assert 'result' in response_data

    def test_follow_request_cosmos_found(self):
        """Test 'follow' request when data is found in Cosmos (not Redis)"""
        mock_req = self.create_mock_request(
            json_body={
                'doi': '10.1000/test123',
                'requestType': 'follow'
            }
        )
        
        cosmos_data = {
            'statusMessage': 'SUCCESS',
            'result': {'paper1': {'title': 'Test Paper'}}
        }
        
        with patch('modules.process_functions.functions._extract_doi_id') as mock_extract:
            mock_extract.return_value = '10.1000/test123'
            
            with patch('modules.process_functions.functions.redis_client') as mock_redis:
                mock_redis.get.return_value = None  # Not in Redis
                
                with patch('modules.process_functions.functions.cosmos_client') as mock_cosmos:
                    mock_cosmos.get_item.return_value = cosmos_data
                    
                    response = _handle_get_papers(mock_req, requestFor='references')
                    
                    assert response.status_code == 200
                    response_data = json.loads(response.get_body().decode())
                    assert response_data['statusMessage'] == 'SUCCESS'

    def test_follow_request_not_found(self):
        """Test 'follow' request when data is not found anywhere"""
        mock_req = self.create_mock_request(
            json_body={
                'doi': '10.1000/test123',
                'requestType': 'follow'
            }
        )
        
        with patch('modules.process_functions.functions._extract_doi_id') as mock_extract:
            mock_extract.return_value = '10.1000/test123'
            
            with patch('modules.process_functions.functions.redis_client') as mock_redis:
                mock_redis.get.return_value = None
                
                with patch('modules.process_functions.functions.cosmos_client') as mock_cosmos:
                    mock_cosmos.get_item.side_effect = Exception("Not found")
                    
                    response = _handle_get_papers(mock_req, requestFor='references')
                    
                    assert response.status_code == 404
                    response_data = json.loads(response.get_body().decode())
                    assert response_data['statusMessage'] == 'NOT_FOUND'

    def test_invalid_doi_format(self):
        """Test when DOI cannot be parsed"""
        mock_req = self.create_mock_request(
            json_body={
                'doi': 'invalid_doi_format',
                'requestType': 'new'
            }
        )
        
        with patch('modules.process_functions.functions._extract_doi_id') as mock_extract:
            mock_extract.return_value = None  # Failed to parse
            
            response = _handle_get_papers(mock_req, requestFor='references')
            
            assert response.status_code == 400
            response_data = json.loads(response.get_body().decode())
            assert response_data['statusMessage'] == 'ERROR'
            assert 'Unable to parse DOI' in response_data['message']

    def test_numeric_parameters_parsing(self):
        """Test that max_nodes and max_depth are properly parsed"""
        mock_req = self.create_mock_request(
            json_body={
                'doi': '10.1000/test123',
                'requestType': 'new',
                'max_nodes': '100',  # String numbers
                'max_depth': '5'
            }
        )
        
        with patch('modules.process_functions.functions._extract_doi_id') as mock_extract:
            mock_extract.return_value = '10.1000/test123'
            
            with patch('modules.process_functions.functions.redis_client') as mock_redis:
                mock_redis.get.return_value = None
                
                with patch('modules.process_functions.functions.cosmos_client') as mock_cosmos:
                    mock_cosmos.get_item.side_effect = Exception("Not found")
                    
                    with patch('modules.process_functions.functions.requests.post') as mock_post:
                        mock_post.return_value.status_code = 202
                        
                        response = _handle_get_papers(mock_req, requestFor='references')
                        
                        assert response.status_code == 202
                        # Should handle string numbers correctly

    def test_invalid_numeric_parameters(self):
        """Test handling of invalid numeric parameters"""
        mock_req = self.create_mock_request(
            json_body={
                'doi': '10.1000/test123',
                'requestType': 'new',
                'max_nodes': 'invalid_number',
                'max_depth': None
            }
        )
        
        with patch('modules.process_functions.functions._extract_doi_id') as mock_extract:
            mock_extract.return_value = '10.1000/test123'
            
            with patch('modules.process_functions.functions.redis_client') as mock_redis:
                mock_redis.get.return_value = None
                
                with patch('modules.process_functions.functions.cosmos_client') as mock_cosmos:
                    mock_cosmos.get_item.side_effect = Exception("Not found")
                    
                    with patch('modules.process_functions.functions.requests.post') as mock_post:
                        mock_post.return_value.status_code = 202
                        
                        response = _handle_get_papers(mock_req, requestFor='references')
                        
                        assert response.status_code == 202
                        # Should handle invalid numbers gracefully

    def test_exception_handling(self):
        """Test that exceptions are properly handled"""
        mock_req = self.create_mock_request()
        mock_req.get_json.side_effect = Exception("Unexpected error")
        mock_req.get_body.side_effect = Exception("Body error")
        
        response = _handle_get_papers(mock_req, requestFor='references')
        
        assert response.status_code == 500
        response_data = json.loads(response.get_body().decode())
        assert response_data['statusMessage'] == 'ERROR'
        assert response_data['message'] == 'Internal server error'

    def test_request_type_case_insensitive(self):
        """Test that request type is case insensitive"""
        mock_req = self.create_mock_request(
            json_body={
                'doi': '10.1000/test123',
                'requestType': 'NEW'  # Uppercase
            }
        )
        
        with patch('modules.process_functions.functions._extract_doi_id') as mock_extract:
            mock_extract.return_value = '10.1000/test123'
            
            with patch('modules.process_functions.functions.redis_client') as mock_redis:
                mock_redis.get.return_value = None
                
                with patch('modules.process_functions.functions.cosmos_client') as mock_cosmos:
                    mock_cosmos.get_item.side_effect = Exception("Not found")
                    
                    with patch('modules.process_functions.functions.requests.post') as mock_post:
                        mock_post.return_value.status_code = 202
                        
                        response = _handle_get_papers(mock_req, requestFor='references')
                        
                        assert response.status_code == 202


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

    def test_extract_doi_id_with_doi_prefix(self):
        """Test extracting DOI ID with doi: prefix"""
        result = _extract_doi_id('doi:10.1000/test123')
        assert result == '10.1000/test123'

    def test_extract_doi_id_invalid_format(self):
        """Test with invalid DOI format"""
        result = _extract_doi_id('invalid_doi_format')
        assert result is None or result == ''

    def test_extract_doi_id_empty_input(self):
        """Test with empty input"""
        result = _extract_doi_id('')
        assert result is None or result == ''
        
        result = _extract_doi_id(None)
        assert result is None or result == ''


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
