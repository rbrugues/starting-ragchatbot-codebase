# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Start Application
```bash
# Quick start with shell script
chmod +x run.sh
./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

### Dependencies
```bash
# Install dependencies
uv sync

# Add new dependency
uv add package-name
```

### Environment Setup
```bash
# Copy environment template and add your API key
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=your-key-here
```

## Architecture Overview

This is a RAG (Retrieval-Augmented Generation) chatbot system with the following key components:

### Backend Structure (`/backend/`)
- **`app.py`** - FastAPI application with CORS middleware, serves both API endpoints and static frontend
- **`rag_system.py`** - Main orchestrator that coordinates all components for query processing
- **`config.py`** - Configuration management with environment variables and defaults
- **`vector_store.py`** - ChromaDB integration for semantic search with SentenceTransformers embeddings
- **`ai_generator.py`** - Anthropic Claude API integration for response generation
- **`document_processor.py`** - Text chunking and processing for course documents  
- **`session_manager.py`** - User session and conversation history management
- **`search_tools.py`** - Tool-based search system for structured queries
- **`models.py`** - Pydantic models for Course, Lesson, and CourseChunk data structures

### Frontend (`/frontend/`)
- Simple HTML/CSS/JavaScript web interface
- Communicates with backend via `/api/query` and `/api/courses` endpoints

### Data Flow
1. Course documents in `/docs/` are processed into chunks on startup
2. Chunks are embedded using `all-MiniLM-L6-v2` and stored in ChromaDB
3. User queries trigger semantic search to find relevant chunks  
4. Retrieved context + conversation history is sent to Claude for response generation
5. Session management maintains conversation context across queries

### Key Technologies
- **FastAPI** - Web framework serving both API and static files
- **ChromaDB** - Vector database for semantic search
- **SentenceTransformers** - Text embeddings (`all-MiniLM-L6-v2`)
- **Anthropic Claude** - AI text generation (`claude-sonnet-4-20250514`)
- **uv** - Python package manager and virtual environment

### Configuration
- Environment variables loaded from `.env` file
- Key settings in `config.py`: chunk size (800), overlap (100), max results (5)
- ChromaDB persisted to `./backend/chroma_db`

### API Endpoints
- `POST /api/query` - Process user questions with RAG system
- `GET /api/courses` - Get course statistics and metadata
- `GET /` - Serves frontend HTML interface

Application runs on `http://localhost:8000` with API docs at `/docs`.
- use uv to run python files or add any dependencies