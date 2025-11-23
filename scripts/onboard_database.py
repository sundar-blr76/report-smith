#!/usr/bin/env python3
"""
Convenience script to onboard a new database to ReportSmith.

This script connects to your database, extracts the schema, and generates
configuration files in config/applications/<app_id>/.

Usage:
    python scripts/onboard_database.py

The script will interactively prompt for database connection details.
"""

import sys
import os
from pathlib import Path

# Add src directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from reportsmith.onboarding.cli import main

if __name__ == '__main__':
    print("=" * 80)
    print("ReportSmith Database Onboarding Script")
    print("=" * 80)
    print()
    print("This script will:")
    print("  1. Connect to your database")
    print("  2. Extract the schema (tables, columns, relationships)")
    print("  3. Generate configuration files in config/applications/<app_id>/")
    print()
    print("You can also run this directly with command-line arguments:")
    print("  python scripts/onboard_database.py --app-id my_app --db-type postgresql ...")
    print()
    print("For help with arguments:")
    print("  python scripts/onboard_database.py --help")
    print()
    
    sys.exit(main())
