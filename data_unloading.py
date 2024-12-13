import os
import psycopg2
import csv
from openpyxl import Workbook
from conf_bd import host, user, password, db_name


def db_upload():
    connection = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        database=db_name
    )
    cursor = connection.cursor()

    tables = ["users", "alerts", "cryptocurrencies"]

    csv_folder = "csv"
    xlsx_folder = "xls"

    os.makedirs(csv_folder, exist_ok=True)
    os.makedirs(xlsx_folder, exist_ok=True)

    workbook = Workbook()
    xlsx_sheets = {}

    for table in tables:
        cursor.execute(f"SELECT * FROM {table};")
        data = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        csv_path = os.path.join(csv_folder, f"{table}.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(columns)
            writer.writerows(data)

        if not xlsx_sheets:
            ws = workbook.active
            ws.title = table
        else:
            ws = workbook.create_sheet(title=table)
        ws.append(columns)
        for row in data:
            ws.append(row)
        xlsx_sheets[table] = ws

    xlsx_path = os.path.join(xlsx_folder, "data.xlsx")
    workbook.save(xlsx_path)

    cursor.close()
    connection.close()

    print(f"Экспорт завершен! CSV сохранены в папке '{csv_folder}', XLSX в '{xlsx_folder}'.")
