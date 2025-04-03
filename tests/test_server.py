import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import os
import sys
import uuid

# Add the app directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
app_dir = os.path.join(parent_dir, "app")
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

class TestMCPServer:
    """Test the MCP server functionality."""
    
    def test_server_version(self):
        """Test that the server has a version attribute."""
        # Import the server module directly without mocking
        # This ensures we're testing the actual code
        from app.server import mcp
        
        # All MCP servers should have a name, and it should be "Hass-MCP"
        assert hasattr(mcp, "name")
        assert mcp.name == "Hass-MCP"

    def test_async_handler_decorator(self):
        """Test the async_handler decorator."""
        # Import the decorator
        from app.server import async_handler
        
        # Create a test async function
        async def test_func(arg1, arg2=None):
            return f"{arg1}_{arg2}"
        
        # Apply the decorator
        decorated_func = async_handler("test_command")(test_func)
        
        # Run the decorated function
        result = asyncio.run(decorated_func("val1", arg2="val2"))
        
        # Verify the result
        assert result == "val1_val2"
    
    def test_tool_functions_exist(self):
        """Test that tool functions exist in the server module."""
        # Import the server module directly
        import app.server
        
        # List of expected tool functions
        expected_tools = [
            "get_version",
            "get_entity", 
            "list_entities",
            "entity_action",
            "domain_summary_tool",  # Domain summaries tool
            "call_service_tool",
            "restart_ha",
            "list_automations"
        ]
        
        # Check that each expected tool function exists
        for tool_name in expected_tools:
            assert hasattr(app.server, tool_name)
            assert callable(getattr(app.server, tool_name))
    
    def test_resource_functions_exist(self):
        """Test that resource functions exist in the server module."""
        # Import the server module directly
        import app.server
        
        # List of expected resource functions - Use only the ones actually in server.py
        expected_resources = [
            "get_entity_resource", 
            "get_entity_resource_detailed",
            "get_all_entities_resource", 
            "list_states_by_domain_resource",     # Domain-specific resource
            "search_entities_resource_with_limit"  # Search resource with limit parameter
        ]
        
        # Check that each expected resource function exists
        for resource_name in expected_resources:
            assert hasattr(app.server, resource_name)
            assert callable(getattr(app.server, resource_name))
            
    @pytest.mark.asyncio
    async def test_list_automations_error_handling(self):
        """Test that list_automations handles errors properly."""
        from app.server import list_automations
        
        # Mock the get_automations function with different scenarios
        with patch("app.server.get_automations") as mock_get_automations:
            # Case 1: Test with 404 error response format (list with single dict with error key)
            mock_get_automations.return_value = [{"error": "HTTP error: 404 - Not Found"}]
            
            # Should return an empty list
            result = await list_automations()
            assert isinstance(result, list)
            assert len(result) == 0
            
            # Case 2: Test with dict error response
            mock_get_automations.return_value = {"error": "HTTP error: 404 - Not Found"}
            
            # Should return an empty list
            result = await list_automations()
            assert isinstance(result, list)
            assert len(result) == 0
            
            # Case 3: Test with unexpected error
            mock_get_automations.side_effect = Exception("Unexpected error")
            
            # Should return an empty list and log the error
            result = await list_automations()
            assert isinstance(result, list)
            assert len(result) == 0
            
            # Case 4: Test with successful response
            mock_automations = [
                {
                    "id": "morning_lights",
                    "entity_id": "automation.morning_lights",
                    "state": "on",
                    "alias": "Turn on lights in the morning"
                }
            ]
            mock_get_automations.side_effect = None
            mock_get_automations.return_value = mock_automations
            
            # Should return the automations list
            result = await list_automations()
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["id"] == "morning_lights"
            
    def test_tools_have_proper_docstrings(self):
        """Test that tool functions have proper docstrings"""
        # Import the server module directly
        import app.server
        
        # List of expected tool functions
        tool_functions = [
            "get_version",
            "get_entity", 
            "list_entities",
            "entity_action",
            "domain_summary_tool",
            "call_service_tool",
            "restart_ha",
            "list_automations",
            "search_entities_tool", 
            "system_overview",
            "get_error_log"
        ]
        
        # Check that each tool function has a proper docstring and exists
        for tool_name in tool_functions:
            assert hasattr(app.server, tool_name), f"{tool_name} function missing"
            tool_function = getattr(app.server, tool_name)
            assert tool_function.__doc__ is not None, f"{tool_name} missing docstring"
            assert len(tool_function.__doc__.strip()) > 10, f"{tool_name} has insufficient docstring"
    
    def test_prompt_functions_exist(self):
        """Test that prompt functions exist in the server module."""
        # Import the server module directly
        import app.server
        
        # List of expected prompt functions
        expected_prompts = [
            "create_automation",
            "debug_automation",
            "troubleshoot_entity"
        ]
        
        # Check that each expected prompt function exists
        for prompt_name in expected_prompts:
            assert hasattr(app.server, prompt_name)
            assert callable(getattr(app.server, prompt_name))
            
    @pytest.mark.asyncio
    async def test_search_entities_resource(self):
        """Test the search_entities_tool function"""
        from app.server import search_entities_tool
        
        # Mock the get_entities function with test data
        mock_entities = [
            {"entity_id": "light.living_room", "state": "on", "attributes": {"friendly_name": "Living Room Light", "brightness": 255}},
            {"entity_id": "light.kitchen", "state": "off", "attributes": {"friendly_name": "Kitchen Light"}}
        ]
        
        with patch("app.server.get_entities", return_value=mock_entities) as mock_get:
            # Test search with a valid query
            result = await search_entities_tool(query="living")
            
            # Verify the function was called with the right parameters including lean format
            mock_get.assert_called_once_with(search_query="living", limit=20, lean=True)
            
            # Check that the result contains the expected entity data
            assert result["count"] == 2
            assert any(e["entity_id"] == "light.living_room" for e in result["results"])
            assert result["query"] == "living"
            
            # Check that domain counts are included
            assert "domains" in result
            assert "light" in result["domains"]
            
            # Test with empty query (returns all entities instead of error)
            result = await search_entities_tool(query="")
            assert "error" not in result
            assert result["count"] > 0
            assert "all entities (no filtering)" in result["query"]
            
            # Test that simplified representation includes domain-specific attributes
            result = await search_entities_tool(query="living")
            assert any("brightness" in e for e in result["results"])
            
            # Test with custom limit as an integer
            mock_get.reset_mock()
            result = await search_entities_tool(query="light", limit=5)
            mock_get.assert_called_once_with(search_query="light", limit=5, lean=True)
            
            # Test with a different limit to ensure it's respected
            mock_get.reset_mock()
            result = await search_entities_tool(query="light", limit=10)
            mock_get.assert_called_once_with(search_query="light", limit=10, lean=True)
            
    @pytest.mark.asyncio
    async def test_domain_summary_tool(self):
        """Test the domain_summary_tool function"""
        from app.server import domain_summary_tool
        
        # Mock the summarize_domain function
        mock_summary = {
            "domain": "light",
            "total_count": 2,
            "state_distribution": {"on": 1, "off": 1},
            "examples": {
                "on": [{"entity_id": "light.living_room", "friendly_name": "Living Room Light"}],
                "off": [{"entity_id": "light.kitchen", "friendly_name": "Kitchen Light"}]
            },
            "common_attributes": [("friendly_name", 2), ("brightness", 1)]
        }
        
        with patch("app.server.summarize_domain", return_value=mock_summary) as mock_summarize:
            # Test the function
            result = await domain_summary_tool(domain="light", example_limit=3)
            
            # Verify the function was called with the right parameters
            mock_summarize.assert_called_once_with("light", 3)
            
            # Check that the result matches the mock data
            assert result == mock_summary
            
    @pytest.mark.asyncio        
    async def test_get_entity_with_field_filtering(self):
        """Test the get_entity function with field filtering"""
        from app.server import get_entity
        
        # Mock entity data
        mock_entity = {
            "entity_id": "light.living_room",
            "state": "on",
            "attributes": {
                "friendly_name": "Living Room Light",
                "brightness": 255,
                "color_temp": 370
            }
        }
        
        # Mock filtered entity data
        mock_filtered = {
            "entity_id": "light.living_room",
            "state": "on"
        }
        
        # Set up mock for get_entity_state to handle different calls
        with patch("app.server.get_entity_state") as mock_get_state:
            # Configure mock to return different responses based on parameters
            mock_get_state.return_value = mock_filtered
            
            # Test with field filtering
            result = await get_entity(entity_id="light.living_room", fields=["state"])
            
            # Verify the function call with fields parameter
            mock_get_state.assert_called_with("light.living_room", fields=["state"])
            assert result == mock_filtered
            
            # Test with detailed=True
            mock_get_state.reset_mock()
            mock_get_state.return_value = mock_entity
            result = await get_entity(entity_id="light.living_room", detailed=True)
            
            # Verify the function call with detailed parameter
            mock_get_state.assert_called_with("light.living_room", lean=False)
            assert result == mock_entity
            
            # Test default lean mode
            mock_get_state.reset_mock()
            mock_get_state.return_value = mock_filtered
            result = await get_entity(entity_id="light.living_room")
            
            # Verify the function call with lean=True parameter
            mock_get_state.assert_called_with("light.living_room", lean=True)
            assert result == mock_filtered

    @pytest.mark.asyncio
    async def test_mcp_tool_error_handling(self):
        """Test error handling for MCP tools."""
        from app.server import entity_action, get_entity, list_entities
        
        # Test invalid entity_id handling
        with patch("app.server.call_service") as mock_call_service:
            mock_call_service.side_effect = Exception("Entity not found")
            result = await entity_action(entity_id="non.existent", action="on")
            assert "error" in result
            assert "Entity not found" in result["error"]
        
        # Test invalid action handling
        result = await entity_action(entity_id="light.living_room", action="invalid_action")
        assert "error" in result
        assert "Invalid action" in result["error"]
        
        # Test get_entity with non-existent entity
        with patch("app.server.get_entity_state") as mock_get_state:
            mock_get_state.return_value = {"error": "Entity not found"}
            result = await get_entity(entity_id="non.existent")
            assert "error" in result
            assert "Entity not found" in result["error"]
            
        # Test list_entities with invalid domain
        result = await list_entities(domain="invalid_domain")
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_mcp_tool_edge_cases(self):
        """Test edge cases for MCP tools."""
        from app.server import entity_action, get_entity, list_entities, search_entities_tool
        
        # Test empty search query
        result = await search_entities_tool(query="")
        assert "results" in result
        assert isinstance(result["results"], list)
        
        # Test extremely long entity_id
        long_entity_id = "light." + "a" * 256
        result = await get_entity(entity_id=long_entity_id)
        assert "error" in result
        
        # Test with special characters in entity_id
        special_entity_id = "light.living_room#$%"
        result = await get_entity(entity_id=special_entity_id)
        assert "error" in result
        
        # Test list_entities with extremely large limit
        result = await list_entities(limit=1000000)
        assert isinstance(result, list)
        assert len(result) <= 1000  # Should be capped at a reasonable limit

    @pytest.mark.asyncio
    async def test_mcp_tool_performance(self):
        """Test performance aspects of MCP tools."""
        from app.server import list_entities, search_entities_tool
        import time
        
        # Test search performance
        start_time = time.time()
        result = await search_entities_tool(query="light")
        end_time = time.time()
        assert end_time - start_time < 2.0  # Should complete within 2 seconds
        
        # Test list_entities performance with different limits
        for limit in [10, 50, 100]:
            start_time = time.time()
            result = await list_entities(limit=limit)
            end_time = time.time()
            assert end_time - start_time < 1.0  # Should complete within 1 second
            assert len(result) <= limit

    @pytest.mark.asyncio
    async def test_mcp_tool_concurrent_access(self):
        """Test concurrent access to MCP tools."""
        from app.server import get_entity, list_entities
        
        # Test concurrent entity queries
        async def query_entity(entity_id):
            return await get_entity(entity_id=entity_id)
            
        # Run multiple queries concurrently
        entity_ids = ["light.living_room", "switch.kitchen", "sensor.temperature"]
        tasks = [query_entity(entity_id) for entity_id in entity_ids]
        results = await asyncio.gather(*tasks)
        
        # Verify results
        assert len(results) == len(entity_ids)
        assert all(isinstance(r, dict) for r in results)

    @pytest.mark.asyncio
    async def test_mcp_tool_state_consistency(self):
        """Test state consistency across different MCP tools."""
        from app.server import get_entity, list_entities, search_entities_tool
        
        # Get entity state through different methods
        entity_id = "light.living_room"
        
        # Direct entity query
        direct_result = await get_entity(entity_id=entity_id)
        
        # List entities filtered by domain
        list_result = await list_entities(domain="light")
        list_entity = next((e for e in list_result if e["entity_id"] == entity_id), None)
        
        # Search entities
        search_result = await search_entities_tool(query="living_room")
        search_entity = next((e for e in search_result["results"] if e["entity_id"] == entity_id), None)
        
        # Verify consistency if entity exists
        if "error" not in direct_result:
            assert list_entity is not None
            assert search_entity is not None
            assert direct_result["state"] == list_entity["state"]
            assert direct_result["state"] == search_entity["state"]