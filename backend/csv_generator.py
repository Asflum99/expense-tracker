from typing import List, Dict
import csv

def generate_csv(body: List[Dict], output_path: str) -> str:
    """
    Genera un archivo CSV a partir de los datos proporcionados.
    
    Args:
        body: Lista de diccionarios con los datos a escribir en el CSV
        output_path: Ruta donde se guardará el archivo CSV
        
    Returns:
        str: Ruta del archivo generado (mismo que output_path)
    """
    keys = ["Date", "Amount", "Category", "Title", "Note", "Account"]
    
    with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(keys)  # Escribe los encabezados
        for obj in body:
            writer.writerow(
                [
                    obj["date"],
                    obj["amount"],
                    obj["category"],
                    obj["title"],
                    obj["note"],
                    obj["account"],
                ]
            )
    
    return output_path