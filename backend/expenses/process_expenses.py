from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from models import Beneficiaries
from database import get_db
from groq import Groq
from dotenv import load_dotenv
from csv_generator import generate_csv
from pydantic import BaseModel
from pathlib import Path
import os, tempfile, uuid

router = APIRouter()
load_dotenv()


class MovementsList(BaseModel):
    movements: list[dict]


@router.post("/process-expenses")
async def process_expenses(request: Request, db: AsyncSession = Depends(get_db)):
    def assign_category(obj):
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

        prompt = f"""
        Eres un experto en categorización de transacciones bancarias.
        Responde solo con una de las siguientes categorías:
        Comida
        Comestibles
        Compras
        Transporte
        Entretenimiento
        Facturas y tarifas
        Regalos
        Belleza
        Trabajo
        Viajes
        Ingreso

        Tu tarea es analizar esta transacción y devolver la categoría más apropiada.
        Transacción:
        Monto: {obj["amount"]}
        Beneficiario: {obj["beneficiary"]}

        Responde solo con una de las categorías listadas arriba. No modifiques el nombre de la categoría.
        """

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], model="llama-3.1-8b-instant"
        )

        return chat_completion.choices[0].message.content

    async def obtain_category(obj, db: AsyncSession):
        try:
            result = await db.execute(
                select(Beneficiaries.category).where(
                    Beneficiaries.name == obj["beneficiary"]
                )
            )
            beneficiary = result.scalar_one_or_none()
        except Exception as e:
            print(f"DB error: {e}")
            raise
        if beneficiary is not None:
            return beneficiary
        else:
            category = assign_category(obj)
            await db.execute(
                insert(Beneficiaries).values(name=obj["beneficiary"], category=category)
            )
            await db.commit()
            return category

    def cleanup():
        try:
            if csv_path.exists():
                csv_path.unlink()
        except Exception as e:
            print(f"Error cleaning up {csv_path}: {e}")

    def file_generator():
        with open(csv_path, "rb") as file:
            yield from file
        cleanup()

    temp_dir = Path(tempfile.gettempdir())
    temp_dir.mkdir(exist_ok=True)
    csv_filename = f"gastos_{uuid.uuid4().hex}.csv"
    csv_path = temp_dir / csv_filename

    try:
        body = await request.json()

        for obj in body:
            category = await obtain_category(obj, db)
            obj["category"] = category

        generate_csv(body, str(csv_path))

        return StreamingResponse(
            file_generator(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=gastos.csv"},
        )

    except Exception as e:
        cleanup()
        raise HTTPException(status_code=500, detail=str(e))
