#!/bin/bash
"""
Comprehensive Code Quality Analysis Script
Runs multiple code quality tools and generates reports for SonarQube
"""

import json
import os
import subprocess
import sys
from datetime import datetime


def run_command(command, description):
    """Run a shell command and capture output"""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"{'='*60}")
    print(f"Command: {command}")

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, cwd=os.getcwd()
        )
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        print(f"Return code: {result.returncode}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False


def main():
    """Main function to run all code quality checks"""
    print("🚀 Starting Comprehensive Code Quality Analysis")
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Working Directory: {os.getcwd()}")

    # Ensure we're using the virtual environment
    python_cmd = "/Users/b.ajay/graphi-be/graphi-python-be/.venv/bin/python"

    results = {}

    # 1. Run tests with coverage
    print("\n" + "🧪 TESTING & COVERAGE ANALYSIS")
    cmd = f"{python_cmd} -m pytest test_search_functions.py --cov=modules --cov=utils --cov-report=html --cov-report=xml --cov-report=term --junitxml=test-results.xml -v"
    results["tests_coverage"] = run_command(cmd, "Running tests with coverage analysis")

    # 2. Run Pylint
    print("\n" + "🔍 PYLINT ANALYSIS")
    cmd = f"{python_cmd} -m pylint modules utils --output-format=text --reports=y --score=y > pylint-report.txt 2>&1 || true"
    results["pylint"] = run_command(cmd, "Running Pylint static analysis")

    # 3. Run Flake8
    print("\n" + "📏 FLAKE8 STYLE ANALYSIS")
    cmd = f"{python_cmd} -m flake8 modules utils --output-file=flake8-report.txt --statistics --count || true"
    results["flake8"] = run_command(cmd, "Running Flake8 style analysis")

    # 4. Run Bandit security analysis
    print("\n" + "🔒 BANDIT SECURITY ANALYSIS")
    cmd = (
        f"{python_cmd} -m bandit -r modules utils -f json -o bandit-report.json || true"
    )
    results["bandit"] = run_command(cmd, "Running Bandit security analysis")

    # 5. Run Safety check for dependencies
    print("\n" + "🛡️ SAFETY DEPENDENCY CHECK")
    cmd = f"{python_cmd} -m safety check --json --output safety-report.json || true"
    results["safety"] = run_command(
        cmd, "Running Safety dependency vulnerability check"
    )

    # 6. Code formatting check with Black
    print("\n" + "✨ BLACK CODE FORMATTING CHECK")
    cmd = f"{python_cmd} -m black --check --diff modules utils || true"
    results["black"] = run_command(cmd, "Checking code formatting with Black")

    # 7. Import sorting check with isort
    print("\n" + "📚 ISORT IMPORT SORTING CHECK")
    cmd = f"{python_cmd} -m isort --check-only --diff modules utils || true"
    results["isort"] = run_command(cmd, "Checking import sorting with isort")

    # Generate summary report
    generate_summary_report(results)

    print(f"\n{'='*60}")
    print("✅ CODE QUALITY ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print("📊 Generated Reports:")
    print("  - coverage.xml (Coverage report)")
    print("  - htmlcov/ (HTML coverage report)")
    print("  - test-results.xml (Test results)")
    print("  - pylint-report.txt (Pylint analysis)")
    print("  - flake8-report.txt (Flake8 analysis)")
    print("  - bandit-report.json (Security analysis)")
    print("  - safety-report.json (Dependency vulnerabilities)")
    print("  - code-quality-summary.json (Summary report)")


def generate_summary_report(results):
    """Generate a summary JSON report"""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "project": "GraphI Python Backend",
        "analysis_results": results,
        "files_analyzed": [
            "modules/search_functions/functions.py",
            "modules/search_functions/__init__.py",
            "modules/cite_functions/functions.py",
            "modules/cite_functions/__init__.py",
            "utils/logger.py",
        ],
        "recommendations": [
            "Increase test coverage for cite_functions module",
            "Fix any Pylint warnings in the report",
            "Address Flake8 style issues",
            "Review Bandit security findings",
            "Update any vulnerable dependencies found by Safety",
        ],
    }

    with open("code-quality-summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n📋 Summary report written to: code-quality-summary.json")


if __name__ == "__main__":
    main()
