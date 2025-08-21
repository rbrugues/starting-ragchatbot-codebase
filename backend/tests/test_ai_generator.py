import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai_generator import AIGenerator


class TestAIGenerator:
    """Test cases for AIGenerator class"""

    def test_initialization_with_valid_api_key(self):
        """Test AIGenerator initializes correctly with valid API key"""
        generator = AIGenerator("valid-api-key", "claude-sonnet-4-20250514")
        assert generator.api_key == "valid-api-key"
        assert generator.model == "claude-sonnet-4-20250514"
        assert generator.use_mock == False
        assert hasattr(generator, "client")

    def test_initialization_without_api_key(self):
        """Test AIGenerator initialization without API key"""
        generator = AIGenerator("", "claude-sonnet-4-20250514")
        assert generator.api_key == ""
        assert generator.use_mock == True
        # This is the critical issue - client should not exist when use_mock is True
        assert not hasattr(generator, "client")

    def test_initialization_with_placeholder_api_key(self):
        """Test AIGenerator initialization with placeholder API key"""
        generator = AIGenerator(
            "your-anthropic-api-key-here", "claude-sonnet-4-20250514"
        )
        assert generator.use_mock == True
        assert not hasattr(generator, "client")

    def test_generate_response_without_api_key_uses_mock(self):
        """Test that mock response is used when no API key is provided"""
        generator = AIGenerator("", "claude-sonnet-4-20250514")

        # Should return mock response, not raise an error
        result = generator.generate_response("What is computer use?")

        # Verify the mock response is returned
        assert (
            result
            == "API key not configured. Please set your Anthropic API key to use this service."
        )

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_with_valid_api_key(self, mock_anthropic):
        """Test generate_response with valid API key"""
        # Mock the Anthropic client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_response.stop_reason = "stop"
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        generator = AIGenerator("valid-api-key", "claude-sonnet-4-20250514")
        result = generator.generate_response("Test query")

        assert result == "Test response"
        mock_client.messages.create.assert_called_once()

    def test_generate_response_with_tools_but_no_api_key(self):
        """Test generate_response with tools but no API key returns mock response"""
        generator = AIGenerator("", "claude-sonnet-4-20250514")

        mock_tools = [{"name": "test_tool", "description": "Test tool"}]
        mock_tool_manager = Mock()

        # Should return mock response, not raise an error
        result = generator.generate_response(
            "Test query", tools=mock_tools, tool_manager=mock_tool_manager
        )

        # Verify the mock response is returned
        assert (
            result
            == "API key not configured. Please set your Anthropic API key to use this service."
        )

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_execution_flow(self, mock_anthropic):
        """Test tool execution flow with valid API key"""
        # Mock the Anthropic client for tool use
        mock_client = Mock()

        # First response with tool use
        mock_tool_response = Mock()
        mock_tool_response.stop_reason = "tool_use"
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.input = {"query": "test"}
        mock_tool_block.id = "tool_123"
        mock_tool_response.content = [mock_tool_block]

        # Final response after tool execution
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Final response with tool results")]

        mock_client.messages.create.side_effect = [
            mock_tool_response,
            mock_final_response,
        ]
        mock_anthropic.return_value = mock_client

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool execution result"

        generator = AIGenerator("valid-api-key", "claude-sonnet-4-20250514")

        tools = [{"name": "search_course_content", "description": "Search tool"}]
        result = generator.generate_response(
            "Test query", tools=tools, tool_manager=mock_tool_manager
        )

        assert result == "Final response with tool results"
        assert mock_client.messages.create.call_count == 2
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="test"
        )

    def test_mock_response_method_exists_and_used(self):
        """Test that _generate_mock_response exists and is properly called"""
        generator = AIGenerator("", "claude-sonnet-4-20250514")

        # The method should exist
        assert hasattr(generator, "_generate_mock_response")

        # Calling generate_response should now use it (bug fixed)
        result = generator.generate_response("Test query")
        assert (
            result
            == "API key not configured. Please set your Anthropic API key to use this service."
        )

    def test_system_prompt_configuration(self):
        """Test that system prompt is properly configured"""
        generator = AIGenerator("valid-api-key", "claude-sonnet-4-20250514")

        assert hasattr(generator, "SYSTEM_PROMPT")
        assert "course materials" in generator.SYSTEM_PROMPT.lower()
        assert "content search tool" in generator.SYSTEM_PROMPT.lower()
        assert "course outline tool" in generator.SYSTEM_PROMPT.lower()
        assert "multi-round tool usage" in generator.SYSTEM_PROMPT.lower()
        assert "up to 2 rounds" in generator.SYSTEM_PROMPT.lower()

    @patch("ai_generator.anthropic.Anthropic")
    def test_multi_round_tool_calling_two_rounds(self, mock_anthropic):
        """Test successful two-round tool execution"""
        mock_client = Mock()

        # Round 1: Tool use response
        mock_round1_response = Mock()
        mock_round1_response.stop_reason = "tool_use"
        mock_tool_block1 = Mock()
        mock_tool_block1.type = "tool_use"
        mock_tool_block1.name = "get_course_outline"
        mock_tool_block1.input = {"course_id": "course-x"}
        mock_tool_block1.id = "tool_round1"
        mock_round1_response.content = [mock_tool_block1]

        # Round 2: Tool use response
        mock_round2_response = Mock()
        mock_round2_response.stop_reason = "tool_use"
        mock_tool_block2 = Mock()
        mock_tool_block2.type = "tool_use"
        mock_tool_block2.name = "search_course_content"
        mock_tool_block2.input = {"query": "authentication"}
        mock_tool_block2.id = "tool_round2"
        mock_round2_response.content = [mock_tool_block2]

        # Final response
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Combined response from both rounds")]
        mock_final_response.stop_reason = "stop"

        mock_client.messages.create.side_effect = [
            mock_round1_response,
            mock_round2_response,
            mock_final_response,
        ]
        mock_anthropic.return_value = mock_client

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "Lesson 4: Authentication Methods",
            "Found 3 courses discussing authentication",
        ]

        generator = AIGenerator("valid-api-key", "claude-sonnet-4-20250514")
        tools = [
            {"name": "get_course_outline", "description": "Get course outline"},
            {"name": "search_course_content", "description": "Search content"},
        ]

        result = generator.generate_response(
            "Find courses about the same topic as lesson 4 of course X",
            tools=tools,
            tool_manager=mock_tool_manager,
        )

        assert result == "Combined response from both rounds"
        # Should have 3 API calls: round 1, round 2, final
        assert mock_client.messages.create.call_count == 3
        # Should have 2 tool executions
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call(
            "get_course_outline", course_id="course-x"
        )
        mock_tool_manager.execute_tool.assert_any_call(
            "search_course_content", query="authentication"
        )

    @patch("ai_generator.anthropic.Anthropic")
    def test_multi_round_early_termination_no_tools(self, mock_anthropic):
        """Test early termination when Claude doesn't use tools"""
        mock_client = Mock()

        # Claude responds without using tools in first round
        mock_response = Mock()
        mock_response.stop_reason = "stop"
        mock_response.content = [Mock(text="Direct answer without tools")]

        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        generator = AIGenerator("valid-api-key", "claude-sonnet-4-20250514")
        tools = [{"name": "search_tool", "description": "Search"}]
        mock_tool_manager = Mock()

        result = generator.generate_response(
            "General knowledge question", tools=tools, tool_manager=mock_tool_manager
        )

        assert result == "Direct answer without tools"
        # Should only have 1 API call
        assert mock_client.messages.create.call_count == 1
        # Should have no tool executions
        assert mock_tool_manager.execute_tool.call_count == 0

    @patch("ai_generator.anthropic.Anthropic")
    def test_multi_round_max_rounds_enforcement(self, mock_anthropic):
        """Test that tool calling stops after 2 rounds"""
        mock_client = Mock()

        # Round 1: Tool use
        mock_round1_response = Mock()
        mock_round1_response.stop_reason = "tool_use"
        mock_tool_block1 = Mock()
        mock_tool_block1.type = "tool_use"
        mock_tool_block1.name = "search_tool"
        mock_tool_block1.input = {"query": "test1"}
        mock_tool_block1.id = "tool_round1"
        mock_round1_response.content = [mock_tool_block1]

        # Round 2: Tool use
        mock_round2_response = Mock()
        mock_round2_response.stop_reason = "tool_use"
        mock_tool_block2 = Mock()
        mock_tool_block2.type = "tool_use"
        mock_tool_block2.name = "search_tool"
        mock_tool_block2.input = {"query": "test2"}
        mock_tool_block2.id = "tool_round2"
        mock_round2_response.content = [mock_tool_block2]

        # Final response (forced after max rounds)
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Final answer after 2 rounds")]

        mock_client.messages.create.side_effect = [
            mock_round1_response,
            mock_round2_response,
            mock_final_response,
        ]
        mock_anthropic.return_value = mock_client

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result"

        generator = AIGenerator("valid-api-key", "claude-sonnet-4-20250514")
        tools = [{"name": "search_tool", "description": "Search"}]

        result = generator.generate_response(
            "Complex query requiring multiple searches",
            tools=tools,
            tool_manager=mock_tool_manager,
        )

        assert result == "Final answer after 2 rounds"
        # Should have 3 API calls: round 1, round 2, final
        assert mock_client.messages.create.call_count == 3
        # Should have 2 tool executions (one per round)
        assert mock_tool_manager.execute_tool.call_count == 2

    @patch("ai_generator.anthropic.Anthropic")
    def test_single_round_backwards_compatibility(self, mock_anthropic):
        """Test that single-round behavior is preserved when multi-round is disabled"""
        mock_client = Mock()

        # Tool use response
        mock_tool_response = Mock()
        mock_tool_response.stop_reason = "tool_use"
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_tool"
        mock_tool_block.input = {"query": "test"}
        mock_tool_block.id = "tool_123"
        mock_tool_response.content = [mock_tool_block]

        # Final response
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Single round response")]

        mock_client.messages.create.side_effect = [
            mock_tool_response,
            mock_final_response,
        ]
        mock_anthropic.return_value = mock_client

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result"

        generator = AIGenerator("valid-api-key", "claude-sonnet-4-20250514")
        tools = [{"name": "search_tool", "description": "Search"}]

        # Disable multi-round
        result = generator.generate_response(
            "Test query",
            tools=tools,
            tool_manager=mock_tool_manager,
            enable_multi_round=False,
        )

        assert result == "Single round response"
        # Should have 2 API calls (original behavior)
        assert mock_client.messages.create.call_count == 2
        # Should have 1 tool execution
        assert mock_tool_manager.execute_tool.call_count == 1

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_execution_error_handling(self, mock_anthropic):
        """Test error handling when tool execution fails"""
        mock_client = Mock()

        # Tool use response
        mock_tool_response = Mock()
        mock_tool_response.stop_reason = "tool_use"
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "failing_tool"
        mock_tool_block.input = {"query": "test"}
        mock_tool_block.id = "tool_123"
        mock_tool_response.content = [mock_tool_block]

        mock_client.messages.create.return_value = mock_tool_response
        mock_anthropic.return_value = mock_client

        # Mock tool manager that raises exception
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = Exception("Tool execution failed")

        generator = AIGenerator("valid-api-key", "claude-sonnet-4-20250514")
        tools = [{"name": "failing_tool", "description": "Failing tool"}]

        result = generator.generate_response(
            "Test query", tools=tools, tool_manager=mock_tool_manager
        )

        # Should return error message
        assert "Tool execution error in round 1" in result
        assert mock_client.messages.create.call_count == 1
        assert mock_tool_manager.execute_tool.call_count == 1

    @patch("ai_generator.anthropic.Anthropic")
    def test_api_error_handling(self, mock_anthropic):
        """Test error handling when API call fails"""
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("API call failed")
        mock_anthropic.return_value = mock_client

        generator = AIGenerator("valid-api-key", "claude-sonnet-4-20250514")
        tools = [{"name": "search_tool", "description": "Search"}]
        mock_tool_manager = Mock()

        result = generator.generate_response(
            "Test query", tools=tools, tool_manager=mock_tool_manager
        )

        # Should return error message
        assert "Error in round 1" in result
        assert "API call failed" in result


if __name__ == "__main__":
    pytest.main([__file__])
