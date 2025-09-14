# main.py (or a new logging_config.py file)
import logging

# Get a logger instance
# __name__ is a good practice as it gives the logger a name based on the module
logger = logging.getLogger(__name__)

# Set the logging level (e.g., INFO, DEBUG, WARNING, ERROR, CRITICAL)
# Messages with a level higher than or equal to this will be processed.
logger.setLevel(logging.INFO)

# Create a handler to output logs (e.g., to console, file)
# StreamHandler outputs to stderr (console by default)
handler = logging.StreamHandler()

# Define a format for your log messages
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)

# Example usage:
# logger.info("This is an info message.")
# logger.warning("This is a warning message.")
# logger.error("This is an error message.")