import os
import sys
from unittest.mock import Mock

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from search_tools import Tool, ToolManager


class MockTool(Tool):
    """Mock tool for testing"""

    def __init__(self, name="mock_tool", should_fail=False):
        self.name = name
        self.should_fail = should_fail
        self.last_sources = []

    def get_tool_definition(self):
        return {
            "name": self.name,
            "description": f"Mock tool named {self.name}",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Test query"}
                },
                "required": ["query"],
            },
        }

    def execute(self, **kwargs):
        if self.should_fail:
            raise Exception("Mock tool execution failed")

        query = kwargs.get("query", "default")
        self.last_sources = [
            {"text": f"Source for {query}", "link": "http://example.com"}
        ]
        return f"Mock result for: {query}"


class TestToolManager:
    """Test cases for ToolManager class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.tool_manager = ToolManager()

    def test_initialization(self):
        """Test ToolManager initialization"""
        assert isinstance(self.tool_manager.tools, dict)
        assert len(self.tool_manager.tools) == 0

    def test_register_tool_success(self):
        """Test successful tool registration"""
        mock_tool = MockTool("test_tool")

        self.tool_manager.register_tool(mock_tool)

        assert "test_tool" in self.tool_manager.tools
        assert self.tool_manager.tools["test_tool"] is mock_tool

    def test_register_tool_without_name(self):
        """Test registering tool without name in definition"""

        class BadTool(Tool):
            def get_tool_definition(self):
                return {"description": "Tool without name"}

            def execute(self, **kwargs):
                return "result"

        bad_tool = BadTool()

        with pytest.raises(ValueError) as exc_info:
            self.tool_manager.register_tool(bad_tool)

        assert "Tool must have a 'name' in its definition" in str(exc_info.value)

    def test_register_multiple_tools(self):
        """Test registering multiple tools"""
        tool1 = MockTool("tool_one")
        tool2 = MockTool("tool_two")

        self.tool_manager.register_tool(tool1)
        self.tool_manager.register_tool(tool2)

        assert len(self.tool_manager.tools) == 2
        assert "tool_one" in self.tool_manager.tools
        assert "tool_two" in self.tool_manager.tools

    def test_get_tool_definitions(self):
        """Test getting all tool definitions"""
        tool1 = MockTool("tool_one")
        tool2 = MockTool("tool_two")

        self.tool_manager.register_tool(tool1)
        self.tool_manager.register_tool(tool2)

        definitions = self.tool_manager.get_tool_definitions()

        assert isinstance(definitions, list)
        assert len(definitions) == 2

        names = [def_["name"] for def_ in definitions]
        assert "tool_one" in names
        assert "tool_two" in names

    def test_get_tool_definitions_empty(self):
        """Test getting tool definitions when no tools registered"""
        definitions = self.tool_manager.get_tool_definitions()

        assert isinstance(definitions, list)
        assert len(definitions) == 0

    def test_execute_tool_success(self):
        """Test successful tool execution"""
        mock_tool = MockTool("test_tool")
        self.tool_manager.register_tool(mock_tool)

        result = self.tool_manager.execute_tool("test_tool", query="test query")

        assert result == "Mock result for: test query"

    def test_execute_tool_with_kwargs(self):
        """Test tool execution with various kwargs"""
        mock_tool = MockTool("test_tool")
        self.tool_manager.register_tool(mock_tool)

        result = self.tool_manager.execute_tool(
            "test_tool",
            query="complex query",
            course_name="Test Course",
            lesson_number=1,
        )

        assert "complex query" in result

    def test_execute_nonexistent_tool(self):
        """Test executing tool that doesn't exist"""
        result = self.tool_manager.execute_tool("nonexistent_tool", query="test")

        assert result == "Tool 'nonexistent_tool' not found"

    def test_execute_tool_with_exception(self):
        """Test tool execution when tool raises exception"""
        failing_tool = MockTool("failing_tool", should_fail=True)
        self.tool_manager.register_tool(failing_tool)

        with pytest.raises(Exception) as exc_info:
            self.tool_manager.execute_tool("failing_tool", query="test")

        assert "Mock tool execution failed" in str(exc_info.value)

    def test_get_last_sources_with_sources(self):
        """Test getting last sources when tool has sources"""
        mock_tool = MockTool("test_tool")
        self.tool_manager.register_tool(mock_tool)

        # Execute tool to generate sources
        self.tool_manager.execute_tool("test_tool", query="test query")

        sources = self.tool_manager.get_last_sources()

        assert isinstance(sources, list)
        assert len(sources) == 1
        assert sources[0]["text"] == "Source for test query"
        assert sources[0]["link"] == "http://example.com"

    def test_get_last_sources_no_sources(self):
        """Test getting last sources when no tools have sources"""
        mock_tool = MockTool("test_tool")
        # Don't execute the tool, so no sources generated
        self.tool_manager.register_tool(mock_tool)

        sources = self.tool_manager.get_last_sources()

        assert isinstance(sources, list)
        assert len(sources) == 0

    def test_get_last_sources_multiple_tools(self):
        """Test getting last sources with multiple tools"""
        tool1 = MockTool("tool_one")
        tool2 = MockTool("tool_two")

        self.tool_manager.register_tool(tool1)
        self.tool_manager.register_tool(tool2)

        # Execute first tool
        self.tool_manager.execute_tool("tool_one", query="first query")

        # Execute second tool (should override first)
        self.tool_manager.execute_tool("tool_two", query="second query")

        sources = self.tool_manager.get_last_sources()

        # Should return sources from the tool that has them (last executed)
        assert len(sources) == 1
        assert "second query" in sources[0]["text"]

    def test_reset_sources(self):
        """Test resetting sources from all tools"""
        mock_tool = MockTool("test_tool")
        self.tool_manager.register_tool(mock_tool)

        # Execute tool to generate sources
        self.tool_manager.execute_tool("test_tool", query="test query")

        # Verify sources exist
        sources = self.tool_manager.get_last_sources()
        assert len(sources) > 0

        # Reset sources
        self.tool_manager.reset_sources()

        # Verify sources are cleared
        sources = self.tool_manager.get_last_sources()
        assert len(sources) == 0
        assert mock_tool.last_sources == []

    def test_reset_sources_multiple_tools(self):
        """Test resetting sources from multiple tools"""
        tool1 = MockTool("tool_one")
        tool2 = MockTool("tool_two")

        self.tool_manager.register_tool(tool1)
        self.tool_manager.register_tool(tool2)

        # Execute both tools
        self.tool_manager.execute_tool("tool_one", query="first")
        self.tool_manager.execute_tool("tool_two", query="second")

        # Reset all sources
        self.tool_manager.reset_sources()

        # Verify all sources are cleared
        assert tool1.last_sources == []
        assert tool2.last_sources == []
        assert self.tool_manager.get_last_sources() == []

    def test_reset_sources_tools_without_sources_attribute(self):
        """Test resetting sources when tool doesn't have last_sources attribute"""

        class ToolWithoutSources(Tool):
            def get_tool_definition(self):
                return {
                    "name": "no_sources_tool",
                    "description": "Tool without sources",
                }

            def execute(self, **kwargs):
                return "result"

        tool_without_sources = ToolWithoutSources()
        self.tool_manager.register_tool(tool_without_sources)

        # This should not raise an exception
        self.tool_manager.reset_sources()

        sources = self.tool_manager.get_last_sources()
        assert sources == []

    def test_tool_integration_with_real_tools(self):
        """Test tool manager with CourseSearchTool and CourseOutlineTool"""
        from unittest.mock import Mock

        from search_tools import CourseOutlineTool, CourseSearchTool

        # Create mock vector store
        mock_vector_store = Mock()

        # Create real tools
        search_tool = CourseSearchTool(mock_vector_store)
        outline_tool = CourseOutlineTool(mock_vector_store)

        # Register tools
        self.tool_manager.register_tool(search_tool)
        self.tool_manager.register_tool(outline_tool)

        # Verify registration
        assert len(self.tool_manager.tools) == 2
        assert "search_course_content" in self.tool_manager.tools
        assert "get_course_outline" in self.tool_manager.tools

        # Verify definitions
        definitions = self.tool_manager.get_tool_definitions()
        assert len(definitions) == 2

        tool_names = [def_["name"] for def_ in definitions]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names


if __name__ == "__main__":
    pytest.main([__file__])
