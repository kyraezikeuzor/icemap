#!/usr/bin/env python3
"""
Import merged case count data into the icemap database.
"""

import csv
import os
import sys
from datetime import datetime

# Add shared utilities to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

def import_case_count_data():
    """Import the merged case count CSV into the database."""
    
    # This would use the database connection from shared/database_utils.py
    # For now, we'll generate SQL statements
    
    csv_file = 'data/merged_case_counts.csv'
    sql_file = 'data/import_case_counts.sql'
    
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found")
        return False
    
    print(f"Reading case count data from {csv_file}...")
    
    sql_statements = [
        "-- Import script for geographic case count data",
        "-- Generated on " + datetime.now().isoformat(),
        "",
        "-- Clear existing data",
        "TRUNCATE TABLE geographic_case_counts;",
        "",
        "-- Import case count data",
        "INSERT INTO geographic_case_counts (category, case_count, subcounty_name, county_name, state_name) VALUES"
    ]
    
    values = []
    row_count = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                category = row['category']
                case_count = int(row['casecount'])
                subcounty = row['subcounty'] if row['subcounty'] else None
                county = row['county'] if row['county'] else None
                state = row['state']
                
                # Escape single quotes in names
                if subcounty:
                    subcounty = subcounty.replace("'", "''")
                if county:
                    county = county.replace("'", "''")
                state = state.replace("'", "''")
                
                # Format SQL value
                subcounty_val = f"'{subcounty}'" if subcounty else "NULL"
                county_val = f"'{county}'" if county else "NULL"
                
                value = f"('{category}', {case_count}, {subcounty_val}, {county_val}, '{state}')"
                values.append(value)
                row_count += 1
                
                # Write in batches of 1000 to avoid memory issues
                if len(values) >= 1000:
                    sql_statements.append(",\n".join(values) + ";")
                    sql_statements.append("")
                    sql_statements.append("INSERT INTO geographic_case_counts (category, case_count, subcounty_name, county_name, state_name) VALUES")
                    values = []
        
        # Write remaining values
        if values:
            sql_statements[-1] = sql_statements[-1]  # Keep the INSERT statement
            sql_statements.append(",\n".join(values) + ";")
        else:
            # Remove the last INSERT statement if no values left
            sql_statements.pop()
        
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return False
    
    # Write SQL file
    try:
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(sql_statements))
        
        print(f"Generated SQL import script: {sql_file}")
        print(f"Total records to import: {row_count:,}")
        
        # Show sample of what will be imported
        print("\nSample records:")
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i < 5:
                    print(f"  {row['category']:>10} | {int(row['casecount']):>6,} | {row['state']}")
                else:
                    break
        
        return True
        
    except Exception as e:
        print(f"Error writing SQL file: {e}")
        return False

def generate_analysis_queries():
    """Generate useful analysis queries for the imported data."""
    
    queries_file = 'data/analysis_queries.sql'
    
    queries = [
        "-- Analysis queries for ICE case count data",
        "-- Generated for icemap.dev transparency initiative",
        "",
        "-- Top 10 states by total case count",
        """SELECT 
    state_name,
    SUM(case_count) as total_cases,
    COUNT(*) as geographic_units
FROM geographic_case_counts 
GROUP BY state_name 
ORDER BY total_cases DESC 
LIMIT 10;""",
        "",
        "-- Case distribution by geographic level",
        """SELECT 
    category,
    COUNT(*) as record_count,
    SUM(case_count) as total_cases,
    AVG(case_count) as avg_cases_per_unit,
    MIN(case_count) as min_cases,
    MAX(case_count) as max_cases
FROM geographic_case_counts 
GROUP BY category 
ORDER BY total_cases DESC;""",
        "",
        "-- Top counties by case count",
        """SELECT 
    county_name,
    state_name,
    case_count
FROM geographic_case_counts 
WHERE category = 'county' 
ORDER BY case_count DESC 
LIMIT 20;""",
        "",
        "-- States with highest subcounty enforcement activity",
        """SELECT 
    state_name,
    COUNT(*) as subcounty_count,
    SUM(case_count) as total_subcounty_cases,
    AVG(case_count) as avg_per_subcounty
FROM geographic_case_counts 
WHERE category = 'subcounty' 
GROUP BY state_name 
ORDER BY total_subcounty_cases DESC 
LIMIT 15;""",
        "",
        "-- High-enforcement subcounty areas (500+ cases)",
        """SELECT 
    subcounty_name,
    county_name,
    state_name,
    case_count
FROM geographic_case_counts 
WHERE category = 'subcounty' 
    AND case_count >= 500 
ORDER BY case_count DESC;""",
        "",
        "-- Enforcement concentration analysis",
        """WITH state_totals AS (
    SELECT 
        state_name,
        SUM(case_count) as state_total
    FROM geographic_case_counts 
    WHERE category = 'subcounty'
    GROUP BY state_name
),
top_subcounties AS (
    SELECT 
        gc.state_name,
        gc.subcounty_name,
        gc.case_count,
        st.state_total,
        (gc.case_count::float / st.state_total * 100) as pct_of_state
    FROM geographic_case_counts gc
    JOIN state_totals st ON gc.state_name = st.state_name
    WHERE gc.category = 'subcounty'
    AND st.state_total > 1000  -- Only states with significant activity
)
SELECT 
    state_name,
    subcounty_name,
    case_count,
    ROUND(pct_of_state, 2) as percent_of_state_total
FROM top_subcounties
WHERE pct_of_state > 5  -- Subcounties with >5% of state's cases
ORDER BY state_name, pct_of_state DESC;"""
    ]
    
    try:
        with open(queries_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(queries))
        
        print(f"Generated analysis queries: {queries_file}")
        return True
        
    except Exception as e:
        print(f"Error writing queries file: {e}")
        return False

if __name__ == "__main__":
    print("ICE Case Count Data Import")
    print("=" * 50)
    
    # Import case count data
    if import_case_count_data():
        print("\n✅ Case count import script generated successfully")
    else:
        print("\n❌ Failed to generate import script")
        sys.exit(1)
    
    # Generate analysis queries
    if generate_analysis_queries():
        print("✅ Analysis queries generated successfully")
    else:
        print("❌ Failed to generate analysis queries")
    
    print("\n" + "=" * 50)
    print("Next steps:")
    print("1. Set up PostgreSQL database with the schema")
    print("2. Run: psql -d icemap -f data/import_case_counts.sql")
    print("3. Execute analysis queries for insights")
    print("4. Integrate with AWS Lambda for live updates")
    print("=" * 50)
