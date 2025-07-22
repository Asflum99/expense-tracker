from groq import Groq
from sqlite3 import Cursor, Connection
import os


def assign_category(obj) -> str:
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )

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
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama-3.1-8b-instant",
    )

    return chat_completion.choices[0].message.content


def obtain_category(cursor, obj) -> str:
    cursor.execute(
        """
        SELECT category FROM beneficiaries WHERE name = ?
    """,
        (obj["beneficiary"],),
    )
    result = cursor.fetchone()
    if result is not None:
        return result[0]
    else:
        category = assign_category(obj)
        cursor.execute(
            """
            INSERT INTO beneficiaries (name, category) VALUES (?, ?)
        """,
            (obj["beneficiary"], category),
        )
        return category


def process_movements(conn: Connection, cursor: Cursor, body):
    for obj in body:
        category = obtain_category(cursor, obj)
        obj["category"] = category

    conn.commit()