from datetime import datetime


def parse_date_multilocale(date: str, format_pattern: str) -> datetime:
    """Acomodar fecha según locale de sistema operativo"""

    try:
        # Parseo que funciona en Linux
        date_linux = date.replace("a. m.", "AM").replace("p. m.", "PM")
        return datetime.strptime(date_linux, format_pattern)
    except ValueError:
        # Si falla, parsear para Spanish_Peru de Windows
        date_windows = date.replace("a. m.", "a.\xa0m.").replace("p. m.", "p.\xa0m.")
        meses_espanol = [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]

        # Buscar y capitalizar el mes en español
        for mes in meses_espanol:
            if mes.lower() in date_windows.lower():  # Buscar case-insensitive
                # Encontrar la posición exacta y reemplazar preservando el caso
                import re

                pattern = re.compile(re.escape(mes), re.IGNORECASE)
                date_modified = pattern.sub(mes.capitalize(), date_windows, count=1)
                break

        return datetime.strptime(date_modified, format_pattern)
