#!/usr/bin/env python3
"""Verify project setup and dependencies."""

import sys
from pathlib import Path

def check_dependencies():
    """Check all required dependencies."""
    print("=" * 60)
    print("🔍 Konko Agent - Setup Verification")
    print("=" * 60)

    # Python version
    print(f"\n✓ Python: {sys.version.split()[0]}")

    # Check imports
    deps = {
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'langchain': 'LangChain',
        'langchain_openai': 'LangChain OpenAI',
        'langgraph': 'LangGraph',
        'langsmith': 'LangSmith',
        'openai': 'OpenAI SDK',
        'pydantic': 'Pydantic',
        'yaml': 'PyYAML',
        'redis': 'Redis',
        'dotenv': 'python-dotenv',
    }

    print("\n📦 Dependencies:")
    for module, name in deps.items():
        try:
            mod = __import__(module)
            version = getattr(mod, '__version__', 'installed')
            print(f"  ✓ {name:20} {version}")
        except ImportError:
            print(f"  ✗ {name:20} NOT INSTALLED")

    # Check project structure
    print("\n📁 Project Structure:")
    required_dirs = [
        'packages/agent-core',
        'packages/agent-runtime',
        'packages/agent-config',
        'tests',
        'examples',
    ]

    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"  ✓ {dir_path}")
        else:
            print(f"  ✗ {dir_path} (missing)")

    # Check environment
    print("\n🔐 Environment:")
    env_file = Path('.env')
    if env_file.exists():
        print(f"  ✓ .env file exists")

        # Check for required vars
        from dotenv import load_dotenv
        import os
        load_dotenv()

        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key and openai_key != 'your-openai-api-key-here':
            print(f"  ✓ OPENAI_API_KEY configured")
        else:
            print(f"  ⚠ OPENAI_API_KEY not set (required for LLM)")
    else:
        print(f"  ⚠ .env file not found (copy from .env.example)")

    print("\n" + "=" * 60)
    print("✅ Setup verification complete!")
    print("=" * 60)

if __name__ == '__main__':
    check_dependencies()
