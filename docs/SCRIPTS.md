# ReportSmith Application Scripts

## Overview
This document describes the application startup and restart scripts for ReportSmith.

## Scripts

### 1. start.sh
**Purpose**: Initializes and starts the ReportSmith application

**Features**:
- Clears previous run's application logs
- Validates required environment variables
- Constructs database URL from environment variables
- Creates/activates Python virtual environment
- Installs/updates dependencies
- Configures logging with timestamped log files
- Initializes core application components

**Required Environment Variables**:
- `FINANCIAL_TESTDB_HOST` - Database host
- `FINANCIAL_TESTDB_PORT` - Database port  
- `FINANCIAL_TESTDB_NAME` - Database name
- `FINANCIAL_TESTDB_USER` - Database user
- `FINANCIAL_TESTDB_PASSWORD` - Database password

**Output**:
- Log files: `logs/app_<timestamp>.log`
- Console output with color-coded status messages

### 2. restart.sh (NEW)
**Purpose**: Complete application restart with cleanup and verification

**5-Step Process**:

1. **Purge Logs**: Removes all previous log files from `logs/` directory
2. **Kill Processes**: Terminates any running ReportSmith processes
   - Graceful shutdown (SIGTERM) with 2-second wait
   - Force kill (SIGKILL) if needed
3. **Start Application**: Launches application via start.sh
   - Runs in background
   - Captures startup output
4. **Monitor Logs**: Displays initial log output
   - Finds most recent log file
   - Shows first 20 lines
5. **Verify Success**: Confirms successful restart
   - Checks for success indicators in logs
   - Displays verification status

**Color-Coded Output**:
- 🟢 Green: Success messages
- 🟡 Yellow: In-progress/warning messages  
- 🔴 Red: Error messages
- 🔵 Blue: Headers and informational messages

**Helpful Commands Displayed**:
```bash
# View logs
tail -f logs/app_<timestamp>.log

# Check running processes
ps aux | grep reportsmith

# Stop application
pkill -f reportsmith
```

## Usage

### Normal Startup
```bash
./start.sh
```

### Full Restart (with cleanup)
```bash
./restart.sh
```

## Log Management

**Log Directory**: `logs/`

**Log Format**: `app_YYYYMMDD_HHMMSS.log`

**Log Content**:
- Timestamp
- Logger name
- Log level
- Message

**Log Levels**:
- INFO: Normal operations
- ERROR: Errors with stack traces
- WARNING: Warnings

**Cleanup**:
- `start.sh`: Clears logs from previous run only
- `restart.sh`: Purges ALL log files

## Notes

- Both scripts are executable (`chmod +x`)
- Scripts use color-coded output for better visibility
- Database URL is constructed dynamically from environment variables
- Logs excluded from git tracking via .gitignore
- Virtual environment auto-created if missing
- Dependencies auto-installed from requirements.txt
