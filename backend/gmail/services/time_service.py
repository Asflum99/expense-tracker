import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_time_range(device_time: str):
    try:
        time_now = datetime.strptime(device_time, "%Y-%m-%d %H:%M:%S")
        time_midnight_today = time_now.replace(hour=0, minute=0, second=0)

        # Convertir a timestamps
        midnight_today = str(int(time_midnight_today.timestamp()))
        now = str(int(time_now.timestamp()))

        return midnight_today, now
    except Exception as e:
        logger.warning(f"Error: {e}")
        raise
