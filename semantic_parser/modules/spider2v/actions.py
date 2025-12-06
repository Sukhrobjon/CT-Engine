"""Spider2-V Action Implementations

This module implements the core actions for the Spider2-V benchmark tasks.
Actions support BigQuery integration for multimodal data science workflows.
"""

import os
import json
from typing import Dict, Any, Optional, Union
from google.cloud import bigquery
import pandas as pd

from semantic_parser.action_protocol import Action, ActionOutput


class InspectSchema(Action):
    """Inspect BigQuery dataset schema to understand available tables and columns"""

    def __init__(self, llm_client, bigquery_client: Optional[bigquery.Client] = None):
        super().__init__(
            name="InspectSchema",
            description="Inspect BigQuery dataset schema to understand available tables and columns. Use this when you need to explore database structure."
        )
        self.client = llm_client
        self.bq_client = bigquery_client or bigquery.Client()

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "dataset_name": {
                    "type": "string",
                    "description": "Name of the BigQuery dataset to inspect (format: project.dataset or dataset)"
                }
            },
            "required": ["dataset_name"]
        }

    def _extract_dataset_with_llm(self, query: str) -> Optional[str]:
        """Use LLM to extract dataset name when regex fails"""
        prompt = f"""Analyze this task and extract the BigQuery dataset name ONLY if the task involves inspecting, querying, or working with a BigQuery dataset.

Task: {query}

IMPORTANT:
- If the task is about CREATING A FILE or GENERATING CODE, return "NONE" (not a dataset inspection task)
- If the task mentions a specific dataset like "bigquery-public-data.covid19_open_data", extract it
- If the task is vague or doesn't mention a dataset, return "NONE"
- DO NOT extract random words from the task description

Return ONLY ONE of:
- "project.dataset" (e.g., "bigquery-public-data.covid19_open_data")
- "dataset" (e.g., "my_dataset")
- "NONE" (if task doesn't involve inspecting a dataset)

Examples:
- "Inspect the bigquery-public-data.covid19_open_data dataset" → "bigquery-public-data.covid19_open_data"
- "Create a dbt model file that calculates metrics" → "NONE"
- "Generate SQL to query the ecommerce dataset" → "ecommerce"

Dataset name:"""

        from semantic_parser.llm_client import Message
        try:
            response = self.client.chat_completion([Message(role="user", content=prompt)])
            dataset_name = response.content.strip()
            # Remove quotes if LLM wrapped the response
            dataset_name = dataset_name.strip('"\'')
            return None if dataset_name.upper() == "NONE" else dataset_name
        except Exception as e:
            print(f"LLM extraction failed: {str(e)}")
            return None

    def execute(self, query: str, dataset_name: Optional[str] = None) -> ActionOutput:
        try:
            # Use dataset_name if provided, otherwise try to extract from query
            if not dataset_name:
                # Try to extract dataset name from query
                # Look for patterns like "bigquery-public-data.covid19_open_data"
                import re
                # First try to find dataset with project prefix (pattern: project.dataset)
                match = re.search(r'([a-z0-9_-]+\.[a-z0-9_-]+)', query, re.IGNORECASE)
                if match:
                    dataset_name = match.group(1)
                else:
                    # If no project.dataset pattern, look for dataset keyword
                    match = re.search(r'dataset[:\s]+([a-z0-9_-]+)', query, re.IGNORECASE)
                    if match:
                        dataset_name = match.group(1)

                # If regex extraction failed, try LLM fallback
                if not dataset_name:
                    dataset_name = self._extract_dataset_with_llm(query)

                # If both methods failed, raise error
                if not dataset_name:
                    raise ValueError("Could not extract dataset name from query. Please provide dataset_name parameter.")

            # Parse dataset reference
            if '.' in dataset_name:
                project_id, dataset_id = dataset_name.split('.', 1)
            else:
                project_id = self.bq_client.project
                dataset_id = dataset_name

            # Get dataset
            dataset_ref = f"{project_id}.{dataset_id}"
            dataset = self.bq_client.get_dataset(dataset_ref)

            # List tables
            tables = list(self.bq_client.list_tables(dataset))

            schema_info = {
                "dataset": dataset_id,
                "project": project_id,
                "tables": []
            }

            # Get schema for each table
            for table_item in tables:
                table_ref = dataset.table(table_item.table_id)
                table = self.bq_client.get_table(table_ref)

                table_schema = {
                    "table_name": table.table_id,
                    "num_rows": table.num_rows,
                    "columns": [
                        {
                            "name": field.name,
                            "type": field.field_type,
                            "mode": field.mode,
                            "description": field.description or ""
                        }
                        for field in table.schema
                    ]
                }
                schema_info["tables"].append(table_schema)

            return ActionOutput(
                success=True,
                result=json.dumps(schema_info, indent=2),
                metadata={
                    "dataset_name": dataset_ref,
                    "table_count": len(tables),
                    "total_columns": sum(len(t["columns"]) for t in schema_info["tables"])
                }
            )

        except Exception as e:
            return ActionOutput(
                success=False,
                result=None,
                error=f"BigQuery error: {str(e)}"
            )


