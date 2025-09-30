# FinancialTestDB Integration Guide

## Database Setup Responsibilities

**All database schema modifications must be done through the FinancialTestDB project** at:
`/home/sundar/sundar_projects/FinancialTestDB`

## Dictionary Tables to Create

The following dictionary tables should be created in the FinancialTestDB project to enhance ReportSmith's dimension loading:

### 1. Fund Type Dictionary
```sql
CREATE TABLE fund_type_dictionary (
    fund_type_code VARCHAR(50) PRIMARY KEY,
    fund_type_name VARCHAR(100) NOT NULL,
    description TEXT,
    investment_strategy TEXT,
    risk_category VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    effective_date DATE DEFAULT CURRENT_DATE,
    region VARCHAR(10) DEFAULT 'US',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Risk Rating Dictionary
```sql
CREATE TABLE risk_rating_dictionary (
    risk_code VARCHAR(20) PRIMARY KEY,
    risk_name VARCHAR(100) NOT NULL,
    description TEXT,
    risk_level INTEGER,
    regulatory_classification VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. Client Type Dictionary
```sql
CREATE TABLE client_type_dictionary (
    client_type_code VARCHAR(50) PRIMARY KEY,
    client_type_name VARCHAR(100) NOT NULL,
    description TEXT,
    regulatory_requirements TEXT,
    minimum_investment DECIMAL(15,2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4. Transaction Type Dictionary
```sql
CREATE TABLE transaction_type_dictionary (
    transaction_type_code VARCHAR(50) PRIMARY KEY,
    transaction_type_name VARCHAR(100) NOT NULL,
    description TEXT,
    impact_type VARCHAR(20), -- 'INFLOW', 'OUTFLOW', 'NEUTRAL'
    requires_approval BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## ReportSmith Configuration

Once dictionary tables are created in FinancialTestDB, enable them in ReportSmith by updating the schema.yaml configuration:

```yaml
dimensions:
  fund_type:
    table: funds
    column: fund_type
    dictionary_table: fund_type_dictionary
    dictionary_value_column: fund_type_code
    dictionary_description_column: description
    dictionary_predicates:
      - "is_active = true"
      - "effective_date <= CURRENT_DATE"
```

## Benefits

- Enhanced semantic embeddings with rich descriptions
- Better natural language query matching
- Centralized dictionary management
- Flexible filtering with predicates
- Temporal and regional support