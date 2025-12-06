#!/bin/bash
#
# Setup Spider2-V BigQuery Datasets
#
# This script creates the 7 datasets that Spider2-V tasks expect.
# Run this once to prepare your GCP project for Spider2-V-style tasks.
#

set -e  # Exit on error

PROJECT="cs224v-recursive-parsing"

echo "============================================================"
echo "SPIDER2-V BIGQUERY DATASET SETUP"
echo "============================================================"
echo ""
echo "This will create 7 datasets in project: $PROJECT"
echo ""

# Create datasets
echo "[1/7] Creating babynames dataset..."
bq mk --dataset $PROJECT:babynames 2>/dev/null || echo "  ✓ Dataset already exists"

echo "[2/7] Creating census dataset..."
bq mk --dataset $PROJECT:census 2>/dev/null || echo "  ✓ Dataset already exists"

echo "[3/7] Creating customer_orders dataset..."
bq mk --dataset $PROJECT:customer_orders 2>/dev/null || echo "  ✓ Dataset already exists"

echo "[4/7] Creating information dataset..."
bq mk --dataset $PROJECT:information 2>/dev/null || echo "  ✓ Dataset already exists"

echo "[5/7] Creating ml_project dataset..."
bq mk --dataset $PROJECT:ml_project 2>/dev/null || echo "  ✓ Dataset already exists"

echo "[6/7] Creating my_dataset dataset..."
bq mk --dataset $PROJECT:my_dataset 2>/dev/null || echo "  ✓ Dataset already exists"

echo "[7/7] Creating my_google_ads dataset..."
bq mk --dataset $PROJECT:my_google_ads 2>/dev/null || echo "  ✓ Dataset already exists"

echo ""
echo "============================================================"
echo "✅ SETUP COMPLETE"
echo "============================================================"
echo ""
echo "Created datasets:"
echo "  • babynames"
echo "  • census"
echo "  • customer_orders"
echo "  • information"
echo "  • ml_project"
echo "  • my_dataset"
echo "  • my_google_ads"
echo ""
echo "Verify with: bq ls --project_id=$PROJECT"
echo ""
