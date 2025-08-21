#!/bin/bash
# Run linting checks

echo "🔍 Running code quality checks..."

# Check with flake8
echo "  📏 Checking code style with flake8..."
uv run flake8 backend/

# Check import sorting
echo "  📦 Checking import sorting with isort..."
uv run isort --check-only --diff backend/

# Check code formatting
echo "  🖤 Checking code formatting with black..."
uv run black --check --diff backend/

echo "✅ All linting checks completed!"