class GenerateSQL(Action):
    """Generate SQL query from natural language description"""

    def __init__(self, llm_client):
        super().__init__(
            name="GenerateSQL",
            description="Generate SQL query from natural language description. Use this when you need to create a SQL query based on requirements."
        )
        self.client = llm_client

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query_description": {
                    "type": "string",
                    "description": "Natural language description of the query"
                },
                "schema": {
                    "type": "string",
                    "description": "Optional JSON string of database schema"
                }
            },
            "required": ["query_description"]
        }

    def execute(self, query: str, query_description: Optional[str] = None, schema: Optional[str] = None) -> ActionOutput:
        try:
            # Use query_description if provided, otherwise use query
            description = query_description if query_description else query

            # Enhanced system prompt
            system_prompt = """You are a SQL expert. Generate ONLY the SQL query with NO explanations.

CRITICAL RULES:
1. Extract table names EXACTLY as mentioned in the task (e.g., "bigquery-public-data.austin_bikeshare.bikeshare_stations")
2. NEVER use placeholders like "your_table_name", "table_name", "dataset.table", or "your_dataset"
3. If a fully qualified table name is in the task, use it EXACTLY
4. If the task mentions specific columns, datasets, or tables, use them precisely
5. Use backticks for table names in BigQuery: `project.dataset.table`
6. Return ONLY the SQL query, no markdown code blocks, no explanations

Examples:
Task: "count rows in bigquery-public-data.covid19_open_data.covid19_open_data"
SQL: SELECT COUNT(*) FROM `bigquery-public-data.covid19_open_data.covid19_open_data`

Task: "find total cases in austin_bikeshare.bikeshare_stations"
SQL: SELECT COUNT(*) FROM `austin_bikeshare.bikeshare_stations`"""

            # Build user prompt with schema context
            user_prompt = f"""Task: {description}"""
            if schema:
                user_prompt = f"""Available Schema:
{schema}

{user_prompt}"""

            user_prompt += "\n\nGenerate the SQL query for this task. Remember: NO placeholders, use EXACT table names from the task."

            from semantic_parser.llm_client import Message
            messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=user_prompt)
            ]

            response = self.client.chat_completion(messages)
            sql = response.content.strip()

            # Clean SQL (remove markdown formatting)
            sql = sql.replace("```sql", "").replace("```", "").strip()

            # Validate no placeholders
            if "your_table" in sql.lower() or "table_name" in sql.lower() or "your_dataset" in sql.lower():
                return ActionOutput(
                    success=False,
                    result=None,
                    error=f"Generated SQL contains placeholder: {sql}. Could not extract actual table name from task."
                )

            return ActionOutput(
                success=True,
                result=sql,
                metadata={"query_length": len(sql), "has_schema": schema is not None}
            )
        except Exception as e:
            return ActionOutput(
                success=False,
                result=None,
                error=f"SQL generation error: {str(e)}"
            )


