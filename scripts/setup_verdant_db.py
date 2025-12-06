#!/usr/bin/env python3
"""
Setup Verdant PostgreSQL database with tables and sample data.
"""

import os
import subprocess
import json
import pandas as pd

# PostgreSQL connection for initial setup (using default postgres user)
PG_BIN = "/usr/local/opt/postgresql@15/bin"
DB_NAME = "verdant_db_new"

# Table schemas from cache
CACHE_DIR = os.path.join(
    os.path.dirname(__file__),
    "..", "semantic_parser", "modules", "verdant", "cache"
)

TABLES = [
    "fundcashflow",
    "fundinvestmentproperties",
    "fundinvestmenttimeproperties",
    "fundtimeproperties",
    "handtransformedportfolioinvestmentswithcfraw"
]

# Map JSON data types to PostgreSQL types
def json_to_pg_type(col):
    data_type = col["data_type"]
    max_len = col.get("character_maximum_length")

    if data_type == "text":
        return "TEXT"
    elif data_type == "character varying":
        return f"VARCHAR({max_len})" if max_len else "VARCHAR(255)"
    elif data_type == "character":
        return f"CHAR({max_len})" if max_len else "CHAR(1)"
    elif data_type == "numeric":
        return "NUMERIC"
    elif data_type == "date":
        return "DATE"
    elif data_type == "smallint":
        return "SMALLINT"
    elif data_type == "integer":
        return "INTEGER"
    else:
        return "TEXT"

def run_psql(sql, database="postgres"):
    """Run SQL command using psql"""
    cmd = [f"{PG_BIN}/psql", "-d", database, "-c", sql]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 and "already exists" not in result.stderr:
        print(f"Warning: {result.stderr}")
    return result

def create_database():
    """Create the verdant database"""
    print(f"Creating database {DB_NAME}...")
    run_psql(f"DROP DATABASE IF EXISTS {DB_NAME};")
    run_psql(f"CREATE DATABASE {DB_NAME};")
    print(f"Database {DB_NAME} created.")

def create_roles():
    """Create required roles"""
    print("Creating roles...")

    # Create creator_role
    run_psql("DROP ROLE IF EXISTS creator_role;")
    run_psql("CREATE ROLE creator_role WITH LOGIN PASSWORD 'creator_role';")
    run_psql(f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO creator_role;", "postgres")

    # Create select_user
    run_psql("DROP ROLE IF EXISTS select_user;")
    run_psql("CREATE ROLE select_user WITH LOGIN PASSWORD 'select_user';")

    print("Roles created.")

def create_table(table_name):
    """Create a table from its schema JSON"""
    schema_path = os.path.join(CACHE_DIR, table_name, f"{table_name}_schema.json")

    if not os.path.exists(schema_path):
        print(f"Schema not found for {table_name}")
        return False

    with open(schema_path) as f:
        schema = json.load(f)

    # Build CREATE TABLE statement
    # Use proper case for table names
    proper_table_name = {
        "fundcashflow": "FundCashFlow",
        "fundinvestmentproperties": "FundInvestmentProperties",
        "fundinvestmenttimeproperties": "FundInvestmentTimeProperties",
        "fundtimeproperties": "FundTimeProperties",
        "handtransformedportfolioinvestmentswithcfraw": "HandTransformedPortfolioInvestmentswithCFRaw"
    }

    table_display_name = proper_table_name.get(table_name, table_name)

    columns = []
    for col in schema:
        col_name = col["column_name"]
        col_type = json_to_pg_type(col)
        columns.append(f'"{col_name}" {col_type}')

    sql = f'CREATE TABLE IF NOT EXISTS "{table_display_name}" (\n  ' + ",\n  ".join(columns) + "\n);"

    print(f"Creating table {table_display_name}...")
    result = run_psql(sql, DB_NAME)

    return True

def load_sample_data(table_name):
    """Load sample data from CSV"""
    csv_path = os.path.join(CACHE_DIR, table_name, f"{table_name}_sample_data.csv")

    if not os.path.exists(csv_path):
        print(f"Sample data not found for {table_name}")
        return False

    proper_table_name = {
        "fundcashflow": "FundCashFlow",
        "fundinvestmentproperties": "FundInvestmentProperties",
        "fundinvestmenttimeproperties": "FundInvestmentTimeProperties",
        "fundtimeproperties": "FundTimeProperties",
        "handtransformedportfolioinvestmentswithcfraw": "HandTransformedPortfolioInvestmentswithCFRaw"
    }

    table_display_name = proper_table_name.get(table_name, table_name)

    # Read CSV and check if it has data
    try:
        df = pd.read_csv(csv_path)
        if len(df) == 0:
            print(f"No sample data for {table_name}")
            return True

        print(f"Loading {len(df)} rows into {table_display_name}...")

        # Use COPY command for efficiency
        copy_cmd = f"\\COPY \"{table_display_name}\" FROM '{csv_path}' WITH CSV HEADER"
        cmd = [f"{PG_BIN}/psql", "-d", DB_NAME, "-c", copy_cmd]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Warning loading data: {result.stderr}")
        else:
            print(f"Loaded data into {table_display_name}")

    except Exception as e:
        print(f"Error loading {table_name}: {e}")
        return False

    return True

def grant_permissions():
    """Grant permissions on all tables"""
    print("Granting permissions...")

    run_psql(f"GRANT CREATE ON SCHEMA public TO creator_role;", DB_NAME)
    run_psql(f"GRANT ALL ON ALL TABLES IN SCHEMA public TO creator_role;", DB_NAME)
    run_psql(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO select_user;", DB_NAME)

    print("Permissions granted.")

def main():
    print("=" * 60)
    print("Setting up Verdant PostgreSQL Database")
    print("=" * 60)

    # Create database
    create_database()

    # Create roles
    create_roles()

    # Create tables and load data
    for table_name in TABLES:
        create_table(table_name)
        load_sample_data(table_name)

    # Grant permissions
    grant_permissions()

    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print(f"\nDatabase: {DB_NAME}")
    print("Users: creator_role (password: creator_role), select_user (password: select_user)")
    print("\nTo connect: psql -d verdant_db_new -U creator_role")

if __name__ == "__main__":
    main()
