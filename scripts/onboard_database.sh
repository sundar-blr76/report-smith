#!/bin/bash
#
# Convenience shell script to onboard a new database to ReportSmith.
#
# This script connects to your database, extracts the schema, and generates
# configuration files in config/applications/<app_id>/.
#
# Usage Examples:
#
# PostgreSQL:
#   ./scripts/onboard_database.sh \
#     --app-id my_app \
#     --app-name "My Application" \
#     --db-type postgresql \
#     --host localhost \
#     --port 5432 \
#     --database mydb \
#     --username user \
#     --password pass
#
# MySQL:
#   ./scripts/onboard_database.sh \
#     --app-id inventory \
#     --app-name "Inventory System" \
#     --db-type mysql \
#     --host localhost \
#     --port 3306 \
#     --database inventory \
#     --username root \
#     --password pass
#
# SQLite:
#   ./scripts/onboard_database.sh \
#     --app-id local_app \
#     --app-name "Local App" \
#     --db-type sqlite \
#     --database /path/to/database.db
#

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Set PYTHONPATH to include src directory
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# Change to project root
cd "$PROJECT_ROOT"

# Run the onboarding CLI
python3 -m reportsmith.onboarding.cli "$@"
