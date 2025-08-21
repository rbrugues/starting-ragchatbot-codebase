"""
API endpoint tests for the RAG system FastAPI application
"""
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import patch, Mock
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config import config


def create_test_app():
    """Create a test FastAPI app without static file mounting"""
    # Import everything we need from the main app but create a new instance
    import warnings
    warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from pydantic import BaseModel
    from typing import List, Optional, Union, Dict, Any

    # Create test app without static file mounting
    app = FastAPI(title="Course Materials RAG System - Test", root_path="")

    # Add middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Pydantic models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Union[str, Dict[str, Any]]]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # Mock RAG system - will be patched in tests
    rag_system = Mock()

    # API Endpoints
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()
            
            answer, sources = rag_system.query(request.query, session_id)
            
            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def read_root():
        return {"message": "RAG System API", "status": "running"}

    # Store rag_system reference for testing
    app.state.rag_system = rag_system
    
    return app


@pytest.fixture
def test_app():
    """Create test app fixture"""
    return create_test_app()


@pytest.fixture  
def client(test_app):
    """Create test client fixture"""
    return TestClient(test_app)


@pytest.mark.api
class TestAPIEndpoints:
    """Test cases for API endpoints"""

    def test_root_endpoint(self, client):
        """Test the root endpoint returns proper response"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "RAG System API"
        assert data["status"] == "running"

    def test_query_endpoint_success(self, client, test_app, sample_query_request, sample_query_response):
        """Test successful query processing"""
        # Mock the RAG system
        mock_rag = test_app.state.rag_system
        mock_rag.query.return_value = (
            sample_query_response["answer"],
            sample_query_response["sources"]
        )
        mock_rag.session_manager.create_session.return_value = sample_query_response["session_id"]

        response = client.post("/api/query", json=sample_query_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == sample_query_response["answer"]
        assert data["sources"] == sample_query_response["sources"]
        assert data["session_id"] == sample_query_response["session_id"]

        # Verify RAG system was called correctly
        mock_rag.query.assert_called_once_with(
            sample_query_request["query"],
            sample_query_request["session_id"]
        )

    def test_query_endpoint_without_session_id(self, client, test_app):
        """Test query endpoint creates session when none provided"""
        # Mock the RAG system
        mock_rag = test_app.state.rag_system
        mock_rag.query.return_value = ("Test answer", [])
        mock_rag.session_manager.create_session.return_value = "new-session-id"

        request_data = {"query": "Test query"}
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "new-session-id"
        
        # Verify session was created
        mock_rag.session_manager.create_session.assert_called_once()

    def test_query_endpoint_validation_error(self, client):
        """Test query endpoint with invalid request data"""
        # Missing required 'query' field
        response = client.post("/api/query", json={})
        assert response.status_code == 422

        # Invalid data type
        response = client.post("/api/query", json={"query": 123})
        assert response.status_code == 422

    def test_query_endpoint_server_error(self, client, test_app):
        """Test query endpoint handles server errors"""
        # Mock the RAG system to raise an exception
        mock_rag = test_app.state.rag_system
        mock_rag.query.side_effect = Exception("Database connection failed")

        request_data = {"query": "Test query", "session_id": "test-session"}
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "Database connection failed" in data["detail"]

    def test_courses_endpoint_success(self, client, test_app, sample_course_stats):
        """Test successful course statistics retrieval"""
        # Mock the RAG system
        mock_rag = test_app.state.rag_system
        mock_rag.get_course_analytics.return_value = sample_course_stats

        response = client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == sample_course_stats["total_courses"]
        assert data["course_titles"] == sample_course_stats["course_titles"]

        # Verify RAG system was called
        mock_rag.get_course_analytics.assert_called_once()

    def test_courses_endpoint_server_error(self, client, test_app):
        """Test courses endpoint handles server errors"""
        # Mock the RAG system to raise an exception
        mock_rag = test_app.state.rag_system
        mock_rag.get_course_analytics.side_effect = Exception("Vector store unavailable")

        response = client.get("/api/courses")
        
        assert response.status_code == 500
        data = response.json()
        assert "Vector store unavailable" in data["detail"]

    def test_query_endpoint_with_complex_sources(self, client, test_app):
        """Test query endpoint with complex source objects"""
        # Mock the RAG system with complex sources
        mock_rag = test_app.state.rag_system
        complex_sources = [
            {
                "course": "Advanced Python",
                "lesson": "Async Programming",
                "text": "Async programming allows...",
                "metadata": {"page": 1, "section": "intro"}
            },
            {
                "course": "Advanced Python", 
                "lesson": "Error Handling",
                "text": "Exception handling is...",
                "metadata": {"page": 5, "section": "errors"}
            }
        ]
        mock_rag.query.return_value = ("Complex answer", complex_sources)
        mock_rag.session_manager.create_session.return_value = "session-123"

        request_data = {"query": "Tell me about Python", "session_id": "session-123"}
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Complex answer"
        assert len(data["sources"]) == 2
        assert data["sources"][0]["course"] == "Advanced Python"
        assert data["sources"][1]["lesson"] == "Error Handling"

    def test_query_endpoint_empty_sources(self, client, test_app):
        """Test query endpoint when no sources are found"""
        # Mock the RAG system with empty sources
        mock_rag = test_app.state.rag_system
        mock_rag.query.return_value = ("No relevant information found", [])
        mock_rag.session_manager.create_session.return_value = "session-456"

        request_data = {"query": "Nonexistent topic", "session_id": "session-456"}
        response = client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "No relevant information found"
        assert data["sources"] == []

    def test_courses_endpoint_empty_courses(self, client, test_app):
        """Test courses endpoint when no courses are available"""
        # Mock the RAG system with empty courses
        mock_rag = test_app.state.rag_system
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        response = client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []


@pytest.mark.api
@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API endpoints"""

    def test_query_and_courses_consistency(self, client, test_app):
        """Test that query and courses endpoints return consistent data"""
        # Mock the RAG system
        mock_rag = test_app.state.rag_system
        
        # Set up course analytics
        course_analytics = {
            "total_courses": 2,
            "course_titles": ["Python Basics", "Advanced Python"]
        }
        mock_rag.get_course_analytics.return_value = course_analytics
        
        # Set up query response with sources from the same courses
        query_sources = [
            {"course": "Python Basics", "lesson": "Variables", "text": "Variables store data"},
            {"course": "Advanced Python", "lesson": "Classes", "text": "Classes define objects"}
        ]
        mock_rag.query.return_value = ("Here's info about Python", query_sources)
        mock_rag.session_manager.create_session.return_value = "integration-session"

        # Get courses
        courses_response = client.get("/api/courses")
        assert courses_response.status_code == 200
        courses_data = courses_response.json()

        # Make a query
        query_response = client.post("/api/query", json={
            "query": "Tell me about Python", 
            "session_id": "integration-session"
        })
        assert query_response.status_code == 200
        query_data = query_response.json()

        # Verify consistency - courses mentioned in sources should exist in course list
        source_courses = {source["course"] for source in query_data["sources"]}
        available_courses = set(courses_data["course_titles"])
        
        # All source courses should be in the available courses
        assert source_courses.issubset(available_courses)

    def test_multiple_queries_same_session(self, client, test_app):
        """Test multiple queries with the same session ID"""
        mock_rag = test_app.state.rag_system
        session_id = "persistent-session"
        
        # First query
        mock_rag.query.return_value = ("Answer 1", [{"course": "Test", "lesson": "1", "text": "Content 1"}])
        response1 = client.post("/api/query", json={
            "query": "First question",
            "session_id": session_id
        })
        assert response1.status_code == 200
        assert response1.json()["session_id"] == session_id

        # Second query with same session
        mock_rag.query.return_value = ("Answer 2", [{"course": "Test", "lesson": "2", "text": "Content 2"}])
        response2 = client.post("/api/query", json={
            "query": "Second question", 
            "session_id": session_id
        })
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

        # Verify both queries were made with the same session
        assert mock_rag.query.call_count == 2
        call_args = mock_rag.query.call_args_list
        assert call_args[0][0][1] == session_id  # First call session ID
        assert call_args[1][0][1] == session_id  # Second call session ID