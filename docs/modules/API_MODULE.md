# API Module - Functional Documentation

**Module Path**: `src/reportsmith/api/`  
**Version**: 1.0  
**Last Updated**: November 7, 2025

---

## Overview

The `api` module provides REST API endpoints for ReportSmith using FastAPI framework.

### Purpose
- Expose REST API for query processing
- Handle HTTP requests and responses
- Provide health and readiness checks
- CORS support for web clients

### Key Components
- **FastAPI Server**: Main API application
- **Endpoints**: /query, /health, /ready

---

## API Endpoints

### POST /query

**Description**: Process natural language query and return SQL/results.

**Request:**
```json
{
    "question": "Show AUM for equity funds",
    "execute": true,
    "format": "json"
}
```

**Response (Success):**
```json
{
    "status": "success",
    "request_id": "rid_abc123",
    "data": {
        "question": "Show AUM for equity funds",
        "sql": {
            "query": "SELECT SUM(funds.total_aum) AS aum...",
            "database": "financial_db"
        },
        "results": [...],
        "row_count": 1
    },
    "timings_ms": {
        "intent": 250,
        "semantic": 150,
        "total": 3594
    }
}
```

**Response (Error):**
```json
{
    "status": "error",
    "request_id": "rid_xyz789",
    "error": {
        "code": "INTENT_ANALYSIS_FAILED",
        "message": "Could not identify entities",
        "details": {...}
    }
}
```

---

### GET /health

**Description**: Basic liveness check.

**Response:**
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2025-11-07T04:47:45Z"
}
```

---

### GET /ready

**Description**: Readiness check for dependencies.

**Response:**
```json
{
    "status": "ready",
    "dependencies": {
        "database": "connected",
        "embeddings": "loaded",
        "knowledge_graph": "loaded",
        "llm_provider": "available"
    }
}
```

---

## Features

- **CORS Support**: Configurable cross-origin resource sharing
- **Request ID Tracking**: Unique ID for each request
- **Error Handling**: Comprehensive error responses
- **JSON Responses**: Consistent response format

---

**See Also:**
- [Agents Module](AGENTS_MODULE.md)
- [High-Level Design](../HLD.md)
