import logging
import sys
import json
from datetime import datetime
from pathlib import Path

# Create logs directory if it doesn't exist
Path("logs").mkdir(exist_ok=True)

# Configure logging
def setup_logger(name: str = "server"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    # Create file handler
    file_handler = logging.FileHandler(
        f"logs/server_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

class SecurityAuditLogger:
    def __init__(self):
        self.logger = logging.getLogger('security_audit')
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler('security_audit.log')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.logger.addHandler(handler)

    def log_security_event(self, event_type: str, user_id: str, details: dict):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "details": details
        }
        self.logger.info(json.dumps(log_entry))

# Create global logger instance
logger = setup_logger()

# Use single logger instance across all files
# ...existing code...

# Remove logger configurations from admin.py and other files