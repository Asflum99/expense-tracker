from db_initializer import db_initializer
from category_assigner_with_ai import process_movements
from csv_generator import generate_csv
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from dotenv import load_dotenv
from auth_google import auth_user, auth_status, oauth2callback
from gmail import read_messages
from logging import Logger
import os, logging, uvicorn

app = FastAPI()
app.include_router(auth_user.router)
app.include_router(auth_status.router)
app.include_router(oauth2callback.router)
app.include_router(read_messages.router)

logger: Logger = logging.getLogger(__name__)
load_dotenv()


@app.post("/process-expenses")
async def process_expenses(request: Request):
    body = await request.json()

    conn, cursor = db_initializer()
    process_movements(conn, cursor, body)
    csv_path = generate_csv(body)
    conn.close()

    # Abrimos el archivo como stream
    file_stream = open(csv_path, mode="rb")
    response = StreamingResponse(file_stream, media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=gastos.csv"

    def remove_file():
        file_stream.close()
        os.remove(csv_path)

    background_task = BackgroundTask(remove_file)

    response = StreamingResponse(
        file_stream, media_type="text/csv", background=background_task
    )
    response.headers["Content-Disposition"] = "attachment; filename=gastos.csv"

    return response


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
