# Spider2-V Failure Analysis - Phase 2: Prompt Improvements Results

**Date**: 2025-11-28
**Experiment**: pilot_test_improved, pilot_test_v3
**Previous Success Rate**: 60% (pilot_test_final)
**Current Success Rate**: 60% (3/5 tasks)
**Status**: Prompt improvements partially successful, new issues identified

---

## Executive Summary

The prompt improvements for InspectSchema and GenerateSQL **partially worked** but revealed deeper architectural issues:

1. **InspectSchema**: Still extracts wrong dataset names (changed from "to" to "schema")
2. **GenerateSQL**: Fixed placeholder issue BUT created regression (missing FROM clause)
3. **Root Cause**: **Context preservation problem** - subtask descriptions don't include parent task details

---

## Detailed Failure Analysis

### Test Results Comparison

| Test ID | Previous Error (pilot_test_final) | New Error (pilot_test_v3) | Status |
|---------|-----------------------------------|---------------------------|--------|
| test_001 | ✅ Success | ✅ Success | Unchanged |
| test_002 | ✅ Success | ✅ Success | Unchanged |
| test_003 | Dataset "to" not found | Dataset "schema" not found | Changed (still failing) |
| test_004 | Placeholder SQL "your_table_name" | No FROM clause in SQL | Regression |
| test_005 | ✅ Success | ✅ Success | Unchanged |

**Success Rate**: 60% → 60% (no improvement, but different failure modes)

---

## Failure 1: test_003 - InspectSchema Still Extracting Wrong Dataset

### Task
```
"Create a dbt model file named 'customer_metrics.sql' that calculates customer lifetime value"
```

### Decomposition (LLM-generated)
```
Subtask 1: "Inspect the BigQuery dataset schema to identify relevant tables and columns for calculating customer lifetime value"
Subtask 2: "Generate SQL query to calculate customer lifetime value using identified tables"
Subtask 3: "Create the dbt model file 'customer_metrics.sql' with the generated SQL"
```

### Error
```
BigQuery error: 404 Not found: Dataset cs224v-recursive-parsing:schema
```

### Root Cause Analysis

**Before (pilot_test_final)**: InspectSchema extracted "to" from "customer **to**" in "customer lifetime value"

**After (pilot_test_v3)**: InspectSchema extracted "schema" from "Inspect the BigQuery dataset **schema**"

#### Why This Happened

1. **DecomposeAgent created a subtask mentioning "schema"** in the description
2. InspectSchema LLM extraction saw "schema" and extracted it as the dataset name
3. The improved prompt DID avoid extracting from unrelated words like "customer to", but it still extracts from metadata words like "schema"

#### The Real Issue: Unnecessary Decomposition

**This task should NOT be decomposed!**

- Task: "Create a dbt model file" → Should just use **CreateFile** action
- No need to inspect BigQuery schema (this is dbt code, not a database query)
- The DecomposeAgent incorrectly judged this as COMPLEX

### Proposed Fix

**Option 1**: Improve complexity judgment to recognize file creation tasks as SIMPLE

Add to `decompose_agent.py` complexity judgment:
```python
# File creation tasks are always SIMPLE
if any(keyword in task_lower for keyword in ["create file", "create a file", "dbt model file"]):
    return SimpleTaskJudgment(
        complexity_judgment="SIMPLE",
        reasoning="File creation tasks don't need decomposition, use CreateFile directly"
    )
```

**Option 2**: Further improve InspectSchema prompt to reject metadata words

Add to InspectSchema LLM prompt:
```
- DO NOT extract metadata words like "schema", "table", "dataset", "column" unless they are ACTUAL dataset names
- "inspect the schema" → NONE (schema is a metadata word)
- "inspect the my_dataset schema" → "my_dataset" (actual dataset name)
```

**Recommendation**: Use **both** fixes - Option 1 prevents unnecessary decomposition, Option 2 handles edge cases

---

## Failure 2: test_004 - GenerateSQL Missing FROM Clause (REGRESSION)

### Task
```
"Execute a query to count total rows in bigquery-public-data.austin_bikeshare.bikeshare_stations"
```

### Decomposition (LLM-generated)
```
Subtask 1: "Generate SQL to count total rows in the specified BigQuery table"
Subtask 2: "Execute the generated SQL query and return the row count"
```

### Generated SQL (pilot_test_v3)
```sql
SELECT COUNT(*)
```

### Error
```
400 Aggregate function COUNT(*) not allowed in SELECT without FROM clause at [1:8]
```

### Root Cause Analysis

**Before (pilot_test_final)**: GenerateSQL generated placeholder `SELECT COUNT(*) FROM your_table_name`

**After (pilot_test_v3)**: GenerateSQL generated `SELECT COUNT(*)` (no FROM clause at all)

#### Why This Happened: Context Loss

1. **Parent task** mentions: `bigquery-public-data.austin_bikeshare.bikeshare_stations`
2. **Subtask 1** description: "Generate SQL to count total rows in the **specified BigQuery table**"
3. **GenerateSQL** receives only subtask description, which says "specified table" but doesn't include the actual table name
4. Improved prompt forbids placeholders, so LLM can't use "your_table_name"
5. Result: LLM generates `SELECT COUNT(*)` without FROM clause

