"""
Structured logging configuration.
"""
import logging
import sys


def configure_logging(debug: bool = False) -> None:
    """
    Set up structured logging for the application.
    In production use JSON logging; for now plain text is fine.
    """
    level = logging.DEBUG if debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if debug else logging.WARNING
    )
