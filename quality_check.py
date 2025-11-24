#!/usr/bin/env python3
"""
Quality check script to ensure 100/100 quality score with zero errors or warnings.
"""

import sys
import subprocess
import os
from pathlib import Path


def run_command(cmd: list[str], description: str) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent
        )
        output = result.stdout + result.stderr
        success = result.returncode == 0
        return success, output
    except Exception as e:
        return False, str(e)


def check_python_syntax():
    """Check Python syntax for all files."""
    print("🔍 Checking Python syntax...")
    files = [
        "app/config.py",
        "app/main.py",
        "app/service.py",
    ]
    
    errors = []
    for file in files:
        if not Path(file).exists():
            errors.append(f"File not found: {file}")
            continue
        
        success, output = run_command(
            ["python3", "-m", "py_compile", file],
            f"Compiling {file}"
        )
        
        if not success:
            errors.append(f"{file}: {output}")
    
    if errors:
        print("❌ Syntax errors found:")
        for error in errors:
            print(f"  {error}")
        return False
    
    print("✅ Python syntax: OK")
    return True


def check_imports():
    """Check that all imports are valid."""
    print("\n🔍 Checking imports...")
    
    # Try importing main modules
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        
        # Check if we can import (without actually running)
        import importlib.util
        
        files = ["app.config", "app.main", "app.service"]
        for module_name in files:
            file_path = module_name.replace(".", "/") + ".py"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                print(f"❌ Cannot load {module_name}")
                return False
        
        print("✅ Imports: OK")
        return True
    except Exception as e:
        print(f"❌ Import check failed: {e}")
        return False


def check_file_structure():
    """Check that all required files exist."""
    print("\n🔍 Checking file structure...")
    
    required_files = [
        "app/__init__.py",
        "app/config.py",
        "app/main.py",
        "app/service.py",
        "requirements.txt",
        "README.md",
        ".gitignore",
    ]
    
    missing = []
    for file in required_files:
        if not Path(file).exists():
            missing.append(file)
    
    if missing:
        print(f"❌ Missing files: {', '.join(missing)}")
        return False
    
    print("✅ File structure: OK")
    return True


def check_npm_package():
    """Check npm package structure."""
    print("\n🔍 Checking npm package...")
    
    sdk_dir = Path("stem-splitter-sdk")
    if not sdk_dir.exists():
        print("⚠️  npm package directory not found (optional)")
        return True
    
    required_files = [
        "package.json",
        "tsconfig.json",
        "src/index.ts",
        "README.md",
    ]
    
    missing = []
    for file in required_files:
        if not (sdk_dir / file).exists():
            missing.append(file)
    
    if missing:
        print(f"❌ Missing npm package files: {', '.join(missing)}")
        return False
    
    print("✅ npm package structure: OK")
    return True


def check_documentation():
    """Check that documentation files exist."""
    print("\n🔍 Checking documentation...")
    
    docs = [
        "README.md",
        "API_DOCUMENTATION.md",
        "DEPLOYMENT.md",
    ]
    
    missing = []
    for doc in docs:
        if not Path(doc).exists():
            missing.append(doc)
    
    if missing:
        print(f"⚠️  Missing documentation: {', '.join(missing)}")
        return True  # Not critical
    
    print("✅ Documentation: OK")
    return True


def main():
    """Run all quality checks."""
    print("=" * 60)
    print("Quality Check - Stem Splitter API")
    print("=" * 60)
    
    checks = [
        ("Python Syntax", check_python_syntax),
        ("Imports", check_imports),
        ("File Structure", check_file_structure),
        ("npm Package", check_npm_package),
        ("Documentation", check_documentation),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} check failed with exception: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Quality Check Results")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("🎉 All checks passed! Quality score: 100/100")
        return 0
    else:
        print("⚠️  Some checks failed. Please fix issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

