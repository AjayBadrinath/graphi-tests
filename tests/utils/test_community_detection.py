"""
Test suite for CommunityDetection module
Tests the detectCommunities function with various scenarios
"""
import json
import pytest
from unittest.mock import Mock, patch
import azure.functions as func
from modules.communityDetection.functions import (
    detectCommunities, 
    _to_float_list, 
    _cosine_similarity, 
    UnionFind
)


class TestCommunityDetection:
    """Test cases for detectCommunities function"""

    def create_mock_request(self, json_body=None):
        """Create a mock Azure Functions HttpRequest"""
        mock_req = Mock(spec=func.HttpRequest)
        
        if json_body is not None:
            mock_req.get_json.return_value = json_body
        else:
            mock_req.get_json.side_effect = ValueError("No JSON body")
            
        return mock_req

    def test_missing_json_body(self):
        """Test when no JSON body is provided"""
        mock_req = self.create_mock_request()
        
        response = detectCommunities(mock_req)
        
        assert response.status_code == 400
        response_data = json.loads(response.get_body().decode())
        assert response_data['statusMessage'] == 'ERROR'
        assert 'Missing or invalid JSON body' in response_data['message']

    def test_empty_json_body(self):
        """Test when JSON body is empty"""
        mock_req = self.create_mock_request(json_body={})
        
        response = detectCommunities(mock_req)
        
        assert response.status_code == 400
        response_data = json.loads(response.get_body().decode())
        assert response_data['statusMessage'] == 'ERROR'
        assert 'Missing or invalid JSON body' in response_data['message']

    def test_no_valid_vectors(self):
        """Test when no valid vectors are found"""
        mock_req = self.create_mock_request(json_body={
            "threshold": 0.9,
            "invalid1": "not_a_list",
            "invalid2": None
        })
        
        response = detectCommunities(mock_req)
        
        assert response.status_code == 400
        response_data = json.loads(response.get_body().decode())
        assert response_data['statusMessage'] == 'ERROR'
        assert 'No valid vectors found' in response_data['message']

    def test_single_community_high_similarity(self):
        """Test when all vectors are highly similar (single community)"""
        # Very similar vectors (should form one community)
        mock_req = self.create_mock_request(json_body={
            "paper1": [1.0, 0.9, 0.8],
            "paper2": [0.95, 0.85, 0.75],
            "paper3": [0.9, 0.8, 0.7],
            "threshold": 0.8
        })
        
        response = detectCommunities(mock_req)
        
        assert response.status_code == 200
        response_data = json.loads(response.get_body().decode())
        assert response_data['statusMessage'] == 'SUCCESS'
        assert response_data['communityCount'] == 1
        
        # All papers should be in the same community (community 0)
        result = response_data['result']
        assert result['paper1'] == result['paper2'] == result['paper3']

    def test_multiple_communities(self):
        """Test when vectors form multiple distinct communities"""
        # Two groups of similar vectors
        mock_req = self.create_mock_request(json_body={
            "paper1": [1.0, 0.0, 0.0],  # Group 1
            "paper2": [0.9, 0.1, 0.0],  # Group 1  
            "paper3": [0.0, 1.0, 0.0],  # Group 2
            "paper4": [0.0, 0.9, 0.1],  # Group 2
            "threshold": 0.7
        })
        
        response = detectCommunities(mock_req)
        
        assert response.status_code == 200
        response_data = json.loads(response.get_body().decode())
        assert response_data['statusMessage'] == 'SUCCESS'
        assert response_data['communityCount'] == 2
        
        result = response_data['result']
        # Papers 1&2 should be in same community, papers 3&4 in another
        assert result['paper1'] == result['paper2']
        assert result['paper3'] == result['paper4'] 
        assert result['paper1'] != result['paper3']

    def test_no_communities_low_threshold(self):
        """Test when threshold is too high, creating separate communities"""
        mock_req = self.create_mock_request(json_body={
            "paper1": [1.0, 0.0, 0.0],
            "paper2": [0.0, 1.0, 0.0], 
            "paper3": [0.0, 0.0, 1.0],
            "threshold": 0.99  # Very high threshold
        })
        
        response = detectCommunities(mock_req)
        
        assert response.status_code == 200
        response_data = json.loads(response.get_body().decode())
        assert response_data['statusMessage'] == 'SUCCESS'
        assert response_data['communityCount'] == 3  # Each paper in its own community
        
        result = response_data['result']
        # All papers should be in different communities
        communities = set(result.values())
        assert len(communities) == 3

    def test_default_threshold(self):
        """Test that default threshold of 0.9 is used when not specified"""
        mock_req = self.create_mock_request(json_body={
            "paper1": [1.0, 0.0, 0.0],
            "paper2": [0.95, 0.0, 0.0]  # High similarity, should group with default 0.9
        })
        
        response = detectCommunities(mock_req)
        
        assert response.status_code == 200
        response_data = json.loads(response.get_body().decode())
        assert response_data['statusMessage'] == 'SUCCESS'
        assert response_data['communityCount'] == 1

    def test_invalid_threshold_fallback(self):
        """Test that invalid threshold falls back to 0.9"""
        mock_req = self.create_mock_request(json_body={
            "paper1": [1.0, 0.0, 0.0],
            "paper2": [0.95, 0.0, 0.0],
            "threshold": "invalid_threshold"
        })
        
        response = detectCommunities(mock_req)
        
        assert response.status_code == 200
        response_data = json.loads(response.get_body().decode())
        assert response_data['statusMessage'] == 'SUCCESS'
        # Should use default threshold 0.9

    def test_inconsistent_vector_dimensions(self):
        """Test handling of vectors with different dimensions"""
        mock_req = self.create_mock_request(json_body={
            "paper1": [1.0, 0.0],        # 2D
            "paper2": [0.0, 1.0, 0.0],   # 3D  
            "paper3": [1.0, 0.0],        # 2D
            "threshold": 0.8
        })
        
        response = detectCommunities(mock_req)
        
        assert response.status_code == 200
        response_data = json.loads(response.get_body().decode())
        assert response_data['statusMessage'] == 'SUCCESS'
        # Should still work, only comparing vectors of same dimension

    def test_exception_handling(self):
        """Test that exceptions are properly handled"""
        mock_req = Mock(spec=func.HttpRequest)
        mock_req.get_json.side_effect = Exception("Unexpected error")
        
        response = detectCommunities(mock_req)
        
        assert response.status_code == 500
        response_data = json.loads(response.get_body().decode())
        assert response_data['statusMessage'] == 'ERROR'
        assert response_data['message'] == 'Internal server error'