class ExecuteQuery(Action):
    """Execute SQL query against BigQuery database"""

    def __init__(self, bigquery_client: Optional[bigquery.Client] = None, llm_client=None):
        super().__init__(
            name="ExecuteQuery",
            description="Execute SQL query against BigQuery database and return results. Use this to run queries and get data."
        )
        self.bq_client = bigquery_client or bigquery.Client()
        self.client = llm_client

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "SQL query to execute"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 1000)",
                    "default": 1000
                }
            },
            "required": ["sql"]
        }

    def _is_valid_sql(self, text: str) -> bool:
        """Quick heuristic check if text looks like SQL"""
        text_upper = text.upper().strip()

        # Common SQL keywords that should start a query
        sql_starters = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'WITH']

        # Check if starts with SQL keyword
        starts_with_sql = any(text_upper.startswith(keyword) for keyword in sql_starters)

        # Natural language indicators
        natural_language_patterns = [
            'EXECUTE A QUERY',
            'RUN A QUERY',
            'COUNT THE',
            'FIND THE',
            'GET THE',
            'SHOW ME',
            'LIST ALL',
        ]
        has_natural_language = any(pattern in text_upper for pattern in natural_language_patterns)

        # If it has natural language patterns, it's likely not SQL
        if has_natural_language:
            return False

        # If it starts with SQL keyword and no natural language, likely valid
        return starts_with_sql

    def _validate_sql_with_llm(self, text: str) -> Dict[str, Any]:
        """Use LLM to validate if text is actual SQL or natural language"""
        if not self.client:
            # If no LLM client, use heuristic only
            return {"is_sql": self._is_valid_sql(text), "reason": "No LLM client available"}

        prompt = f"""Is the following text a valid SQL query or natural language?

Text: {text}

Respond with a JSON object with these fields:
- is_sql: boolean (true if it's actual SQL, false if it's natural language)
- reason: string (brief explanation)
- suggestion: string (if not SQL, suggest what action to use)

Example responses:
{{"is_sql": true, "reason": "Valid SELECT statement", "suggestion": ""}}
{{"is_sql": false, "reason": "Natural language query description", "suggestion": "Use GenerateSQL action first to convert this to SQL"}}

Response:"""

        from semantic_parser.llm_client import Message
        try:
            response = self.client.chat_completion([Message(role="user", content=prompt)])
            # Try to parse JSON response
            import json
            result = json.loads(response.content.strip())
            return result
        except Exception as e:
            # Fallback to heuristic if LLM fails
            return {"is_sql": self._is_valid_sql(text), "reason": f"LLM validation failed: {str(e)}"}

    def execute(self, query: str, sql: Optional[str] = None, max_results: int = 1000) -> ActionOutput:
        try:
            # Use sql if provided, otherwise assume query contains the SQL
            sql_to_execute = sql if sql else query

            # Validate that input is actually SQL, not natural language
            if not self._is_valid_sql(sql_to_execute):
                # Use LLM for more thorough validation
                validation = self._validate_sql_with_llm(sql_to_execute)

                if not validation.get("is_sql", False):
                    error_msg = f"Invalid input: The provided text appears to be natural language, not SQL.\n"
                    error_msg += f"Reason: {validation.get('reason', 'Not a valid SQL query')}\n"
                    if validation.get('suggestion'):
                        error_msg += f"Suggestion: {validation['suggestion']}\n"
                    else:
                        error_msg += "Suggestion: Use the GenerateSQL action first to convert your query to SQL, then pass the result to ExecuteQuery."

                    return ActionOutput(
                        success=False,
                        result=None,
                        error=error_msg
                    )

            # Execute query
            query_job = self.bq_client.query(sql_to_execute)

            # Get results as DataFrame
            df = query_job.to_dataframe(max_results=max_results)

            # Convert to markdown table for display
            result_str = df.to_markdown(index=False)

            return ActionOutput(
                success=True,
                result=df,  # Return actual dataframe for type safety
                metadata={
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "total_bytes_processed": query_job.total_bytes_processed,
                    "job_id": query_job.job_id,
                    "markdown_table": result_str  # Store markdown in metadata for display
                }
            )

        except Exception as e:
            return ActionOutput(
                success=False,
                result=None,
                error=f"Query execution error: {str(e)}"
            )


