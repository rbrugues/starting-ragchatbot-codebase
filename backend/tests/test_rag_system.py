import pytest
import sys
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rag_system import RAGSystem
from config import Config
from models import Course, Lesson, CourseChunk


class TestRAGSystem:
    """Test cases for RAGSystem integration"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create test config with temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config()
        self.config.CHROMA_PATH = self.temp_dir
        self.config.ANTHROPIC_API_KEY = ""  # Force mock mode
        
        # Initialize RAG system
        self.rag_system = RAGSystem(self.config)
    
    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test RAG system initialization"""
        assert self.rag_system.config is not None
        assert self.rag_system.document_processor is not None
        assert self.rag_system.vector_store is not None
        assert self.rag_system.ai_generator is not None
        assert self.rag_system.session_manager is not None
        assert self.rag_system.tool_manager is not None
        assert self.rag_system.search_tool is not None
        assert self.rag_system.outline_tool is not None
    
    def test_tool_registration(self):
        """Test that tools are properly registered"""
        definitions = self.rag_system.tool_manager.get_tool_definitions()
        assert len(definitions) == 2
        
        tool_names = [def_["name"] for def_ in definitions]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names
    
    def test_add_course_document_success(self):
        """Test successfully adding a course document"""
        with patch.object(self.rag_system.document_processor, 'process_course_document') as mock_process:
            # Mock successful document processing
            test_course = Course(
                title="Test Course",
                instructor="Test Instructor", 
                course_link="http://example.com",
                lessons=[Lesson(lesson_number=1, title="Intro", lesson_link="http://example.com/lesson1")]
            )
            test_chunks = [
                CourseChunk(course_title="Test Course", lesson_number=1, chunk_index=0, content="Test content chunk")
            ]
            mock_process.return_value = (test_course, test_chunks)
            
            course, chunk_count = self.rag_system.add_course_document("test_file.pdf")
            
            assert course.title == "Test Course"
            assert chunk_count == 1
            mock_process.assert_called_once_with("test_file.pdf")
    
    def test_add_course_document_failure(self):
        """Test handling of document processing failure"""
        with patch.object(self.rag_system.document_processor, 'process_course_document') as mock_process:
            mock_process.side_effect = Exception("Processing failed")
            
            course, chunk_count = self.rag_system.add_course_document("bad_file.pdf")
            
            assert course is None
            assert chunk_count == 0
    
    def test_add_course_folder_with_files(self):
        """Test adding course folder with files"""
        # Create temporary folder structure
        test_folder = os.path.join(self.temp_dir, "test_docs")
        os.makedirs(test_folder)
        
        # Create test files
        test_file1 = os.path.join(test_folder, "course1.pdf")
        test_file2 = os.path.join(test_folder, "course2.docx")
        test_file3 = os.path.join(test_folder, "readme.txt")  # Should be processed
        test_file4 = os.path.join(test_folder, "image.jpg")   # Should be ignored
        
        for file_path in [test_file1, test_file2, test_file3, test_file4]:
            with open(file_path, 'w') as f:
                f.write("test content")
        
        with patch.object(self.rag_system.document_processor, 'process_course_document') as mock_process:
            # Mock successful processing for valid files
            def mock_processing(file_path):
                if file_path.endswith(('.pdf', '.docx', '.txt')):
                    course_name = os.path.basename(file_path).split('.')[0]
                    course = Course(title=f"Course {course_name}", instructor="Teacher", course_link="http://example.com", lessons=[])
                    chunks = [CourseChunk(course_title=f"Course {course_name}", lesson_number=1, chunk_index=0, content="content")]
                    return course, chunks
                else:
                    raise Exception("Unsupported file type")
            
            mock_process.side_effect = mock_processing
            
            courses, chunks = self.rag_system.add_course_folder(test_folder)
            
            assert courses == 3  # pdf, docx, txt files
            assert chunks == 3
            assert mock_process.call_count == 3
    
    def test_add_course_folder_nonexistent(self):
        """Test adding nonexistent course folder"""
        courses, chunks = self.rag_system.add_course_folder("/nonexistent/folder")
        
        assert courses == 0
        assert chunks == 0
    
    def test_add_course_folder_clear_existing(self):
        """Test adding course folder with clear_existing=True"""
        with patch.object(self.rag_system.vector_store, 'clear_all_data') as mock_clear:
            with patch('os.path.exists', return_value=True):
                with patch('os.listdir', return_value=[]):
                    self.rag_system.add_course_folder("test_folder", clear_existing=True)
                    
                    mock_clear.assert_called_once()
    
    def test_query_without_api_key_should_fail(self):
        """Test that query fails without API key due to the critical bug"""
        # This test verifies the critical bug we identified
        with pytest.raises(AttributeError):
            self.rag_system.query("What is computer use?")
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_query_with_api_key(self, mock_anthropic):
        """Test query with valid API key"""
        # Set up API key
        self.config.ANTHROPIC_API_KEY = "valid-api-key"
        self.rag_system = RAGSystem(self.config)
        
        # Mock Anthropic client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_response.stop_reason = "stop"
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        response, sources = self.rag_system.query("Test query")
        
        assert response == "Test response"
        assert isinstance(sources, list)
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_query_with_tool_execution(self, mock_anthropic):
        """Test query that triggers tool execution"""
        # Set up API key
        self.config.ANTHROPIC_API_KEY = "valid-api-key"
        self.rag_system = RAGSystem(self.config)
        
        # Mock Anthropic client for tool execution flow
        mock_client = Mock()
        
        # First response with tool use
        mock_tool_response = Mock()
        mock_tool_response.stop_reason = "tool_use"
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.input = {"query": "computer use"}
        mock_tool_block.id = "tool_123"
        mock_tool_response.content = [mock_tool_block]
        
        # Final response after tool execution
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Computer use is a capability...")]
        
        mock_client.messages.create.side_effect = [mock_tool_response, mock_final_response]
        mock_anthropic.return_value = mock_client
        
        # Mock tool execution
        with patch.object(self.rag_system.search_tool, 'execute') as mock_tool_execute:
            mock_tool_execute.return_value = "Search results about computer use"
            
            response, sources = self.rag_system.query("What is computer use?")
            
            assert response == "Computer use is a capability..."
            mock_tool_execute.assert_called_once_with(query="computer use")
    
    def test_query_with_session_management(self):
        """Test query with session management"""
        # Set up API key to avoid the critical bug
        self.config.ANTHROPIC_API_KEY = "valid-api-key"
        
        with patch('ai_generator.anthropic.Anthropic'):
            with patch.object(self.rag_system.ai_generator, 'generate_response') as mock_generate:
                mock_generate.return_value = "Response with history"
                
                # First query creates session
                response1, sources1 = self.rag_system.query("First query", session_id="test_session")
                
                # Second query should include history
                response2, sources2 = self.rag_system.query("Second query", session_id="test_session")
                
                # Verify generate_response was called with conversation history
                assert mock_generate.call_count == 2
                
                # Second call should have conversation history
                second_call_args = mock_generate.call_args_list[1]
                assert second_call_args[1]['conversation_history'] is not None
    
    def test_query_source_management(self):
        """Test that sources are properly managed during queries"""
        self.config.ANTHROPIC_API_KEY = "valid-api-key"
        
        with patch('ai_generator.anthropic.Anthropic'):
            with patch.object(self.rag_system.ai_generator, 'generate_response') as mock_generate:
                mock_generate.return_value = "Test response"
                
                # Mock tool manager to return sources
                with patch.object(self.rag_system.tool_manager, 'get_last_sources') as mock_get_sources:
                    with patch.object(self.rag_system.tool_manager, 'reset_sources') as mock_reset_sources:
                        mock_get_sources.return_value = [{"text": "Test Source", "link": "http://example.com"}]
                        
                        response, sources = self.rag_system.query("Test query")
                        
                        assert response == "Test response"
                        assert len(sources) == 1
                        assert sources[0]["text"] == "Test Source"
                        
                        # Verify sources were retrieved and reset
                        mock_get_sources.assert_called_once()
                        mock_reset_sources.assert_called_once()
    
    def test_get_course_analytics(self):
        """Test getting course analytics"""
        with patch.object(self.rag_system.vector_store, 'get_course_count') as mock_count:
            with patch.object(self.rag_system.vector_store, 'get_existing_course_titles') as mock_titles:
                mock_count.return_value = 3
                mock_titles.return_value = ["Course 1", "Course 2", "Course 3"]
                
                analytics = self.rag_system.get_course_analytics()
                
                assert analytics["total_courses"] == 3
                assert len(analytics["course_titles"]) == 3
                assert "Course 1" in analytics["course_titles"]
    
    def test_course_duplicate_handling(self):
        """Test that duplicate courses are not re-added"""
        test_folder = os.path.join(self.temp_dir, "test_docs")
        os.makedirs(test_folder)
        
        test_file = os.path.join(test_folder, "course.pdf")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        with patch.object(self.rag_system.document_processor, 'process_course_document') as mock_process:
            with patch.object(self.rag_system.vector_store, 'get_existing_course_titles') as mock_existing:
                # First time - no existing courses
                mock_existing.return_value = []
                course = Course(title="Test Course", instructor="Teacher", course_link="http://example.com", lessons=[])
                chunks = [CourseChunk(course_title="Test Course", lesson_number=1, chunk_index=0, content="content")]
                mock_process.return_value = (course, chunks)
                
                courses1, chunks1 = self.rag_system.add_course_folder(test_folder)
                assert courses1 == 1
                
                # Second time - course already exists
                mock_existing.return_value = ["Test Course"]
                
                courses2, chunks2 = self.rag_system.add_course_folder(test_folder)
                assert courses2 == 0  # Should skip existing course
    
    def test_integration_with_real_components(self):
        """Test integration between real components (without API calls)"""
        # Add test data
        test_course = Course(
            title="Integration Test Course",
            instructor="Test Teacher",
            course_link="http://example.com/course",
            lessons=[
                Lesson(lesson_number=1, title="Introduction", lesson_link="http://example.com/lesson1"),
                Lesson(lesson_number=2, title="Advanced Topics", lesson_link="http://example.com/lesson2")
            ]
        )
        test_chunks = [
            CourseChunk(course_title="Integration Test Course", lesson_number=1, chunk_index=0, content="Introduction to the course"),
            CourseChunk(course_title="Integration Test Course", lesson_number=2, chunk_index=1, content="Advanced topics discussion")
        ]
        
        # Add to vector store
        self.rag_system.vector_store.add_course_metadata(test_course)
        self.rag_system.vector_store.add_course_content(test_chunks)
        
        # Test course search tool
        search_result = self.rag_system.search_tool.execute("introduction")
        assert "Introduction to the course" in search_result
        
        # Test course outline tool
        outline_result = self.rag_system.outline_tool.execute("Integration Test Course")
        assert "Integration Test Course" in outline_result
        assert "Introduction" in outline_result
        assert "Advanced Topics" in outline_result
    
    def test_error_handling_in_query(self):
        """Test error handling in query processing"""
        # Force an error in AI generation
        with patch.object(self.rag_system.ai_generator, 'generate_response') as mock_generate:
            mock_generate.side_effect = Exception("AI generation failed")
            
            with pytest.raises(Exception) as exc_info:
                self.rag_system.query("Test query")
            
            assert "AI generation failed" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__])