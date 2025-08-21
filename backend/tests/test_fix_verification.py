#!/usr/bin/env python3
"""
Verification test for the critical bug fix
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai_generator import AIGenerator


def test_critical_fix():
    """Test that the critical bug is fixed"""
    print("Testing critical bug fix...")

    # Test without API key (should use mock response now)
    generator = AIGenerator("", "claude-sonnet-4-20250514")

    try:
        response = generator.generate_response("What is computer use?")
        print(f"✅ SUCCESS: Got response without API key: {response[:50]}...")
        return True
    except AttributeError as e:
        print(f"❌ FAILED: Still getting AttributeError: {e}")
        return False
    except Exception as e:
        print(f"⚠️  OTHER ERROR: {e}")
        return False


def test_outline_query():
    """Test outline query without API key"""
    print("\nTesting outline query...")

    generator = AIGenerator("", "claude-sonnet-4-20250514")

    try:
        response = generator.generate_response("What's the outline of the MCP course?")
        print(f"✅ SUCCESS: Got outline response: {response[:100]}...")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("CRITICAL BUG FIX VERIFICATION")
    print("=" * 60)

    success1 = test_critical_fix()
    success2 = test_outline_query()

    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 ALL TESTS PASSED - CRITICAL BUG IS FIXED!")
    else:
        print("💥 SOME TESTS FAILED - BUG MAY STILL EXIST")
    print("=" * 60)
