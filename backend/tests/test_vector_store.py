import pytest
import sys
import os
import tempfile
import shutil
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from vector_store import VectorStore, SearchResults
from models import Course, Lesson, CourseChunk


class TestVectorStore:
    """Test cases for VectorStore class"""
    
    def setup_method(self):
        """Set up test fixtures with temporary ChromaDB"""
        self.temp_dir = tempfile.mkdtemp()
        self.vector_store = VectorStore(
            chroma_path=self.temp_dir,
            embedding_model="all-MiniLM-L6-v2",
            max_results=5
        )
    
    def teardown_method(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test VectorStore initialization"""
        assert self.vector_store.max_results == 5
        assert self.vector_store.client is not None
        assert self.vector_store.course_catalog is not None
        assert self.vector_store.course_content is not None
    
    def test_add_course_metadata(self):
        """Test adding course metadata to catalog"""
        # Create test course
        lessons = [
            Lesson(lesson_number=1, title="Introduction", lesson_link="http://example.com/lesson1"),
            Lesson(lesson_number=2, title="Advanced Topics", lesson_link="http://example.com/lesson2")
        ]
        course = Course(
            title="Test Course",
            instructor="Test Instructor",
            course_link="http://example.com/course",
            lessons=lessons
        )
        
        # Add to vector store
        self.vector_store.add_course_metadata(course)
        
        # Verify it was added
        results = self.vector_store.course_catalog.get(ids=["Test Course"])
        assert results is not None
        assert len(results['ids']) == 1
        assert results['ids'][0] == "Test Course"
        
        metadata = results['metadatas'][0]
        assert metadata['title'] == "Test Course"
        assert metadata['instructor'] == "Test Instructor"
        assert metadata['course_link'] == "http://example.com/course"
        assert metadata['lesson_count'] == 2
        assert 'lessons_json' in metadata
    
    def test_add_course_content(self):
        """Test adding course content chunks"""
        chunks = [
            CourseChunk(
                course_title="Test Course",
                lesson_number=1,
                chunk_index=0,
                content="This is the first chunk of content"
            ),
            CourseChunk(
                course_title="Test Course",
                lesson_number=1,
                chunk_index=1,
                content="This is the second chunk of content"
            )
        ]
        
        self.vector_store.add_course_content(chunks)
        
        # Verify content was added
        results = self.vector_store.course_content.get()
        assert results is not None
        assert len(results['ids']) == 2
        assert "Test_Course_0" in results['ids']
        assert "Test_Course_1" in results['ids']
    
    def test_search_with_no_data(self):
        """Test search when no data is loaded"""
        results = self.vector_store.search("test query")
        
        assert isinstance(results, SearchResults)
        assert results.is_empty()
        assert results.error is None
    
    def test_search_with_data(self):
        """Test search with actual data"""
        # Add test data first
        chunks = [
            CourseChunk(
                course_title="Python Course",
                lesson_number=1,
                chunk_index=0,
                content="Python is a programming language used for data science and web development"
            ),
            CourseChunk(
                course_title="Python Course",
                lesson_number=2,
                chunk_index=1,
                content="Variables in Python store data values and can be strings, integers, or floats"
            )
        ]
        self.vector_store.add_course_content(chunks)
        
        # Search for content
        results = self.vector_store.search("Python programming language")
        
        assert isinstance(results, SearchResults)
        assert not results.is_empty()
        assert len(results.documents) > 0
        assert "Python" in results.documents[0]
    
    def test_resolve_course_name_success(self):
        """Test course name resolution with existing course"""
        # Add course metadata
        lessons = [Lesson(lesson_number=1, title="Intro", lesson_link="http://example.com/lesson1")]
        course = Course(
            title="Machine Learning Fundamentals",
            instructor="Dr. Smith",
            course_link="http://example.com/ml",
            lessons=lessons
        )
        self.vector_store.add_course_metadata(course)
        
        # Test exact match
        resolved = self.vector_store._resolve_course_name("Machine Learning Fundamentals")
        assert resolved == "Machine Learning Fundamentals"
        
        # Test partial match
        resolved = self.vector_store._resolve_course_name("Machine Learning")
        assert resolved == "Machine Learning Fundamentals"
    
    def test_resolve_course_name_not_found(self):
        """Test course name resolution when course doesn't exist"""
        resolved = self.vector_store._resolve_course_name("Nonexistent Course")
        assert resolved is None
    
    def test_search_with_course_filter(self):
        """Test search with course name filter"""
        # Add data for multiple courses
        chunks = [
            CourseChunk(course_title="Python Course", lesson_number=1, chunk_index=0, content="Python programming basics"),
            CourseChunk(course_title="Java Course", lesson_number=1, chunk_index=0, content="Java programming basics")
        ]
        self.vector_store.add_course_content(chunks)
        
        # Add course metadata for resolution
        python_course = Course(
            title="Python Course",
            instructor="Python Teacher",
            course_link="http://example.com/python",
            lessons=[Lesson(lesson_number=1, title="Intro", lesson_link="http://example.com/python/1")]
        )
        self.vector_store.add_course_metadata(python_course)
        
        # Search with course filter
        results = self.vector_store.search("programming", course_name="Python Course")
        
        assert not results.is_empty()
        assert "Python" in results.documents[0]
        assert results.metadata[0]['course_title'] == "Python Course"
    
    def test_search_with_lesson_filter(self):
        """Test search with lesson number filter"""
        chunks = [
            CourseChunk(course_title="Test Course", lesson_number=1, chunk_index=0, content="Lesson 1 content"),
            CourseChunk(course_title="Test Course", lesson_number=2, chunk_index=1, content="Lesson 2 content")
        ]
        self.vector_store.add_course_content(chunks)
        
        results = self.vector_store.search("content", lesson_number=2)
        
        assert not results.is_empty()
        assert "Lesson 2" in results.documents[0]
        assert results.metadata[0]['lesson_number'] == 2
    
    def test_search_with_nonexistent_course_filter(self):
        """Test search with course filter that doesn't exist"""
        results = self.vector_store.search("test", course_name="Nonexistent Course")
        
        assert results.error is not None
        assert "No course found matching" in results.error
    
    def test_build_filter_combinations(self):
        """Test various filter combinations"""
        # No filters
        filter_dict = self.vector_store._build_filter(None, None)
        assert filter_dict is None
        
        # Course only
        filter_dict = self.vector_store._build_filter("Test Course", None)
        assert filter_dict == {"course_title": "Test Course"}
        
        # Lesson only
        filter_dict = self.vector_store._build_filter(None, 1)
        assert filter_dict == {"lesson_number": 1}
        
        # Both filters
        filter_dict = self.vector_store._build_filter("Test Course", 1)
        expected = {"$and": [
            {"course_title": "Test Course"},
            {"lesson_number": 1}
        ]}
        assert filter_dict == expected
    
    def test_get_existing_course_titles(self):
        """Test getting list of existing course titles"""
        # Initially empty
        titles = self.vector_store.get_existing_course_titles()
        assert titles == []
        
        # Add courses
        course1 = Course(title="Course 1", instructor="Teacher 1", course_link="http://example.com/1", lessons=[])
        course2 = Course(title="Course 2", instructor="Teacher 2", course_link="http://example.com/2", lessons=[])
        self.vector_store.add_course_metadata(course1)
        self.vector_store.add_course_metadata(course2)
        
        titles = self.vector_store.get_existing_course_titles()
        assert len(titles) == 2
        assert "Course 1" in titles
        assert "Course 2" in titles
    
    def test_get_course_count(self):
        """Test getting course count"""
        assert self.vector_store.get_course_count() == 0
        
        course = Course(title="Test Course", instructor="Teacher", course_link="http://example.com", lessons=[])
        self.vector_store.add_course_metadata(course)
        
        assert self.vector_store.get_course_count() == 1
    
    def test_get_all_courses_metadata(self):
        """Test getting all courses metadata"""
        # Add course with lessons
        lessons = [
            Lesson(lesson_number=1, title="Intro", lesson_link="http://example.com/lesson1"),
            Lesson(lesson_number=2, title="Advanced", lesson_link="http://example.com/lesson2")
        ]
        course = Course(title="Test Course", instructor="Teacher", course_link="http://example.com/course", lessons=lessons)
        self.vector_store.add_course_metadata(course)
        
        metadata_list = self.vector_store.get_all_courses_metadata()
        
        assert len(metadata_list) == 1
        metadata = metadata_list[0]
        assert metadata['title'] == "Test Course"
        assert metadata['instructor'] == "Teacher"
        assert 'lessons' in metadata  # Should be parsed from JSON
        assert len(metadata['lessons']) == 2
        assert metadata['lessons'][0]['lesson_number'] == 1
        assert metadata['lessons'][0]['lesson_title'] == "Intro"
    
    def test_get_course_link(self):
        """Test getting course link"""
        course = Course(title="Test Course", instructor="Teacher", course_link="http://example.com/course", lessons=[])
        self.vector_store.add_course_metadata(course)
        
        link = self.vector_store.get_course_link("Test Course")
        assert link == "http://example.com/course"
        
        # Test nonexistent course
        link = self.vector_store.get_course_link("Nonexistent")
        assert link is None
    
    def test_get_lesson_link(self):
        """Test getting specific lesson link"""
        lessons = [
            Lesson(lesson_number=1, title="Intro", lesson_link="http://example.com/lesson1"),
            Lesson(lesson_number=2, title="Advanced", lesson_link="http://example.com/lesson2")
        ]
        course = Course(title="Test Course", instructor="Teacher", course_link="http://example.com/course", lessons=lessons)
        self.vector_store.add_course_metadata(course)
        
        # Test existing lesson
        link = self.vector_store.get_lesson_link("Test Course", 1)
        assert link == "http://example.com/lesson1"
        
        # Test nonexistent lesson
        link = self.vector_store.get_lesson_link("Test Course", 999)
        assert link is None
        
        # Test nonexistent course
        link = self.vector_store.get_lesson_link("Nonexistent", 1)
        assert link is None
    
    def test_clear_all_data(self):
        """Test clearing all data"""
        # Add some data
        course = Course(title="Test Course", instructor="Teacher", course_link="http://example.com", lessons=[])
        self.vector_store.add_course_metadata(course)
        
        chunks = [CourseChunk(course_title="Test Course", lesson_number=1, chunk_index=0, content="Test content")]
        self.vector_store.add_course_content(chunks)
        
        # Verify data exists
        assert self.vector_store.get_course_count() > 0
        
        # Clear data
        self.vector_store.clear_all_data()
        
        # Verify data is cleared
        assert self.vector_store.get_course_count() == 0
        results = self.vector_store.course_content.get()
        assert len(results['ids']) == 0
    
    def test_search_results_from_chroma(self):
        """Test SearchResults.from_chroma class method"""
        chroma_results = {
            'documents': [['doc1', 'doc2']],
            'metadatas': [[{'key': 'value1'}, {'key': 'value2'}]],
            'distances': [[0.1, 0.2]]
        }
        
        results = SearchResults.from_chroma(chroma_results)
        
        assert results.documents == ['doc1', 'doc2']
        assert results.metadata == [{'key': 'value1'}, {'key': 'value2'}]
        assert results.distances == [0.1, 0.2]
        assert results.error is None
    
    def test_search_results_empty(self):
        """Test SearchResults.empty class method"""
        results = SearchResults.empty("Test error message")
        
        assert results.documents == []
        assert results.metadata == []
        assert results.distances == []
        assert results.error == "Test error message"
        assert results.is_empty() == True


if __name__ == "__main__":
    pytest.main([__file__])