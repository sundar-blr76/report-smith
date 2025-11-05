#!/usr/bin/env python3
"""
Example: LLM-driven Extraction Enhancer

This example demonstrates all four functional requirements:
- FR-1: Extraction summary generation
- FR-2: Column ordering optimization
- FR-3: Predicate coercion
- FR-4: Iterative SQL validation

This is a standalone demonstration that shows expected behavior
without requiring dependencies or making actual LLM API calls.
"""


def example_summary_generation():
    """Example: FR-1 - Extraction Summary Generation"""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Extraction Summary Generation (FR-1)")
    print("=" * 80)
    
    # Note: This example shows the API usage without actual LLM calls
    # To run with real LLM, uncomment the OpenAI client initialization
    
    # from openai import OpenAI
    # client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    # enhancer = SqlEnhancer(llm_client=client)
    
    # For demonstration, we'll show the expected behavior
    print("\nScenario: User asks 'Show AUM for equity funds in Q4 2025'")
    print("\nGenerated SQL:")
    sql = """
    SELECT 
        funds.fund_type AS fund_type,
        SUM(funds.total_aum) AS aum
    FROM funds
    WHERE funds.fund_type = 'Equity Growth'
      AND funds.report_date >= '2025-10-01'
      AND funds.report_date <= '2025-12-31'
      AND funds.is_active = true
    GROUP BY funds.fund_type
    """
    print(sql)
    
    print("\nExpected Summary Output:")
    print("""
    Summary: Retrieved total AUM for equity funds in Q4 2025 (October-December 2025).
    
    Filters Applied:
    - fund_type = 'Equity Growth'
    - report_date range: 2025-10-01 to 2025-12-31
    - is_active = true (auto-filter)
    
    Transformations:
    - Q4 2025 converted to fiscal quarter date range (2025-10-01 to 2025-12-31)
    
    Assumptions:
    - Currency: USD (from column metadata)
    - Active records only (default filter)
    """)


def example_column_ordering():
    """Example: FR-2 - Column Ordering Optimization"""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Column Ordering Optimization (FR-2)")
    print("=" * 80)
    
    print("\nScenario: Query returns multiple columns in random order")
    print("\nOriginal Column Order:")
    original_columns = [
        "funds.total_aum",
        "funds.fund_type",
        "funds.expense_ratio",
        "funds.fund_name",
        "funds.fund_id",
        "funds.inception_date",
    ]
    for col in original_columns:
        print(f"  - {col}")
    
    print("\nLLM-Optimized Column Order:")
    print("(Primary identifiers → Metrics → Descriptive attributes)")
    optimized_columns = [
        "funds.fund_id",
        "funds.fund_name",
        "funds.total_aum",
        "funds.expense_ratio",
        "funds.fund_type",
        "funds.inception_date",
    ]
    for col in optimized_columns:
        print(f"  - {col}")
    
    print("\nReasoning:")
    print("""
    - fund_id, fund_name: Primary identifiers for human readability
    - total_aum, expense_ratio: Key metrics requested by user
    - fund_type, inception_date: Descriptive attributes for context
    """)


def example_predicate_coercion():
    """Example: FR-3 - Predicate Coercion"""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Predicate Coercion (FR-3)")
    print("=" * 80)
    
    examples = [
        {
            "type": "Date/Quarter",
            "input": "Q4 2025",
            "output": "date >= '2025-10-01' AND date <= '2025-12-31'",
            "description": "Fiscal quarter Q4 2025 → October-December 2025 date range",
        },
        {
            "type": "Date/Month",
            "input": "Apr-2025",
            "output": "date >= '2025-04-01' AND date <= '2025-04-30'",
            "description": "Month abbreviation → Full month date range",
        },
        {
            "type": "Currency (US)",
            "input": "$1.2M",
            "output": "1200000",
            "description": "Dollar amount with M suffix → Numeric value",
        },
        {
            "type": "Currency (India)",
            "input": "INR 12,00,000",
            "output": "1200000",
            "description": "Indian numbering format (lakh) → Standard numeric",
        },
        {
            "type": "Boolean (Y/N)",
            "input": "Y",
            "output": "true",
            "description": "Yes/No format → Boolean true/false",
        },
        {
            "type": "Boolean (1/0)",
            "input": "1",
            "output": "true",
            "description": "Numeric boolean → Boolean true/false",
        },
        {
            "type": "Numeric",
            "input": "1,500",
            "output": "1500",
            "description": "Comma-separated number → Numeric value",
        },
    ]
    
    for example in examples:
        print(f"\n{example['type']}:")
        print(f"  Input:  {example['input']}")
        print(f"  Output: {example['output']}")
        print(f"  Note:   {example['description']}")


