import csv, json


def generate_csv():
    with open("mock.json", "r", encoding="utf-8") as f:
        json_objects = json.load(f)

    keys = ["Date", "Amount", "Category", "Title", "Note", "Account"]

    with open("gastos.csv", "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(keys)
        for obj in json_objects:
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
