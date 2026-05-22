import logging
import os
from pathlib import Path


def get_logger(name: str = "it_support_agent") -> logging.Logger:
    """
    Streamlit reruns scripts, so this function is careful not to add duplicate handlers.
    Logs go to:
    - console
    - <project_root>/logs/it_support_agent.log
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

    project_root = Path(__file__).resolve().parents[1]
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "it_support_agent.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False
    return logger