class CreateFile(Action):
    """Create a file with specified content"""

    def __init__(self, output_dir: str = "/tmp/spider2v_output"):
        super().__init__(
            name="CreateFile",
            description="Create a file with specified content. Use this for creating dbt models, configs, or any file needed for the task."
        )
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name of the file to create"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["filename", "content"]
        }

    def execute(self, query: str, filename: Optional[str] = None, content: Optional[str] = None) -> ActionOutput:
        # Extract filename from query if not provided
        if not filename:
            filename = self._extract_filename_from_query(query)
            if not filename:
                return ActionOutput(
                    success=False,
                    result=None,
                    error=f"Could not determine filename from task: '{query}'. Please specify filename explicitly."
                )

        # Generate default content if not provided
        if not content:
            content = f"-- File created for: {query}\n-- TODO: Add implementation\n"

        file_path = os.path.join(self.output_dir, filename)

        try:
            with open(file_path, 'w') as f:
                f.write(content)

            return ActionOutput(
                success=True,
                result=file_path,
                metadata={"file_path": file_path, "size_bytes": len(content)}
            )
        except Exception as e:
            return ActionOutput(
                success=False,
                result=None,
                error=str(e)
            )

    def _extract_filename_from_query(self, query: str) -> Optional[str]:
        """Extract filename from query using regex patterns."""
        import re

        # Pattern 1: "file named 'filename'" or "file called 'filename'"
        match = re.search(r"(?:file|model)\s+(?:named|called)\s+['\"]([^'\"]+)['\"]", query, re.IGNORECASE)
        if match:
            return match.group(1)

        # Pattern 2: "create filename.ext" or "make filename.ext"
        match = re.search(r"(?:create|make|generate)\s+([\w_-]+\.(?:sql|py|txt|csv|json|yaml|yml|md|sh))", query, re.IGNORECASE)
        if match:
            return match.group(1)

        # Pattern 3: Any quoted filename with extension
        match = re.search(r"['\"]?([\w_-]+\.(?:sql|py|txt|csv|json|yaml|yml|md|sh))['\"]?", query)
        if match:
            return match.group(1)

        # Pattern 4: "dbt model file named X" - dbt models are .sql
        match = re.search(r"dbt\s+model\s+(?:file\s+)?(?:named|called)\s+['\"]?(\w+)['\"]?", query, re.IGNORECASE)
        if match:
            name = match.group(1)
            # Add .sql extension if not present
            if not name.endswith('.sql'):
                name += '.sql'
            return name

        return None


class ClickButton(Action):
    """Simulate clicking a button in a GUI"""

    def __init__(self):
        super().__init__(
            name="ClickButton",
            description="Simulate clicking a button in a GUI. Use this for UI interactions like clicking 'Run Query' or 'Save Results'."
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "button_description": {
                    "type": "string",
                    "description": "Description of the button to click"
                }
            },
            "required": ["button_description"]
        }

    def execute(self, query: str, button_description: Optional[str] = None) -> ActionOutput:
        # Use button_description if provided, otherwise use query
        description = button_description if button_description else query

        # Mock implementation - just log the action
        return ActionOutput(
            success=True,
            result=f"Clicked button: {description}",
            metadata={"simulated": True, "button": description}
        )


