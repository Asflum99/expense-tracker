from db_initializer import db_initializer
from category_assigner_with_ai import process_movements
from csv_generator import generate_csv

if __name__ == "__main__":
    db_initializer()
    process_movements()
    generate_csv()
