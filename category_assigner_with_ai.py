from groq import Groq
import sqlite3, json, os


def assign_category(obj) -> str:
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )

    prompt = f"""
    Eres un experto en categorización de transacciones bancarias.
    Responde solo con una de las siguientes categorías:
    - Comida
    - Comestibles
    - Compras
    - Transporte
    - Entretenimiento
    - Facturas y tarifas
    - Regalos
    - Belleza
    - Trabajo
    - Viajes
    - Ingreso

    Tu tarea es analizar esta transacción y devolver la categoría más apropiada.
    Transacción:
    - Monto: {obj["amount"]}
    - Beneficiario: {obj["beneficiary"]}

    Responde solo con una de las categorías listadas arriba.
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


def process_movements():
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()

    with open("mock.json", "r", encoding="utf-8") as f:
        json_objects = json.load(f)
        for obj in json_objects:
            category = obtain_category(cursor, obj)
            obj["category"] = category

    with open("mock.json", "w", encoding="utf-8") as f:
        json.dump(json_objects, f, indent=4)

    conn.commit()
    conn.close()
