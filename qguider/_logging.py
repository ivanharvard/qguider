import logging

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[37m",      # Gray
        logging.INFO: "\033[36m",       # Cyan
        logging.WARNING: "\033[33m",    # Yellow
        logging.ERROR: "\033[31m",      # Red
        logging.CRITICAL: "\033[1;31m", # Bold Red
    }

    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        level = f"{color}[{record.levelname}]{self.RESET}"

        return f"{level} {record.getMessage()}"


def setup_logger(name: str = "app") -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter())

    logger.addHandler(handler)
    logger.propagate = False

    return logger