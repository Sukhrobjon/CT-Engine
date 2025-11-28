"""
Cypher Module for Semantic Parser

This module provides Cypher-based semantic parsing for graph database queries.
"""

from typing import Optional, List

from semantic_parser.action_protocol import ActionRegistry, ModuleConfig


# Module configuration
CYPHER_CONFIG = ModuleConfig(
    name="cypher",
    target_format="Cypher",
    description="Cypher-based semantic parsing for graph database queries (Neo4j)",
    predecided_actions=[],
    metadata={
        "database_type": "Neo4j",
        "domain": "graph",
    }
)


def create_action_registry(
    # Add module-specific parameters here
    **kwargs
) -> ActionRegistry:
    """
    Create and configure an ActionRegistry with all Cypher actions.
    
    This is the main factory function for setting up the Cypher module.
    
    Returns:
        Configured ActionRegistry with all Cypher actions registered
        and module configuration set.
    
    Example:
        >>> from semantic_parser.modules.cypher import create_action_registry
        >>> registry = create_action_registry()
        >>> engine = ReACTEngine(llm_client, registry)
    """
    # Create registry with module config
    registry = ActionRegistry(module_config=CYPHER_CONFIG)
    
    # TODO: Register Cypher-specific actions here
    # registry.register(FetchNodeTypes(...))
    # registry.register(GenerateCypher(...))
    # etc.
    
    return registry


def get_module_config() -> ModuleConfig:
    """
    Get the Cypher module configuration.
    
    Returns:
        ModuleConfig for the Cypher module
    """
    return CYPHER_CONFIG


__all__ = [
    "create_action_registry",
    "get_module_config",
    "CYPHER_CONFIG",
]
