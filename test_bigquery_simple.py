#!/usr/bin/env python3
"""Simple test of BigQuery connectivity without full framework imports"""

import os
import json
from google.cloud import bigquery
from google.oauth2 import service_account

print("\n" + "="*60)
print("TESTING BIGQUERY CONNECTIVITY")
print("="*60)

# Configuration
service_account_path = "/Users/sukhrobjongolibboev/Desktop/Stanford/CS224VFall2025/final project/CT-Engine/spider-471218-77fec1ca4fcf.json"
project_id = "cs224v-recursive-parsing"

print(f"\n[1/2] Initializing BigQuery client...")
print(f"  Service Account: {service_account_path}")
print(f"  Project: {project_id}")

try:
    credentials = service_account.Credentials.from_service_account_file(service_account_path)
    client = bigquery.Client(credentials=credentials, project=project_id)
    print(f"  ✓ Client initialized successfully")
except Exception as e:
    print(f"  ❌ Failed to initialize client: {e}")
    exit(1)

print(f"\n[2/2] Testing with public dataset...")
dataset_name = "bigquery-public-data.covid19_open_data"
print(f"  Dataset: {dataset_name}")

try:
    # Parse dataset reference
    project, dataset_id = dataset_name.split('.')
    dataset_ref = f"{project}.{dataset_id}"

    # Get dataset
    dataset = client.get_dataset(dataset_ref)
    print(f"  ✓ Dataset found: {dataset.dataset_id}")

    # List tables
    tables = list(client.list_tables(dataset))
    print(f"  ✓ Tables found: {len(tables)}")

    # Get schema for first table
    if tables:
        table_ref = dataset.table(tables[0].table_id)
        table = client.get_table(table_ref)
        print(f"  ✓ Sample table: {table.table_id}")
        print(f"  ✓ Rows: {table.num_rows:,}")
        print(f"  ✓ Columns: {len(table.schema)}")

        print(f"\n  First 5 columns:")
        for field in table.schema[:5]:
            print(f"    - {field.name} ({field.field_type})")

    print(f"\n✅ BigQuery connection successful!")

except Exception as e:
    print(f"\n❌ BigQuery test failed: {e}")
    exit(1)

print("\n" + "="*60)
print("TEST COMPLETE - BigQuery is working!")
print("="*60 + "\n")
