"""
MLflow configuration and integration for LangGraph workflow tracing.

This module provides comprehensive MLflow integration for tracking LangGraph workflows:
- Automatic tracing via mlflow.langchain.autolog()
- Experiment management and organization
- Artifact storage and retrieval
- Performance metrics tracking
- Workflow versioning and lineage

Key Features:
- Zero-code tracing for all LangGraph workflows
- Hierarchical run tracking (orchestrator -> workflows -> nodes)
- Automatic parameter and metric logging
- S3-compatible artifact storage support
- Environment-based configuration

Usage:
    from infrastructure.observability import initialize_mlflow

    # Initialize MLflow at application startup
    initialize_mlflow()

    # All LangGraph workflows will now be automatically traced
"""

import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MLflowConfig(BaseSettings):
    """
    MLflow configuration settings loaded from environment variables.

    All settings are prefixed with MLFLOW_ and can be set via:
    - Environment variables (highest priority)
    - .env file
    - Default values (lowest priority)
    """

    model_config = SettingsConfigDict(
        env_prefix="MLFLOW_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Core MLflow settings
    tracking_uri: str = Field(
        default="./mlruns",
        description="MLflow tracking server URI (local path or remote URL)"
    )

    experiment_name: str = Field(
        default="dataops-agent-workflows",
        description="Default experiment name for all workflow runs"
    )

    enable_auto_logging: bool = Field(
        default=True,
        description="Enable automatic tracing for LangGraph workflows"
    )

    artifact_location: Optional[str] = Field(
        default=None,
        description="Custom artifact storage location (e.g., s3://bucket/path)"
    )

    registry_uri: Optional[str] = Field(
        default=None,
        description="MLflow model registry URI (defaults to tracking_uri)"
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level for MLflow operations"
    )

    enable_nested_runs: bool = Field(
        default=True,
        description="Enable nested runs for workflow nodes"
    )

    environment: str = Field(
        default="development",
        description="Deployment environment tag (development/staging/production)"
    )

    # Advanced settings
    run_name_prefix: str = Field(
        default="workflow",
        description="Prefix for MLflow run names"
    )

    enable_system_metrics: bool = Field(
        default=True,
        description="Log system metrics (CPU, memory, etc.)"
    )

    tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional tags to apply to all runs"
    )


# Global configuration instance
_mlflow_config: Optional[MLflowConfig] = None
_mlflow_initialized: bool = False


def get_mlflow_config() -> MLflowConfig:
    """
    Get the global MLflow configuration instance.

    Returns:
        MLflowConfig: Singleton configuration object
    """
    global _mlflow_config
    if _mlflow_config is None:
        _mlflow_config = MLflowConfig()
    return _mlflow_config


