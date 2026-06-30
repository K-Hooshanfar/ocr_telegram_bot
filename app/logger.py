import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("ocr_app")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "app.log"),
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
