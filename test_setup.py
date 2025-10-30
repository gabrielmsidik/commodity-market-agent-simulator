"""Test script to verify the setup is correct."""

import sys
import os

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        import flask
        print("✓ Flask")
    except ImportError as e:
        print(f"✗ Flask: {e}")
        return False
    
    try:
        import langgraph
        print("✓ LangGraph")
    except ImportError as e:
        print(f"✗ LangGraph: {e}")
        return False
    
    try:
        import langchain
        print("✓ LangChain")
    except ImportError as e:
        print(f"✗ LangChain: {e}")
        return False
    
    try:
        import sqlalchemy
        print("✓ SQLAlchemy")
    except ImportError as e:
        print(f"✗ SQLAlchemy: {e}")
        return False
    
    try:
        import plotly
        print("✓ Plotly")
    except ImportError as e:
        print(f"✗ Plotly: {e}")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✓ python-dotenv")
    except ImportError as e:
        print(f"✗ python-dotenv: {e}")
        return False
    
    return True


def test_project_structure():
    """Test that all required files and directories exist."""
    print("\nTesting project structure...")
    
    required_files = [
        "app.py",
        "requirements.txt",
        ".env.example",
        "README.md",
        "USAGE_GUIDE.md",
        "documentation.md",
        "src/__init__.py",
        "src/config.py",
        "src/models/state.py",
        "src/agents/llm.py",
        "src/agents/tools.py",
        "src/graph/nodes.py",
        "src/graph/workflow.py",
        "src/simulation/config.py",
        "src/simulation/shoppers.py",
        "src/simulation/runner.py",
        "src/database/models.py",
        "src/database/operations.py",
        "src/web/app.py",
        "templates/index.html",
        "static/style.css",
        "static/app.js"
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} (missing)")
            all_exist = False
    
    return all_exist


def test_env_file():
    """Test that .env file exists or can be created."""
    print("\nTesting environment configuration...")
    
    if os.path.exists(".env"):
        print("✓ .env file exists")
        return True
    elif os.path.exists(".env.example"):
        print("⚠ .env file not found, but .env.example exists")
        print("  Please copy .env.example to .env and add your API keys")
        return True
    else:
        print("✗ Neither .env nor .env.example found")
        return False


def test_module_imports():
    """Test that project modules can be imported."""
    print("\nTesting project modules...")
    
    try:
        from src.config import get_config
        print("✓ src.config")
    except Exception as e:
        print(f"✗ src.config: {e}")
        return False
    
    try:
        from src.models.state import EconomicState
        print("✓ src.models.state")
    except Exception as e:
        print(f"✗ src.models.state: {e}")
        return False
    
    try:
        from src.simulation.config import SimulationConfig
        print("✓ src.simulation.config")
    except Exception as e:
        print(f"✗ src.simulation.config: {e}")
        return False
    
    try:
        from src.simulation.shoppers import generate_shopper_database
        print("✓ src.simulation.shoppers")
    except Exception as e:
        print(f"✗ src.simulation.shoppers: {e}")
        return False
    
    try:
        from src.database.models import Simulation
        print("✓ src.database.models")
    except Exception as e:
        print(f"✗ src.database.models: {e}")
        return False
    
    try:
        from src.web import create_app
        print("✓ src.web")
    except Exception as e:
        print(f"✗ src.web: {e}")
        return False
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Commodity Market Agent Simulator - Setup Test")
    print("=" * 60)
    
    results = []
    
    # Test imports
    results.append(("Dependencies", test_imports()))
    
    # Test project structure
    results.append(("Project Structure", test_project_structure()))
    
    # Test env file
    results.append(("Environment Config", test_env_file()))
    
    # Test module imports
    results.append(("Project Modules", test_module_imports()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ All tests passed! The setup is complete.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env (if not done)")
        print("2. Edit .env with your API keys")
        print("3. Run: python -m src.database.init_db")
        print("4. Run: python app.py")
        print("5. Open browser to http://localhost:5000")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

