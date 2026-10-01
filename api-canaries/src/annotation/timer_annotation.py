import logging
import time


logger = logging.getLogger(__name__)


def log_time(func):
    """
    A decorator that measures the execution time of a function.
    """

    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        logger.info(
            f"Function '{func.__name__}' executed in {elapsed_time:.4f} seconds."
        )
        return result

    return wrapper
