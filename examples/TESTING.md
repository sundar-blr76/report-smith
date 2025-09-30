# Quick Test: Embedding Demo

## Running the Demo

```bash
cd examples
./run_embedding_demo.sh
```

**Expected output:**
- ✓ Loads 4 dimensions from column markers
- ✓ Loads ALL 62 dimension values (no limits)
- ✓ Demonstrates semantic search
- ✓ Shows dictionary table config
- ✓ Saves complete log to `logs/embedding_demo_YYYYMMDD_HHMMSS.log`

## Viewing Logs

```bash
# View latest log
cd examples
./view_latest_log.sh

# List all logs
ls -lt logs/*.log

# View specific log
cat logs/embedding_demo_20250930_171602.log
```

## Common Issues

1. **ModuleNotFoundError: No module named 'chromadb'**
   - Solution: `pip install -r requirements.txt`

2. **Config directory not found**
   - Solution: Run from project root or use the `run_embedding_demo.sh` script

3. **Database connection failed**
   - Check environment variables are set (FINANCIAL_TESTDB_*)
   - Verify database is accessible at 192.168.29.69:5432

## Direct Run (without script)

```bash
source venv/bin/activate
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
python3 examples/embedding_demo.py
```

**Note:** This won't create a log file, output goes to stdout only.

## Log File Format

Each log file contains:
- Header with timestamp
- Complete demo output (all 4 sections)
- Embedding statistics
- Footer with completion timestamp

Example log path:
```
examples/logs/embedding_demo_20250930_171602.log
```
