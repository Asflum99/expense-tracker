from db_initializer import db_initializer
from category_assigner_with_ai import process_movements
from csv_generator import generate_csv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from google.oauth2 import id_token
from google.auth.transport import requests
import os, json

app = FastAPI()


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

@app.post("/users/auth/google")
async def google_auth(request: Request):
    try:
        # Leer el body crudo primero
        raw_body = await request.body()
        
        # Parsear el JSON desde el raw body
        body = json.loads(raw_body.decode('utf-8'))
        
        token = body.get("id_token")
        
        if not token:
            raise HTTPException(status_code=400, detail="Missing id_token")
            
        try:
            CLIENT_ID = os.environ.get("CLIENT_ID")
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)
            userid = idinfo["sub"]
        except ValueError as e:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {"userid": userid}
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")