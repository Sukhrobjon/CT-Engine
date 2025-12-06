#!/usr/bin/env python3
"""
Populate Spider2-V datasets with sample data

This script creates tables in the 7 datasets that Spider2-V tasks expect.
Tables are populated with minimal sample data for testing.
"""

from google.cloud import bigquery
from google.oauth2 import service_account
import os

# Setup credentials
SERVICE_ACCOUNT_PATH = "/Users/sukhrobjongolibboev/Desktop/Stanford/CS224VFall2025/final project/CT-Engine/spider-471218-77fec1ca4fcf.json"
PROJECT_ID = "cs224v-recursive-parsing"

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_PATH,
    scopes=["https://www.googleapis.com/auth/bigquery"],
)

client = bigquery.Client(credentials=credentials, project=PROJECT_ID)

print("=" * 60)
print("SPIDER2-V DATASET POPULATION")
print("=" * 60)
print(f"\nProject: {PROJECT_ID}")
print(f"Using service account: {SERVICE_ACCOUNT_PATH}\n")

# Step 1: Create datasets first
print("Step 1: Creating datasets...")
DATASET_IDS = ["babynames", "census", "customer_orders", "information", "ml_project", "my_dataset", "my_google_ads"]

for dataset_id in DATASET_IDS:
    dataset_full_id = f"{PROJECT_ID}.{dataset_id}"
    dataset = bigquery.Dataset(dataset_full_id)
    dataset.location = "US"

    try:
        dataset = client.create_dataset(dataset, exists_ok=True, timeout=30)
        print(f"  ✅ Created dataset: {dataset_id}")
    except Exception as e:
        print(f"  ❌ Error creating {dataset_id}: {str(e)}")

print(f"\nStep 2: Creating tables and populating data...\n")

# Define datasets and tables to create
DATASETS_TABLES = {
    "babynames": [
        {
            "table_id": "names_2014",
            "schema": [
                bigquery.SchemaField("name", "STRING"),
                bigquery.SchemaField("gender", "STRING"),
                bigquery.SchemaField("count", "INTEGER"),
            ],
            "data": [
                {"name": "Emma", "gender": "F", "count": 20799},
                {"name": "Olivia", "gender": "F", "count": 19674},
                {"name": "Noah", "gender": "M", "count": 19144},
                {"name": "Liam", "gender": "M", "count": 18138},
            ]
        }
    ],
    "census": [
        {
            "table_id": "2012",
            "schema": [
                bigquery.SchemaField("state", "STRING"),
                bigquery.SchemaField("population", "INTEGER"),
                bigquery.SchemaField("year", "INTEGER"),
            ],
            "data": [
                {"state": "California", "population": 38041430, "year": 2012},
                {"state": "Texas", "population": 26059203, "year": 2012},
                {"state": "New York", "population": 19570261, "year": 2012},
            ]
        },
        {
            "table_id": "gdp",
            "schema": [
                bigquery.SchemaField("country", "STRING"),
                bigquery.SchemaField("gdp", "FLOAT"),
                bigquery.SchemaField("year", "INTEGER"),
            ],
            "data": [
                {"country": "United States", "gdp": 16197.0, "year": 2012},
                {"country": "China", "gdp": 8560.0, "year": 2012},
            ]
        }
    ],
    "customer_orders": [
        {
            "table_id": "orders",
            "schema": [
                bigquery.SchemaField("order_id", "INTEGER"),
                bigquery.SchemaField("customer_name", "STRING"),
                bigquery.SchemaField("order_amount", "FLOAT"),
            ],
            "data": [
                {"order_id": 1, "customer_name": "John Doe", "order_amount": 100.50},
                {"order_id": 2, "customer_name": "Jane Smith", "order_amount": 250.75},
            ]
        }
    ],
    "information": [
        {
            "table_id": "history",
            "schema": [
                bigquery.SchemaField("customer_name", "STRING"),
                bigquery.SchemaField("order_date", "STRING"),
                bigquery.SchemaField("order_amount", "INTEGER"),
            ],
            "data": [
                {"customer_name": "Alice", "order_date": "2024-01-15", "order_amount": 100},
                {"customer_name": "Bob", "order_date": "2024-01-16", "order_amount": 200},
            ]
        }
    ],
    "ml_project": [
        {
            "table_id": "information",
            "schema": [
                bigquery.SchemaField("feature1", "FLOAT"),
                bigquery.SchemaField("feature2", "FLOAT"),
                bigquery.SchemaField("label", "INTEGER"),
            ],
            "data": [
                {"feature1": 1.5, "feature2": 2.3, "label": 1},
                {"feature1": 0.8, "feature2": 1.2, "label": 0},
            ]
        }
    ],
    "my_dataset": [
        {
            "table_id": "information",
            "schema": [
                bigquery.SchemaField("id", "INTEGER"),
                bigquery.SchemaField("name", "STRING"),
                bigquery.SchemaField("value", "FLOAT"),
            ],
            "data": [
                {"id": 1, "name": "test1", "value": 42.0},
                {"id": 2, "name": "test2", "value": 100.0},
            ]
        }
    ],
    "my_google_ads": [
        {
            "table_id": "ad_stats_data",
            "schema": [
                bigquery.SchemaField("ad_id", "STRING"),
                bigquery.SchemaField("impressions", "INTEGER"),
                bigquery.SchemaField("clicks", "INTEGER"),
            ],
            "data": [
                {"ad_id": "ad_001", "impressions": 1000, "clicks": 50},
                {"ad_id": "ad_002", "impressions": 2000, "clicks": 100},
            ]
        }
    ]
}

# Create tables with data
total_tables = sum(len(tables) for tables in DATASETS_TABLES.values())
current = 0

for dataset_id, tables in DATASETS_TABLES.items():
    for table_info in tables:
        current += 1
        table_id = table_info["table_id"]
        full_table_id = f"{PROJECT_ID}.{dataset_id}.{table_id}"

        print(f"[{current}/{total_tables}] Creating {dataset_id}.{table_id}...", end=" ")

        try:
            # Create table
            table = bigquery.Table(full_table_id, schema=table_info["schema"])
            table = client.create_table(table, exists_ok=True)

            # Insert sample data
            errors = client.insert_rows_json(table, table_info["data"])

            if errors:
                print(f"⚠️  Created but errors inserting data: {errors}")
            else:
                row_count = len(table_info["data"])
                print(f"✅ Created with {row_count} sample rows")

        except Exception as e:
            print(f"❌ Error: {str(e)}")

print("\n" + "=" * 60)
print("✅ DATASET POPULATION COMPLETE")
print("=" * 60)
print(f"\nCreated {total_tables} tables across 7 datasets")
print("\nVerify with:")
print(f"  python3 -c \"from google.cloud import bigquery; client = bigquery.Client(); print([d.dataset_id for d in client.list_datasets()])\"")
