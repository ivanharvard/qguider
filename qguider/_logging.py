import logging

logger = logging.getLogger("qguider")

# Prevent "No handler found" warnings while allowing the
# application using qguider to configure logging however it wants.
logger.addHandler(logging.NullHandler())