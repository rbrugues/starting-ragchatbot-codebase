"""
Shared fixtures and configuration for RAG system tests
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Generator, Dict, Any, List
import tempfile
import os
import shutil
from pathlib import Path

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config import Config
from rag_system import RAGSystem
from vector_store import VectorStore
from ai_generator import AIGenerator
from session_manager import SessionManager
from search_tools import ToolManager


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_config(temp_dir: str) -> Config:
    """Test configuration with temporary directories"""
    config = Config()
    config.chroma_db_path = os.path.join(temp_dir, "test_chroma_db")
    config.anthropic_api_key = "test-api-key"
    config.chunk_size = 500
    config.chunk_overlap = 50
    config.max_results = 3
    return config


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for AI generation"""
    with patch('anthropic.Anthropic') as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        
        # Mock the messages.create method
        mock_response = Mock()
        mock_response.content = [Mock(text="Test AI response")]
        mock_instance.messages.create.return_value = mock_response
        
        yield mock_instance


@pytest.fixture
def mock_sentence_transformer():
    """Mock SentenceTransformer for embeddings"""
    with patch('sentence_transformers.SentenceTransformer') as mock_transformer:
        mock_instance = Mock()
        mock_transformer.return_value = mock_instance
        
        # Mock encode method to return dummy embeddings
        mock_instance.encode.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5] for _ in range(10)]
        
        yield mock_instance


@pytest.fixture
def sample_course_data() -> Dict[str, Any]:
    """Sample course data for testing"""
    return {
        "course_title": "Test Course",
        "lessons": [
            {
                "lesson_title": "Lesson 1",
                "content": "This is test content for lesson 1. It contains important information about the topic."
            },
            {
                "lesson_title": "Lesson 2", 
                "content": "This is test content for lesson 2. It covers advanced concepts and examples."
            }
        ]
    }


@pytest.fixture
def sample_chunks() -> List[Dict[str, Any]]:
    """Sample chunks for testing vector store"""
    return [
        {
            "id": "chunk_1",
            "text": "Test content for chunk 1",
            "course": "Test Course",
            "lesson": "Lesson 1",
            "metadata": {"source": "test_doc.txt"}
        },
        {
            "id": "chunk_2", 
            "text": "Test content for chunk 2",
            "course": "Test Course",
            "lesson": "Lesson 2",
            "metadata": {"source": "test_doc.txt"}
        }
    ]


@pytest.fixture
def mock_vector_store(test_config: Config, sample_chunks: List[Dict[str, Any]]):
    """Mock vector store with sample data"""
    with patch('vector_store.VectorStore') as mock_vs:
        mock_instance = Mock()
        mock_vs.return_value = mock_instance
        
        # Mock search method
        mock_instance.search.return_value = sample_chunks[:2]  # Return first 2 chunks
        mock_instance.get_collection_stats.return_value = {
            "total_chunks": len(sample_chunks),
            "courses": ["Test Course"]
        }
        
        yield mock_instance


@pytest.fixture
def mock_ai_generator(mock_anthropic_client):
    """Mock AI generator"""
    with patch('ai_generator.AIGenerator') as mock_ai:
        mock_instance = Mock()
        mock_ai.return_value = mock_instance
        
        mock_instance.generate.return_value = "Test AI response"
        
        yield mock_instance


@pytest.fixture
def mock_session_manager():
    """Mock session manager"""
    with patch('session_manager.SessionManager') as mock_sm:
        mock_instance = Mock()
        mock_sm.return_value = mock_instance
        
        mock_instance.create_session.return_value = "test-session-id"
        mock_instance.get_conversation_history.return_value = []
        mock_instance.add_message.return_value = None
        
        yield mock_instance


@pytest.fixture
def mock_tool_manager():
    """Mock tool manager"""
    with patch('search_tools.ToolManager') as mock_tm:
        mock_instance = Mock()
        mock_tm.return_value = mock_instance
        
        mock_instance.search_courses.return_value = ["Test Course"]
        
        yield mock_instance


@pytest.fixture
def mock_rag_system(
    test_config: Config,
    mock_vector_store,
    mock_ai_generator, 
    mock_session_manager,
    mock_tool_manager
):
    """Mock RAG system with all dependencies"""
    with patch('rag_system.RAGSystem') as mock_rag:
        mock_instance = Mock()
        mock_rag.return_value = mock_instance
        
        # Mock the main query method
        mock_instance.query.return_value = (
            "Test response",
            [{"course": "Test Course", "lesson": "Lesson 1", "text": "Test content"}]
        )
        
        # Mock analytics method
        mock_instance.get_course_analytics.return_value = {
            "total_courses": 1,
            "course_titles": ["Test Course"]
        }
        
        # Mock add_course_folder method
        mock_instance.add_course_folder.return_value = (1, 2)  # 1 course, 2 chunks
        
        # Mock session manager property
        mock_instance.session_manager = mock_session_manager
        
        yield mock_instance


@pytest.fixture
def sample_query_request() -> Dict[str, Any]:
    """Sample API query request"""
    return {
        "query": "What is the main topic of the course?",
        "session_id": "test-session-id"
    }


@pytest.fixture
def sample_query_response() -> Dict[str, Any]:
    """Sample API query response"""
    return {
        "answer": "The main topic is testing and RAG systems.",
        "sources": [
            {
                "course": "Test Course",
                "lesson": "Lesson 1", 
                "text": "Test content for testing"
            }
        ],
        "session_id": "test-session-id"
    }


@pytest.fixture
def sample_course_stats() -> Dict[str, Any]:
    """Sample course statistics response"""
    return {
        "total_courses": 1,
        "course_titles": ["Test Course"]
    }


# Test data files
@pytest.fixture
def create_test_docs(temp_dir: str) -> str:
    """Create test document files"""
    docs_dir = os.path.join(temp_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    
    # Create a test course file
    course_file = os.path.join(docs_dir, "test_course.md")
    with open(course_file, "w") as f:
        f.write("""# Test Course

## Lesson 1: Introduction
This is the introduction lesson content.

## Lesson 2: Advanced Topics  
This covers advanced topics and concepts.
""")
    
    return docs_dir


# Common mock patches
@pytest.fixture(autouse=True)
def mock_warnings():
    """Automatically mock warnings to avoid noise in tests"""
    with patch('warnings.filterwarnings'):
        yield


@pytest.fixture
def no_chroma_persistence():
    """Disable ChromaDB persistence for tests"""
    with patch.dict(os.environ, {"CHROMA_ENABLE_PERSISTENCE": "false"}):
        yield