def example_sql_validation():
    """Example: FR-4 - Iterative SQL Validation"""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Iterative SQL Validation & Refinement (FR-4)")
    print("=" * 80)
    
    print("\nScenario: Initial SQL is missing currency column in GROUP BY")
    print("\nIteration 1: Initial SQL")
    print("-" * 40)
    initial_sql = """
    SELECT 
        funds.fund_type AS fund_type,
        SUM(funds.total_aum) AS aum
    FROM funds
    WHERE funds.is_active = true
    GROUP BY funds.fund_type
    """
    print(initial_sql)
    
    print("\nValidation Result:")
    print("  Status: ✗ Invalid")
    print("  Issues:")
    print("    - Currency column 'currency_code' missing from SELECT")
    print("    - Currency column 'currency_code' missing from GROUP BY")
    print("  Warnings:")
    print("    - Multiple currencies detected in sample data")
    
    print("\nIteration 2: LLM Refined SQL")
    print("-" * 40)
    refined_sql = """
    SELECT 
        funds.fund_type AS fund_type,
        funds.currency_code AS currency_code,
        SUM(funds.total_aum) AS aum
    FROM funds
    WHERE funds.is_active = true
    GROUP BY funds.fund_type, funds.currency_code
    """
    print(refined_sql)
    
    print("\nValidation Result:")
    print("  Status: ✓ Valid")
    print("  Issues: None")
    print("  Warnings: None")
    
    print("\nRefinement Summary:")
    print("  Iterations: 2")
    print("  Changes Made:")
    print("    - Added 'currency_code' to SELECT clause")
    print("    - Added 'currency_code' to GROUP BY clause")
    print("  Reasoning:")
    print("    - Sample data showed mixed currencies (USD, EUR, GBP)")
    print("    - Aggregating without grouping by currency would be incorrect")
    print("    - Currency context is essential for interpreting AUM values")
    
    print("\nToken Usage:")
    print("  Iteration 1: 500 prompt + 100 completion = 600 total")
    print("  Iteration 2: 450 prompt + 80 completion = 530 total")
    print("  Total: 1,130 tokens")


def example_safety_features():
    """Example: Safety Features"""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Safety Features")
    print("=" * 80)
    
    print("\nRead-Only SQL Enforcement:")
    print("-" * 40)
    
    safe_queries = [
        "SELECT * FROM funds WHERE is_active = true",
        "WITH totals AS (SELECT ...) SELECT * FROM totals",
    ]
    
    unsafe_queries = [
        "INSERT INTO funds VALUES (...)",
        "UPDATE funds SET is_active = false",
        "DELETE FROM funds WHERE fund_id = 1",
        "DROP TABLE funds",
        "CREATE TABLE test (id INT)",
    ]
    
    print("\n✓ Allowed Queries (Read-Only):")
    for query in safe_queries:
        print(f"  - {query}")
    
    print("\n✗ Rejected Queries (DDL/DML):")
    for query in unsafe_queries:
        print(f"  - {query}")
    
    print("\n\nRate Limiting:")
    print("-" * 40)
    print("  Default: 60 requests per minute")
    print("  Prevents: Accidental runaway API calls")
    print("  Behavior: Returns error after limit exceeded")
    
    print("\n\nCost Caps:")
    print("-" * 40)
    print("  Default: 100,000 tokens per request")
    print("  Prevents: Excessive token usage and costs")
    print("  Behavior: Returns error when cap would be exceeded")


def main():
    """Run all examples"""
    print("\n" + "=" * 80)
    print("LLM-DRIVEN EXTRACTION ENHANCER - EXAMPLES")
    print("=" * 80)
    print("\nThis script demonstrates all four functional requirements:")
    print("  FR-1: Extraction summary generation")
    print("  FR-2: Column ordering optimization")
    print("  FR-3: Predicate value coercion")
    print("  FR-4: Iterative SQL validation")
    print("\nNote: These examples show expected behavior without making")
    print("      actual LLM API calls. To run with real LLM, configure")
    print("      the OpenAI/Anthropic/Gemini client.")
    
    # Run all examples
    example_summary_generation()
    example_column_ordering()
    example_predicate_coercion()
    example_sql_validation()
    example_safety_features()
    
    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80)
    print("\nFor full documentation, see: docs/EXTRACTION_ENHANCER.md")
    print("For tests, run: pytest tests/unit/test_extraction_enhancer.py -v")
    print()


if __name__ == "__main__":
    main()