class TestHelperFunctions:
    """Test cases for helper functions"""

    def test_to_float_list_valid_numbers(self):
        """Test converting valid number list"""
        result = _to_float_list([1, 2.5, "3.0", "4"])
        assert result == [1.0, 2.5, 3.0, 4.0]

    def test_to_float_list_mixed_valid_invalid(self):
        """Test converting mixed valid/invalid values"""
        result = _to_float_list([1, "invalid", 3.0, None, "5"])
        assert result == [1.0, 3.0, 5.0]

    def test_to_float_list_empty_input(self):
        """Test with empty input"""
        assert _to_float_list([]) == []
        assert _to_float_list(None) == []
        assert _to_float_list("not_a_list") == []

    def test_cosine_similarity_identical_vectors(self):
        """Test cosine similarity of identical vectors"""
        vec = [1.0, 2.0, 3.0]
        similarity = _cosine_similarity(vec, vec)
        assert abs(similarity - 1.0) < 1e-10  # Should be 1.0

    def test_cosine_similarity_orthogonal_vectors(self):
        """Test cosine similarity of orthogonal vectors"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = _cosine_similarity(vec1, vec2)
        assert abs(similarity - 0.0) < 1e-10  # Should be 0.0

    def test_cosine_similarity_opposite_vectors(self):
        """Test cosine similarity of opposite vectors"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = _cosine_similarity(vec1, vec2)
        assert abs(similarity - (-1.0)) < 1e-10  # Should be -1.0

    def test_cosine_similarity_empty_vectors(self):
        """Test cosine similarity with empty or mismatched vectors"""
        assert _cosine_similarity([], [1, 2, 3]) == 0.0
        assert _cosine_similarity([1, 2], [1, 2, 3]) == 0.0
        assert _cosine_similarity([], []) == 0.0

    def test_cosine_similarity_zero_vectors(self):
        """Test cosine similarity with zero vectors"""
        zero_vec = [0.0, 0.0, 0.0]
        normal_vec = [1.0, 2.0, 3.0]
        similarity = _cosine_similarity(zero_vec, normal_vec)
        assert similarity == 0.0


class TestUnionFind:
    """Test cases for UnionFind data structure"""

    def test_union_find_basic_operations(self):
        """Test basic union-find operations"""
        uf = UnionFind()
        
        # Initially, each element is its own parent
        assert uf.find("a") == "a"
        assert uf.find("b") == "b"
        
        # Union two elements
        uf.union("a", "b")
        root_a = uf.find("a")
        root_b = uf.find("b")
        assert root_a == root_b  # Should have same root

    def test_union_find_multiple_groups(self):
        """Test union-find with multiple groups"""
        uf = UnionFind()
        
        # Create two separate groups
        uf.union("a", "b")
        uf.union("c", "d")
        
        # Elements in same group should have same root
        assert uf.find("a") == uf.find("b")
        assert uf.find("c") == uf.find("d")
        
        # Elements in different groups should have different roots
        assert uf.find("a") != uf.find("c")

    def test_union_find_path_compression(self):
        """Test that path compression works correctly"""
        uf = UnionFind()
        
        # Create a chain: a -> b -> c
        uf.union("a", "b")
        uf.union("b", "c")
        
        # All should have same root
        root = uf.find("a")
        assert uf.find("b") == root
        assert uf.find("c") == root

    def test_union_find_duplicate_union(self):
        """Test unioning elements already in same set"""
        uf = UnionFind()
        
        uf.union("a", "b")
        root_before = uf.find("a")
        
        # Union again - should not change anything
        uf.union("a", "b")
        root_after = uf.find("a")
        
        assert root_before == root_after


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
