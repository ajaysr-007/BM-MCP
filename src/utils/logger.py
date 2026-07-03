import logging
import sys

# Configure logger
logger = logging.getLogger("botiq-mcp-server")
logger.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)

# Stream Handler
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)

# Prevent duplicate handlers if module is reloaded
if not logger.handlers:
    logger.addHandler(stream_handler)
