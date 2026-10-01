import logging

import mlflow

from conf.const import EXPERIMENT_NAME

logger = logging.getLogger(__name__)


def set_mlflow_params():
    logger.info("Set MLflow params")
    # uri = "sqlite:///mlflow.db"
    # mlflow.set_tracking_uri(uri)
    mlflow.set_tracking_uri("http://localhost:5000")
    mlflow.set_experiment(experiment_name=EXPERIMENT_NAME)
    mlflow.enable_system_metrics_logging()
    logger.info(f"MLflow Tracking URI: {mlflow.get_tracking_uri()}")
    logger.info(f"Active Experiment: {mlflow.get_experiment_by_name(EXPERIMENT_NAME)}")


def enable_mlflow_tracing():
    logger.info("Enabling MLflow autologging for tracing.")
    mlflow.autolog()
