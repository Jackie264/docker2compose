#!/usr/bin/env python3
"""
Test runner script for docker2compose project
"""

import sys
import subprocess
import os

def run_tests():
    """Run all tests and display results"""
    print("Running docker2compose test suite...")
    print("=" * 50)
    
    # Change to the project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # Run pytest with verbose output
    cmd = [sys.executable, '-m', 'pytest', 'tests/', '-v', '--tb=short']
    
    try:
        result = subprocess.run(cmd, check=False)
        
        if result.returncode == 0:
            print("\n" + "=" * 50)
            print("✅ All tests passed!")
            print("Test coverage has been successfully increased.")
        else:
            print("\n" + "=" * 50)
            print("❌ Some tests failed.")
            print("Please check the output above for details.")
            
        return result.returncode
        
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(run_tests())