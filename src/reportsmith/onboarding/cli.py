"""Command-line interface for database onboarding."""

import argparse
import sys
from pathlib import Path

from ..config_system.config_models import DatabaseType, DatabaseConfig
from .onboarding_manager import OnboardingManager
from ..logger import get_logger

logger = get_logger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="ReportSmith Database Onboarding Tool - Infer schema and generate configurations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # PostgreSQL database
  python -m reportsmith.onboarding.cli \\
    --app-id my_app \\
    --app-name "My Application" \\
    --db-type postgresql \\
    --host localhost \\
    --port 5432 \\
    --database mydb \\
    --username user \\
    --password pass \\
    --output-dir ./config/applications

  # MySQL database with specific schema
  python -m reportsmith.onboarding.cli \\
    --app-id inventory_system \\
    --app-name "Inventory Management" \\
    --db-type mysql \\
    --host db.example.com \\
    --port 3306 \\
    --database inventory \\
    --schema public \\
    --username dbuser \\
    --password dbpass \\
    --output-dir ./config/applications

  # Oracle database
  python -m reportsmith.onboarding.cli \\
    --app-id erp_system \\
    --app-name "ERP System" \\
    --db-type oracle \\
    --host oracle.example.com \\
    --port 1521 \\
    --service-name ORCL \\
    --username system \\
    --password oracle \\
    --output-dir ./config/applications

  # Introspect specific tables only
  python -m reportsmith.onboarding.cli \\
    --app-id sales_app \\
    --app-name "Sales Application" \\
    --db-type postgresql \\
    --host localhost \\
    --port 5432 \\
    --database sales \\
    --username user \\
    --password pass \\
    --tables customers orders products \\
    --output-dir ./config/applications
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--app-id',
        required=True,
        help='Application identifier (e.g., fund_accounting)'
    )
    
    parser.add_argument(
        '--app-name',
        required=True,
        help='Human-readable application name (e.g., "Fund Accounting System")'
    )
    
    parser.add_argument(
        '--db-type',
        required=True,
        choices=['postgresql', 'mysql', 'oracle', 'sqlserver', 'sqlite'],
        help='Database type'
    )
    
    parser.add_argument(
        '--host',
        help='Database host (not required for SQLite)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        help='Database port'
    )
    
    parser.add_argument(
        '--database',
        required=True,
        help='Database name (or file path for SQLite)'
    )
    
    parser.add_argument(
        '--username',
        help='Database username'
    )
    
    parser.add_argument(
        '--password',
        help='Database password'
    )
    
    # Optional arguments
    parser.add_argument(
        '--schema',
        default='public',
        help='Database schema to introspect (default: public)'
    )
    
    parser.add_argument(
        '--service-name',
        help='Oracle service name (required for Oracle)'
    )
    
    parser.add_argument(
        '--tables',
        nargs='+',
        help='Specific tables to introspect (default: all tables)'
    )
    
    parser.add_argument(
        '--business-function',
        help='Brief description of business function (e.g., "Fund Management & Client Portfolio Tracking")'
    )
    
    parser.add_argument(
        '--output-dir',
        default='./config/applications',
        help='Output directory for generated configurations (default: ./config/applications)'
    )
    
    return parser.parse_args()


def validate_args(args):
    """Validate command-line arguments."""
    # For non-SQLite databases, require host and port
    if args.db_type != 'sqlite':
        if not args.host:
            print("Error: --host is required for non-SQLite databases")
            sys.exit(1)
        if not args.port:
            print("Error: --port is required for non-SQLite databases")
            sys.exit(1)
    
    # For Oracle, require service name
    if args.db_type == 'oracle' and not args.service_name:
        print("Error: --service-name is required for Oracle databases")
        sys.exit(1)
    
    # Set default ports if not specified
    if args.db_type != 'sqlite' and not args.port:
        default_ports = {
            'postgresql': 5432,
            'mysql': 3306,
            'oracle': 1521,
            'sqlserver': 1433
        }
        args.port = default_ports.get(args.db_type)


def main():
    """Main entry point for CLI."""
    args = parse_args()
    validate_args(args)
    
    print("=" * 80)
    print("REPORTSMITH DATABASE ONBOARDING TOOL")
    print("=" * 80)
    print(f"\nApplication: {args.app_name} ({args.app_id})")
    print(f"Database: {args.db_type} - {args.host or args.database}:{args.port or 'N/A'}")
    print(f"Schema: {args.schema}")
    print(f"Output: {args.output_dir}")
    print()
    
    try:
        # Create database configuration
        db_config = DatabaseConfig(
            database_type=DatabaseType(args.db_type),
            host=args.host or 'localhost',
            port=args.port or 5432,
            database_name=args.database,
            schema=args.schema,
            username=args.username,
            password=args.password,
            service_name=args.service_name
        )
        
        # Initialize onboarding manager
        manager = OnboardingManager(
            application_id=args.app_id,
            application_name=args.app_name,
            database_config=db_config
        )
        
        # Run onboarding
        output_paths = manager.run_onboarding(
            output_dir=args.output_dir,
            schema=args.schema if args.schema != 'public' else None,
            tables=args.tables,
            business_function=args.business_function
        )
        
        print("\n✓ Onboarding completed successfully!")
        
        return 0
        
    except Exception as e:
        logger.error(f"Onboarding failed: {e}")
        print(f"\n✗ Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