#### The Real Issue: Context Preservation

**Subtasks don't inherit parent task details!**

The DecomposeAgent creates subtask descriptions that reference information from the parent task ("specified BigQuery table") but don't include the actual data (table name).

### Proposed Fix

**Option 1**: Enhance subtask descriptions to include specific details

Modify decomposition prompt in `decompose_agent.py`:
```
When creating subtask descriptions:
- Include ALL specific details from parent task (table names, dataset names, file names, etc.)
- Don't use vague references like "specified table" or "the dataset" - use actual names
- Example: Instead of "Generate SQL for the specified table", use "Generate SQL for bigquery-public-data.austin_bikeshare.bikeshare_stations"
```

**Option 2**: Pass parent task as context to all actions

Modify action execution to include parent task:
```python
# In decompose_agent.py
action_output = action.execute(
    query=subtask.description,
    parent_task=self.current_task  # NEW: Pass parent task for context
)
```

Then modify GenerateSQL to fall back to parent task if needed:
```python
def execute(self, query: str, parent_task: Optional[str] = None, ...):
    # Try to extract table from query first
    # If not found, try parent_task
    # If still not found, return error
```

**Recommendation**: Use **Option 1** (enhance subtask descriptions) - simpler and more transparent

---

## Success: test_004 Decomposition Quality

Despite the failure, test_004 showed **excellent decomposition**:

```
Subtask 1: Generate SQL
Subtask 2: Execute SQL
```

This is correct! The override logic properly detected:
```
⚠ Override: Task needs SQL generation before execution (no SQL in context)
  Forcing decomposition instead of simple execution
```

The decomposition itself is good, just the context preservation needs work.

---

## Action Items (Priority Order)

### High Priority (Blocking 80% success)

1. **Fix Context Preservation** - Enhance subtask descriptions to include specific details from parent task
   - File: `semantic_parser/src/decompose/decompose_agent.py`
   - Location: Decomposition LLM prompt
   - Estimated Impact: +20% success rate (fixes test_004)

2. **Fix Complexity Judgment for File Creation** - Recognize "create file" tasks as SIMPLE
   - File: `semantic_parser/src/decompose/decompose_agent.py`
   - Location: Complexity judgment logic
   - Estimated Impact: +20% success rate (fixes test_003)

### Medium Priority (Quality improvements)

3. **Enhance InspectSchema Metadata Detection** - Reject metadata words like "schema", "table", etc.
   - File: `semantic_parser/modules/spider2v/actions.py`
   - Location: `InspectSchema._extract_dataset_with_llm()`
   - Estimated Impact: Edge case protection

4. **Add Validation to GenerateSQL** - Detect missing FROM clause
   - File: `semantic_parser/modules/spider2v/actions.py`
   - Location: `GenerateSQL.execute()`
   - Estimated Impact: Better error messages

---

## Lessons Learned

### What Worked ✅

1. **Placeholder detection** - GenerateSQL no longer uses "your_table_name"
2. **InspectSchema improvements** - Changed behavior (no longer extracts "to")
3. **Decomposition quality** - test_004 decomposition was excellent
4. **Override logic** - Correctly detected when SQL generation needed

### What Didn't Work ❌

1. **Prompt-only fixes insufficient** - Deeper architectural issues exist
2. **Context preservation missing** - Subtasks don't have access to parent task details
3. **Complexity judgment too aggressive** - Decomposes simple tasks unnecessarily
4. **LLM extraction still fragile** - Extracts metadata words like "schema"

### Key Insight 💡

**Prompt engineering alone cannot solve context preservation issues.**

The architecture needs to:
- Pass parent task context to subtasks
- OR enhance subtask descriptions to be self-contained
- OR avoid unnecessary decomposition in the first place

---

## Next Experiment Plan

### Phase 3: Fix Architecture Issues

**Target**: 80%+ success rate on 5 tasks, then scale to 10

#### Step 1: Fix Context Preservation (30 min)
Enhance decomposition prompt to include specific details in subtask descriptions.

#### Step 2: Fix Complexity Judgment (15 min)
Add rules for file creation tasks to be judged as SIMPLE.

#### Step 3: Re-run Pilot Test (10 min)
```bash
python3 experiments/run_spider2v_experiment.py 5 pilot_test_phase3
```
**Target**: 80-100% success (4-5 tasks passing)

#### Step 4: If Successful, Scale to 10 Real Tasks (30 min)
```bash
python3 experiments/run_spider2v_experiment.py 10 bigquery_verbose_real
```
**Target**: 70-80% success on real Spider2-V tasks

---

## Metrics Comparison

| Metric | pilot_test_final | pilot_test_v3 | Change |
|--------|------------------|---------------|--------|
| Success Rate | 60% | 60% | No change |
| Avg Duration | 11.8s | 17.5s | +48% (slower) |
| Action Usage | 6 | 6 | Same |
| Error Types | 2 | 2 | Same (different errors) |

**Conclusion**: Prompt improvements changed failure modes but didn't improve success rate. Need architectural fixes.

---

**Last Updated**: 2025-11-28
**Next Steps**: Implement context preservation and complexity judgment fixes
