import csv
import io
import logging
from io import StringIO

from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

def _generate_csv_content(movements: list[dict[str, float | str]]):
    try:
        output = StringIO()
        keys = ["Date", "Amount", "Category", "Title", "Note", "Account"]
        writer = csv.writer(output)
        writer.writerow(keys)

        for movement in movements:
            try:
                writer.writerow(
                    [
                        movement["date"],
                        movement["amount"],
                        movement.get("category", "Desconocido"),
                        movement["title"],
                        movement["note"],
                        movement["account"],
                    ]
                )
            except KeyError as e:
                logger.warning(f"Essential key missing in movement, skipping row: {e}")
                continue

        return output.getvalue()

    except Exception as e:
        logger.error(f"Error generating CSV content: {e}")
        raise


def create_csv_response(movements: list[dict[str, float | str]]):
    try:
        csv_content = _generate_csv_content(movements)

        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=gastos.csv"},
        )

    except Exception as e:
        logger.error(f"Error creating CSV response: {e}")
        raise