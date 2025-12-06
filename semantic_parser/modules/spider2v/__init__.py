"""Spider2-V Module for CT-Engine

This module provides actions and utilities for Spider2-V benchmark tasks,
supporting multimodal data science workflows across BigQuery, dbt, and other tools.
"""

import os
from typing import Optional
from google.cloud import bigquery
from google.oauth2 import service_account

from semantic_parser.action_protocol import ActionRegistry, ModuleConfig
from semantic_parser.llm_client import AzureOpenAIClient

from .actions import (
    InspectSchema,
    GenerateSQL,
    ExecuteQuery,
    CreateFile,
    ClickButton,
    Finish,
    SPIDER2V_ACTIONS
)


SPIDER2V_CONFIG = ModuleConfig(
    name="spider2v",
    target_format="SQL",  # Can also handle dbt, Airbyte configs
    description="Multimodal data science workflow agent for Spider2-V benchmark",
    predecided_actions=[],  # No predecided actions for now
    metadata={
        "database_type": "BigQuery",
        "supports_multimodal": True,
        "tools": ["BigQuery", "dbt", "Airbyte", "Selenium"]
    }
)


def create_action_registry(
    openai_api_key: Optional[str] = None,
    deployment_name: str = "o3",
    bigquery_project: Optional[str] = None,
    service_account_path: Optional[str] = None,
    output_dir: str = "/tmp/spider2v_output"
) -> ActionRegistry:
    """
    Create and configure ActionRegistry with all Spider2-V actions.

    Args:
        openai_api_key: Azure OpenAI API key (defaults to env var)
        deployment_name: Name of deployment to use (default: "o3")
        bigquery_project: BigQuery project ID (defaults to env var)
        service_account_path: Path to service account JSON (defaults to env var)
        output_dir: Directory for CreateFile action outputs

    Returns:
        Configured ActionRegistry with all Spider2-V actions
    """
    # Get API key
    api_key = openai_api_key or os.getenv("AZURE_OPENAI_API_KEY")

    # Initialize LLM client
    llm_client = AzureOpenAIClient(
        api_key=api_key,
        deployment_name=deployment_name,
    )

    # Initialize BigQuery client
    service_account_file = service_account_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if service_account_file and os.path.exists(service_account_file):
        # Use service account credentials
        credentials = service_account.Credentials.from_service_account_file(service_account_file)
        project = bigquery_project or os.getenv("BIGQUERY_PROJECT") or credentials.project_id
        bq_client = bigquery.Client(credentials=credentials, project=project)
    elif bigquery_project:
        # Use default credentials with specified project
        bq_client = bigquery.Client(project=bigquery_project)
    else:
        # Use default credentials and project
        bq_client = bigquery.Client()

    # Create registry with module config
    registry = ActionRegistry(module_config=SPIDER2V_CONFIG)

    # Register all actions with BigQuery client
    registry.register(InspectSchema(llm_client=llm_client, bigquery_client=bq_client))
    registry.register(GenerateSQL(llm_client=llm_client))
    registry.register(ExecuteQuery(bigquery_client=bq_client, llm_client=llm_client))
    registry.register(CreateFile(output_dir=output_dir))
    registry.register(ClickButton())
    registry.register(Finish(llm_client=llm_client))

    return registry


# Public API
__all__ = [
    "create_action_registry",
    "SPIDER2V_CONFIG",
    "SPIDER2V_ACTIONS",
    "InspectSchema",
    "GenerateSQL",
    "ExecuteQuery",
    "CreateFile",
    "ClickButton",
    "Finish",
]
