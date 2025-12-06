# Spider2-V Integration Analysis

## Executive Summary

This document analyzes the integration between the CT-Engine's DecomposeAgent architecture and the Spider2-V benchmark dataset. It provides a comprehensive understanding of how Verdant-style verbose instruction generation works and how to adapt it for Spider2-V multimodal data science workflows.

## Table of Contents

1. [Verdant Architecture Analysis](#1-verdant-architecture-analysis)
2. [Spider2-V Dataset Structure](#2-spider2v-dataset-structure)
3. [Integration Strategy](#3-integration-strategy)
4. [Implementation Plan](#4-implementation-plan)
5. [References](#5-references)

---

## 1. Verdant Architecture Analysis

### 1.1 Overview

Verdant is a module for SQL-based semantic parsing for financial database queries using PostgreSQL. It follows a **ReACT-style** (Reasoning + Acting) agent pattern with specialized actions for database interaction.

### 1.2 Verdant Actions

Verdant implements 6 core actions:

#### **FetchRelatedColumns**
- **Purpose**: Identify relevant database columns for a query
- **Input**: Query + optional column dictionary + background knowledge
- **Output**: Selected columns with descriptions and reasoning
- **LLM Usage**: Yes - analyzes task and selects relevant columns

#### **FetchBackgroundKnowledge**
- **Purpose**: Retrieve domain-specific background information
- **Input**: Natural language query
- **Output**: Background knowledge about the query domain
- **LLM Usage**: Yes - generates contextual information

#### **SketchSQL**
- **Purpose**: Create natural language sketch of SQL logic
- **Input**: Query + selected columns
- **Output**: Natural language description of SQL logic
- **LLM Usage**: Yes - converts query to logical steps

#### **GenerateSQL**
- **Purpose**: Generate actual SQL from natural language sketch
- **Input**: Natural language sketch + selected columns
- **Output**: Executable SQL query
- **LLM Usage**: Yes - converts sketch to SQL

#### **ExecuteSQL**
- **Purpose**: Execute SQL against database
- **Input**: SQL query
- **Output**: Query results as table
- **LLM Usage**: No - direct database execution

#### **GenerateAndExecuteSQL** (Combined)
- **Purpose**: Generate and execute SQL in one step
- **Input**: Natural language sketch + selected columns
- **Output**: Query results + generated SQL
- **LLM Usage**: Yes + DB execution

#### **Finish**
- **Purpose**: Format final answer from results
- **Input**: Original query + result table
- **Output**: Natural language answer
- **LLM Usage**: Yes - converts table to answer

### 1.3 Verdant Workflow Pattern

```
User Query
    ↓
FetchBackgroundKnowledge (predecided action)
    ↓
FetchRelatedColumns
    ↓
SketchSQL (optional)
    ↓
GenerateSQL
    ↓
ExecuteSQL
    ↓
Finish
```

### 1.4 Key Design Principles

1. **Action Modularity**: Each action is independent and composable
2. **LLM-Driven Reasoning**: Actions use LLM for intelligent decisions
3. **Predecided Actions**: Some actions (FetchBackgroundKnowledge) run automatically
4. **Schema-Based**: Actions follow ActionProtocol with get_input_schema()
5. **Caching**: Table descriptions cached for efficiency

### 1.5 VerboseInstructionGenerator Concept

While not explicitly implemented in Verdant, the **verbose instruction pattern** emerges from:
- SketchSQL generating step-by-step natural language logic
- FetchBackgroundKnowledge providing contextual information
- Each action contributing to a trace of reasoning steps

---

## 2. Spider2-V Dataset Structure

### 2.1 Overview

**Spider2-V** is a multimodal agent benchmark for automating data science and engineering workflows across 494 real-world tasks spanning 20 enterprise applications.

**Source**: [GitHub - xlang-ai/Spider2-V](https://github.com/xlang-ai/Spider2-V)
**Paper**: NeurIPS 2024

### 2.2 Dataset Categories

The dataset is organized by:

1. **Application Type** (20 total):
   - BigQuery, Snowflake, dbt, Dagster, Airflow
   - Airbyte, Superset, Metabase, ServiceNow
   - Jupyter, Excel, and more

2. **Instruction Type**:
   - **Verbose**: Step-by-step instructions embedded in task
   - **Abstract**: High-level goal only

3. **Account Requirement**:
   - Account-required tasks (real cloud services)
   - Non-account tasks (local/mock environments)

### 2.3 Task Format

Each task is a JSON file with:

```json
{
    "id": "unique-uuid",
    "snapshot": "environment-name (e.g., bigquery)",
    "instruction": "Task description with optional verbose steps",
    "source": ["reference URLs"],
    "action_number": 7,
    "config": [
        {"type": "setup_action", "parameters": {...}}
    ],
    "related_apps": ["bigquery", "chromium"],
    "tags": ["gui", "account", "data_warehousing", "verbose"],
    "evaluator": {
        "func": ["comparison_function"],
        "result": [{"type": "fetch_result", ...}],
        "expected": [{"type": "gold_standard", ...}]
    },
    "counterpart": "abstract-version-uuid"
}
```

### 2.4 Verbose Instruction Pattern

**Example from BigQuery task**:
```
"instruction": "Please add an empty column named RANK to the 2012 schema...
Here is a step-by-step tutorial from an expert instructing you how to complete it:
1. First, you need to view the project first, click toggle node...
2. Click the Toggle node of census dataset
3. Click 2012 Dataset
4. In the schema interface, click EDIT SCHEMA
5. In 'New fields' part, click '+'
6. Enter RANK in Field name
7. Click SAVE button
You can exactly follow the detailed plan above or proactively tackle the task..."
```

**Key Observation**: Verbose instructions are **already present** in the dataset, not generated dynamically.

### 2.5 Dataset Statistics

- **Total Tasks**: 494
- **Verbose Tasks**: ~247 (50%)
- **Abstract Tasks**: ~247 (50%)
- **Applications**: 20
- **BigQuery Tasks**: 20
- **Average Steps**: 7 actions per task

---

## 3. Integration Strategy

### 3.1 Core Insight

**Spider2-V does NOT need a VerboseInstructionGenerator** in the same way Verdant uses SketchSQL because:

1. **Verbose instructions already exist** in the dataset (test_verbose.json)
2. **Abstract instructions** are for testing agent's planning ability
3. The challenge is **executing** the instructions, not generating them

### 3.2 What Needs to be Built

Instead of generating verbose instructions, we need:

#### **Action Layer**:
Implement Spider2-V-specific actions similar to Verdant's pattern:

```
InspectSchema (✅ Already implemented)
GenerateSQL (✅ Already implemented)
ExecuteQuery (✅ Already implemented)
CreateFile (✅ Already implemented)
ClickButton (✅ Already implemented - mock)
Finish (✅ Already implemented)
```

**NEW ACTIONS NEEDED**:

```
OpenBrowser - Open and navigate to URLs
ClickElement - Click GUI elements by description/coordinates
TypeText - Type text into input fields
UploadFile - Upload files to web interfaces
Screenshot - Capture and analyze screenshots
WaitForElement - Wait for elements to appear
RunCommand - Execute shell commands
```

#### **Environment Integration**:
Connect to Spider2-V's desktop environment:

```python
from desktop_env.envs.desktop_env import DesktopEnv

env = DesktopEnv(action_space="pyautogui")
obs = env.reset(task_config=task_json)
obs, reward, done, info = env.step(action_string)
score = env.evaluate()
```

#### **Task Decomposition**:
Use DecomposeAgent to break down complex instructions:

- **For Verbose Instructions**: Parse steps and execute sequentially
- **For Abstract Instructions**: Use DecomposeAgent's recursive decomposition

### 3.3 Architectural Alignment

**Verdant Pattern** → **Spider2-V Adaptation**:

| Verdant Component | Spider2-V Equivalent |
|---|---|
| FetchRelatedColumns | InspectSchema (BigQuery tables) |
| FetchBackgroundKnowledge | Load task context from JSON |
| SketchSQL | Parse verbose instructions (if available) |
| GenerateSQL | GenerateSQL (for BigQuery tasks) |
| ExecuteSQL | ExecuteQuery (BigQuery API) |
| Generic Actions | GUI actions (ClickElement, TypeText, etc.) |
| DatabaseManager | DesktopEnv (VM environment) |

---

## 4. Implementation Plan

### 4.1 Phase 1: Core Actions for GUI Interaction (Priority 1)

Implement environment actions in `semantic_parser/modules/spider2v/env_actions.py`:

```python
class OpenBrowser(Action):
    """Navigate to URL in browser"""

class ClickElement(Action):
    """Click element by description or coordinates"""

class TypeText(Action):
    """Type text into input field"""

class UploadFile(Action):
    """Upload file to web form"""

class Screenshot(Action):
    """Capture and return screenshot"""

class WaitForElement(Action):
    """Wait for element to appear"""

class RunCommand(Action):
    """Execute shell command"""
```

### 4.2 Phase 2: Environment Integration

Create `semantic_parser/modules/spider2v/env_manager.py`:

```python
class Spider2VEnvironmentManager:
    """
    Manages interaction with Spider2-V desktop environment.

    Responsibilities:
    - Initialize DesktopEnv
    - Reset environment with task config
    - Execute actions via env.step()
    - Evaluate task completion
    - Capture observations (screenshots, a11y trees)
    """

    def __init__(self, vm_path: Optional[str] = None):
        self.env = DesktopEnv(action_space="pyautogui")

    def reset(self, task_config: Dict) -> Dict:
        """Reset environment with task configuration"""

    def execute_action(self, action_string: str) -> Tuple[Dict, float, bool, Dict]:
        """Execute action and return observation"""

    def evaluate(self) -> float:
        """Evaluate task completion"""
```

### 4.3 Phase 3: Verbose Instruction Parser (Optional)

For parsing embedded step-by-step instructions:

```python
class VerboseInstructionParser:
    """
    Parse verbose instructions from Spider2-V tasks.

    Extracts step-by-step instructions like:
    "1. Click toggle node..."
    "2. Click census dataset..."

    Returns structured subtasks for DecomposeAgent.
    """

    def parse(self, instruction: str) -> List[SubTask]:
        """Extract steps from verbose instruction"""
```

### 4.4 Phase 4: Task Loader Integration

Update `semantic_parser/modules/spider2v/task_loader.py`:

```python
class Spider2VTaskLoader:
    """Load tasks from official Spider2-V dataset"""

    def __init__(self, dataset_path: str = "../spider2v_dataset"):
        self.dataset_path = dataset_path

    def load_task_split(self, split: str = "test_verbose") -> List[Dict]:
        """
        Load tasks from specific split.

        Args:
            split: One of "test_verbose", "test_abstract", "test_all", etc.
        """

    def load_single_task(self, task_id: str) -> Dict:
        """Load specific task by ID"""
```

### 4.5 Phase 5: Testing & Evaluation

Create experiment script:

```python
# experiments/run_spider2v_real_experiment.py

from semantic_parser.modules.spider2v import create_action_registry
from semantic_parser.modules.spider2v.env_manager import Spider2VEnvironmentManager
from semantic_parser.modules.spider2v.task_loader import Spider2VTaskLoader
from semantic_parser.src.decompose import DecomposeAgent

# Load tasks
loader = Spider2VTaskLoader()
tasks = loader.load_task_split("test_verbose")

# Initialize environment
env_manager = Spider2VEnvironmentManager()

# Initialize agent
registry = create_action_registry()
agent = DecomposeAgent(llm_client, registry)

# Run experiment
for task in tasks:
    # Reset environment
    obs = env_manager.reset(task)

    # Solve with agent
    trace = await agent.solve(task["instruction"])

    # Evaluate
    score = env_manager.evaluate()
```

---

## 5. References

### Official Sources

- **Spider2-V GitHub**: https://github.com/xlang-ai/Spider2-V
- **Spider2-V Website**: https://spider2-v.github.io/
- **Spider2-V Paper**: https://arxiv.org/abs/2407.10956 (NeurIPS 2024)

### Related Work

- **OSWorld** (base environment): https://github.com/xlang-ai/OSWorld
- **Spider 2.0** (text-to-SQL): https://spider2-sql.github.io/

### Key Papers

1. **Spider2-V**: Cao et al., "Spider2-V: How Far Are Multimodal Agents From Automating Data Science and Engineering Workflows?", NeurIPS 2024
2. **OSWorld**: Xie et al., "OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments", arXiv 2024

---

## Conclusion

The integration of Spider2-V with CT-Engine's DecomposeAgent requires:

1. ✅ **Dataset Downloaded**: Official Spider2-V repository cloned
2. ✅ **Architecture Understood**: Verdant pattern analyzed
3. ⏳ **GUI Actions Needed**: Implement OpenBrowser, ClickElement, TypeText, etc.
4. ⏳ **Environment Integration**: Connect to DesktopEnv API
5. ⏳ **Testing**: Run on real Spider2-V tasks with VM environment

The key insight is that **verbose instructions already exist** in the dataset - our job is to **execute** them, not generate them. The DecomposeAgent's recursive decomposition will handle abstract instructions.
