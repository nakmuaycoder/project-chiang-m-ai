import logging
import sys


def setup_logger(name="llm_coach", level=logging.INFO):
    """
    Configures and returns a logger with a StreamHandler pointing to stdout.
    This maintains the clean formatting of CLI tools (no timestamps, module names, etc.)
    while using the standard logging module.
    """
    logger = logging.getLogger(name)

    # Check if handlers already exist so we don't accidentally add multiples
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        # Use simple format to mimic print() for CLI
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logger.setLevel(level)
        # Prevent propagation to the root logger to avoid duplicate log entries
        logger.propagate = False

    return logger


logger = setup_logger()
