import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from search_tools import CourseSearchTool
from vector_store import SearchResults


class TestCourseSearchTool:
    """Test cases for CourseSearchTool class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_vector_store = Mock()
        self.tool = CourseSearchTool(self.mock_vector_store)

    def test_tool_definition(self):
        """Test that tool definition is correctly formatted"""
        definition = self.tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["type"] == "object"
        assert "query" in definition["input_schema"]["properties"]
        assert "query" in definition["input_schema"]["required"]
        assert "course_name" in definition["input_schema"]["properties"]
        assert "lesson_number" in definition["input_schema"]["properties"]

    def test_execute_successful_search(self):
        """Test successful search execution"""
        # Mock successful search results
        mock_results = SearchResults(
            documents=["Test content from lesson"],
            metadata=[{"course_title": "Test Course", "lesson_number": 1}],
            distances=[0.5],
            error=None,
        )
        self.mock_vector_store.search.return_value = mock_results

        # Mock lesson link retrieval
        with patch.object(
            self.tool, "_get_lesson_link", return_value="http://example.com/lesson1"
        ):
            result = self.tool.execute("test query")

        assert "[Test Course - Lesson 1]" in result
        assert "Test content from lesson" in result
        assert len(self.tool.last_sources) == 1
        assert self.tool.last_sources[0]["text"] == "Test Course - Lesson 1"
        assert self.tool.last_sources[0]["link"] == "http://example.com/lesson1"

    def test_execute_with_search_error(self):
        """Test execute when vector store returns error"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="Search failed: No embeddings available",
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.tool.execute("test query")

        assert result == "Search failed: No embeddings available"
        self.mock_vector_store.search.assert_called_once()

    def test_execute_with_empty_results(self):
        """Test execute when no results are found"""
        mock_results = SearchResults(
            documents=[], metadata=[], distances=[], error=None
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.tool.execute("test query")

        assert "No relevant content found" in result

    def test_execute_with_course_filter(self):
        """Test execute with course name filter"""
        mock_results = SearchResults(
            documents=["Course specific content"],
            metadata=[{"course_title": "Filtered Course", "lesson_number": 2}],
            distances=[0.3],
            error=None,
        )
        self.mock_vector_store.search.return_value = mock_results

        with patch.object(self.tool, "_get_lesson_link", return_value=None):
            result = self.tool.execute("test query", course_name="Filtered Course")

        self.mock_vector_store.search.assert_called_once_with(
            query="test query", course_name="Filtered Course", lesson_number=None
        )
        assert "[Filtered Course - Lesson 2]" in result

    def test_execute_with_lesson_filter(self):
        """Test execute with lesson number filter"""
        mock_results = SearchResults(
            documents=["Lesson specific content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 3}],
            distances=[0.2],
            error=None,
        )
        self.mock_vector_store.search.return_value = mock_results

        with patch.object(
            self.tool, "_get_lesson_link", return_value="http://example.com/lesson3"
        ):
            result = self.tool.execute("test query", lesson_number=3)

        self.mock_vector_store.search.assert_called_once_with(
            query="test query", course_name=None, lesson_number=3
        )
        assert "[Test Course - Lesson 3]" in result

    def test_execute_no_course_filter_message(self):
        """Test execute shows filter info in error message"""
        mock_results = SearchResults(
            documents=[], metadata=[], distances=[], error=None
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.tool.execute(
            "test query", course_name="Missing Course", lesson_number=5
        )

        assert (
            "No relevant content found in course 'Missing Course' in lesson 5" in result
        )

    def test_format_results_multiple_documents(self):
        """Test formatting of multiple search results"""
        mock_results = SearchResults(
            documents=["Content 1", "Content 2"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
            ],
            distances=[0.1, 0.2],
            error=None,
        )

        with patch.object(
            self.tool,
            "_get_lesson_link",
            side_effect=[
                "http://example.com/course-a/lesson1",
                "http://example.com/course-b/lesson2",
            ],
        ):
            result = self.tool._format_results(mock_results)

        assert "[Course A - Lesson 1]" in result
        assert "[Course B - Lesson 2]" in result
        assert "Content 1" in result
        assert "Content 2" in result
        assert len(self.tool.last_sources) == 2

    def test_format_results_no_lesson_number(self):
        """Test formatting when lesson number is None"""
        mock_results = SearchResults(
            documents=["General content"],
            metadata=[{"course_title": "General Course", "lesson_number": None}],
            distances=[0.3],
            error=None,
        )

        result = self.tool._format_results(mock_results)

        assert "[General Course]" in result
        assert "General content" in result
        assert len(self.tool.last_sources) == 1
        assert self.tool.last_sources[0]["link"] is None

    def test_get_lesson_link_success(self):
        """Test successful lesson link retrieval"""
        mock_catalog_result = {
            "metadatas": [
                {
                    "lessons_json": '[{"lesson_number": 1, "lesson_link": "http://example.com/lesson1"}]'
                }
            ]
        }
        self.mock_vector_store.course_catalog.get.return_value = mock_catalog_result

        link = self.tool._get_lesson_link("Test Course", 1)

        assert link == "http://example.com/lesson1"
        self.mock_vector_store.course_catalog.get.assert_called_once_with(
            ids=["Test Course"]
        )

    def test_get_lesson_link_no_lesson_number(self):
        """Test lesson link retrieval with None lesson number"""
        link = self.tool._get_lesson_link("Test Course", None)
        assert link is None

    def test_get_lesson_link_not_found(self):
        """Test lesson link retrieval when lesson not found"""
        mock_catalog_result = {
            "metadatas": [
                {
                    "lessons_json": '[{"lesson_number": 2, "lesson_link": "http://example.com/lesson2"}]'
                }
            ]
        }
        self.mock_vector_store.course_catalog.get.return_value = mock_catalog_result

        link = self.tool._get_lesson_link(
            "Test Course", 1
        )  # Looking for lesson 1, but only lesson 2 exists

        assert link is None

    def test_get_lesson_link_exception_handling(self):
        """Test lesson link retrieval with exception"""
        self.mock_vector_store.course_catalog.get.side_effect = Exception(
            "Database error"
        )

        link = self.tool._get_lesson_link("Test Course", 1)

        assert link is None

    def test_last_sources_tracking(self):
        """Test that last_sources are properly tracked and reset"""
        # Initially empty
        assert self.tool.last_sources == []

        # After search
        mock_results = SearchResults(
            documents=["Test content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 1}],
            distances=[0.1],
            error=None,
        )

        with patch.object(
            self.tool, "_get_lesson_link", return_value="http://example.com/test"
        ):
            self.tool._format_results(mock_results)

        assert len(self.tool.last_sources) == 1
        assert self.tool.last_sources[0]["text"] == "Test Course - Lesson 1"
        assert self.tool.last_sources[0]["link"] == "http://example.com/test"


if __name__ == "__main__":
    pytest.main([__file__])
