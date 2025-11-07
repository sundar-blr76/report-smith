# UI Module - Functional Documentation

**Module Path**: `src/reportsmith/ui/`  
**Version**: 1.0  
**Last Updated**: November 7, 2025

---

## Overview

The `ui` module provides an interactive web interface using Streamlit.

### Purpose
- Provide user-friendly web interface
- Display sample queries
- Show query results in formatted tables
- Real-time query processing

### Key Components
- **Streamlit App**: Main UI application
- **JSON Viewer**: Result visualization

---

## Features

### Query Interface
- Sample query dropdown
- Natural language input field
- Submit button for processing

### Results Display
- SQL query display
- Formatted result tables
- Execution metrics
- Error messages (if any)

### Status Monitoring
- API connection status
- Processing indicators
- Request history

---

## Usage

Start the UI:
```bash
streamlit run src/reportsmith/ui/app.py
```

Access at: http://localhost:8501

---

**See Also:**
- [API Module](API_MODULE.md)
- [High-Level Design](../HLD.md)
