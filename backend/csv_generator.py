import csv


def generate_csv(body) -> str:
    keys = ["Date", "Amount", "Category", "Title", "Note", "Account"]
    file_path = "gastos.csv"

    with open(file_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(keys)
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

    return file_path