class SaveToCSV(Action):
    """Save DataFrame or query results to CSV file"""

    def __init__(self, output_dir: str = "/tmp/spider2v_output"):
        super().__init__(
            name="SaveToCSV",
            description="Save DataFrame or query results to a CSV file. Use this to export data to CSV format."
        )
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "string",
                    "description": "Data to save (DataFrame or string)"
                },
                "filepath": {
                    "type": "string",
                    "description": "Path where to save the CSV file"
                }
            },
            "required": ["data", "filepath"]
        }

    def execute(self, query: str, data: Optional[Union[str, pd.DataFrame]] = None, filepath: Optional[str] = None) -> ActionOutput:
        try:
            # Extract filepath from query if not provided
            if filepath is None:
                # Try to extract filepath from query
                import re
                patterns = [
                    r"save.*?(?:to|in|at)\s+['\"]?([/\w\-\.]+\.csv)['\"]?",
                    r"['\"]?([/\w\-\.]+\.csv)['\"]?",
                ]
                for pattern in patterns:
                    match = re.search(pattern, query, re.IGNORECASE)
                    if match:
                        filepath = match.group(1)
                        break

            if filepath is None:
                filepath = os.path.join(self.output_dir, "output.csv")

            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else self.output_dir, exist_ok=True)

            # Convert data to DataFrame if needed
            if isinstance(data, pd.DataFrame):
                df = data
            elif isinstance(data, str):
                # Try to parse as simple data
                return ActionOutput(
                    success=False,
                    result=None,
                    error="SaveToCSV requires a DataFrame, not a string. Use ExecuteQuery to get data first."
                )
            else:
                return ActionOutput(
                    success=False,
                    result=None,
                    error=f"SaveToCSV requires data to be a DataFrame, got {type(data)}"
                )

            # Save to CSV
            df.to_csv(filepath, index=False)

            return ActionOutput(
                success=True,
                result=f"Data saved to {filepath}",
                metadata={"filepath": filepath, "rows": len(df), "columns": len(df.columns)}
            )

        except Exception as e:
            return ActionOutput(
                success=False,
                result=None,
                error=f"SaveToCSV error: {str(e)}"
            )


class Finish(Action):
    """Complete the task and provide final answer"""

    def __init__(self, llm_client):
        super().__init__(
            name="Finish",
            description="Complete the task and provide final answer to the user. Use this as the last step to summarize results."
        )
        self.client = llm_client

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Original user query"
                },
                "result": {
                    "type": "string",
                    "description": "Result to present to user"
                }
            },
            "required": ["query"]
        }

    def execute(self, query: str, result: Optional[Union[str, pd.DataFrame]] = None) -> ActionOutput:
        try:
            from semantic_parser.llm_client import Message

            # Convert result to string if it's a dataframe
            result_str = None
            if result is not None:
                if isinstance(result, pd.DataFrame):
                    result_str = result.to_markdown(index=False)
                else:
                    result_str = str(result)

            # If no result provided, just acknowledge the query
            if result_str is None:
                final_answer = f"Task completed: {query}"
            else:
                messages = [
                    Message(role="system", content="Provide a clear, concise answer to the user's query."),
                    Message(role="user", content=f"Query: {query}\n\nResult: {result_str}\n\nProvide final answer:")
                ]
                response = self.client.chat_completion(messages)
                final_answer = response.content

            return ActionOutput(
                success=True,
                result=final_answer,
                metadata={"original_query": query, "had_result": result is not None}
            )
        except Exception as e:
            return ActionOutput(
                success=False,
                result=None,
                error=f"Finish error: {str(e)}"
            )


# List of all actions for registration
SPIDER2V_ACTIONS = [
    InspectSchema,
    GenerateSQL,
    ExecuteQuery,
    CreateFile,
    SaveToCSV,
    ClickButton,
    Finish
]
