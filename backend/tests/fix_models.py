#!/usr/bin/env python3
"""Script to fix Pydantic model usage in test files"""

import re
import os

def fix_course_chunk_usage(content):
    """Fix CourseChunk constructor calls"""
    # Pattern: CourseChunk("title", number, index, "content")
    pattern = r'CourseChunk\("([^"]+)",\s*(\d+),\s*(\d+),\s*"([^"]+)"\)'
    replacement = r'CourseChunk(course_title="\1", lesson_number=\2, chunk_index=\3, content="\4")'
    return re.sub(pattern, replacement, content)

def fix_course_usage(content):
    """Fix Course constructor calls"""
    # Pattern: Course("title", "instructor", "link", lessons)
    pattern = r'Course\("([^"]+)",\s*"([^"]*)",\s*"([^"]*)",\s*(\[.*?\])\)'
    replacement = r'Course(title="\1", instructor="\2", course_link="\3", lessons=\4)'
    return re.sub(pattern, replacement, content)

def fix_lesson_usage(content):
    """Fix Lesson constructor calls"""
    # Pattern: Lesson(number, "title", "link")
    pattern = r'Lesson\((\d+),\s*"([^"]+)",\s*"([^"]*)"\)'
    replacement = r'Lesson(lesson_number=\1, title="\2", lesson_link="\3")'
    return re.sub(pattern, replacement, content)

def fix_file(filepath):
    """Fix a single file"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Apply fixes
    content = fix_course_chunk_usage(content)
    content = fix_course_usage(content)
    content = fix_lesson_usage(content)
    
    # Only write if changes were made
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Fixed {filepath}")
    else:
        print(f"No changes needed for {filepath}")

if __name__ == "__main__":
    test_files = [
        "test_vector_store.py",
        "test_rag_system.py",
        "test_course_search_tool.py"
    ]
    
    for filename in test_files:
        filepath = os.path.join("tests", filename)
        if os.path.exists(filepath):
            fix_file(filepath)