def initialize_mlflow() -> None:
    """
    Initialize MLflow for LangGraph workflow tracing.

    This function should be called once at application startup to:
    1. Configure MLflow tracking URI
    2. Set up the default experiment
    3. Enable automatic tracing for LangGraph
    4. Configure logging

    The function is idempotent - calling it multiple times is safe.

    Raises:
        ImportError: If MLflow is not installed
        Exception: If MLflow initialization fails
    """
    global _mlflow_initialized

    if _mlflow_initialized:
        logging.info("MLflow already initialized, skipping")
        return

    try:
        import mlflow
        import mlflow.langchain
    except ImportError as e:
        logging.warning(
            f"MLflow not available: {e}. "
            "Install with: pip install 'dataops-agent[observability]'"
        )
        return

    config = get_mlflow_config()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    try:
        # Set tracking URI
        mlflow.set_tracking_uri(config.tracking_uri)
        logger.info(f"MLflow tracking URI set to: {config.tracking_uri}")

        # Set registry URI if specified
        if config.registry_uri:
            mlflow.set_registry_uri(config.registry_uri)
            logger.info(f"MLflow registry URI set to: {config.registry_uri}")

        # Create or get experiment
        try:
            experiment = mlflow.get_experiment_by_name(config.experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(
                    name=config.experiment_name,
                    artifact_location=config.artifact_location,
                    tags={
                        "project": "dataops-agent",
                        "environment": config.environment,
                        **config.tags
                    }
                )
                logger.info(f"Created MLflow experiment: {config.experiment_name} (ID: {experiment_id})")
            else:
                logger.info(f"Using existing MLflow experiment: {config.experiment_name}")
        except Exception as exp_error:
            logger.warning(f"Could not create/get experiment: {exp_error}")

        # Set the experiment as active
        mlflow.set_experiment(config.experiment_name)

        # Enable automatic tracing for LangGraph
        if config.enable_auto_logging:
            mlflow.langchain.autolog(
                log_models=True,
                log_input_examples=True,
                log_model_signatures=True,
                extra_tags={
                    "framework": "langgraph",
                    "environment": config.environment,
                    **config.tags
                }
            )
            logger.info("MLflow automatic tracing enabled for LangGraph workflows")

        _mlflow_initialized = True
        logger.info("MLflow initialization completed successfully")

    except Exception as e:
        logger.error(f"Failed to initialize MLflow: {e}")
        raise


def setup_mlflow_tracking(
    run_name: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    nested: bool = False
) -> None:
    """
    Set up MLflow tracking for a workflow run.

    This is a convenience function for manual tracking setup.
    In most cases, autolog() handles this automatically.

    Args:
        run_name: Custom name for the MLflow run
        tags: Additional tags for the run
        nested: Whether this is a nested run
    """
    try:
        import mlflow
    except ImportError:
        logging.warning("MLflow not available, skipping tracking setup")
        return

    config = get_mlflow_config()

    # Merge tags
    all_tags = {
        "environment": config.environment,
        **config.tags,
        **(tags or {})
    }

    # Set tags for the active run
    if mlflow.active_run():
        for key, value in all_tags.items():
            mlflow.set_tag(key, value)

        if run_name:
            mlflow.set_tag("mlflow.runName", run_name)


@contextmanager
def mlflow_run(
    run_name: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    nested: bool = False,
    **kwargs
):
    """
    Context manager for MLflow runs with automatic cleanup.

    Usage:
        with mlflow_run(run_name="my-workflow", tags={"version": "1.0"}):
            # Your workflow execution
            result = workflow.invoke(state)
            mlflow.log_metric("execution_time", duration)

    Args:
        run_name: Custom name for the run
        tags: Additional tags for the run
        nested: Whether this is a nested run (child of current active run)
        **kwargs: Additional arguments passed to mlflow.start_run()

    Yields:
        MLflow Run object
    """
    try:
        import mlflow
    except ImportError:
        logging.warning("MLflow not available, running without tracing")
        yield None
        return

    config = get_mlflow_config()

    # Merge tags
    all_tags = {
        "environment": config.environment,
        **config.tags,
        **(tags or {})
    }

    # Generate run name if not provided
    if not run_name:
        run_name = f"{config.run_name_prefix}-{config.environment}"

    with mlflow.start_run(run_name=run_name, nested=nested, tags=all_tags, **kwargs) as run:
        yield run


def log_workflow_execution(
    workflow_name: str,
    parameters: Dict[str, Any],
    result: Dict[str, Any],
    execution_time: float,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Manually log workflow execution details to MLflow.

    This is typically handled automatically by autolog(), but can be used
    for additional custom logging.

    Args:
        workflow_name: Name of the executed workflow
        parameters: Input parameters to the workflow
        result: Workflow execution result
        execution_time: Total execution time in seconds
        metadata: Additional metadata to log
    """
    try:
        import mlflow
    except ImportError:
        logging.warning("MLflow not available, skipping logging")
        return

    if not mlflow.active_run():
        logging.warning("No active MLflow run, skipping logging")
        return

    try:
        # Log parameters
        for key, value in parameters.items():
            if isinstance(value, (str, int, float, bool)):
                mlflow.log_param(key, value)

        # Log metrics
        mlflow.log_metric("execution_time_seconds", execution_time)

        if result.get("success"):
            mlflow.log_metric("success", 1)
        else:
            mlflow.log_metric("success", 0)

        # Log metadata
        if metadata:
            for key, value in metadata.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(key, value)
                elif isinstance(value, str):
                    mlflow.set_tag(key, value)

        # Set tags
        mlflow.set_tag("workflow_name", workflow_name)

    except Exception as e:
        logging.error(f"Failed to log workflow execution: {e}")


def is_mlflow_available() -> bool:
    """
    Check if MLflow is available and initialized.

    Returns:
        bool: True if MLflow is available and initialized
    """
    global _mlflow_initialized
    try:
        import mlflow
        return _mlflow_initialized
    except ImportError:
        return False


def get_active_run_id() -> Optional[str]:
    """
    Get the ID of the currently active MLflow run.

    Returns:
        Optional[str]: Run ID if a run is active, None otherwise
    """
    try:
        import mlflow
        active_run = mlflow.active_run()
        return active_run.info.run_id if active_run else None
    except ImportError:
        return None
