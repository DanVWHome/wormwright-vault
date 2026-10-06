"""Read plain-text vault CSV files."""
import csv
from pathlib import Path


class ImportErrorDetail(ValueError):
    pass


def read_export(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as source:
        reader = csv.DictReader(source)
        required = {'description', 'link', 'user_name', 'pw', 'notes'}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ImportErrorDetail('CSV needs description, link, user_name, pw, and notes column headers.')
        rows = []
        for number, row in enumerate(reader, 2):
            if None in row or any(row.get(field) is None for field in required):
                raise ImportErrorDetail(f'Row {number} has an incorrect number of columns.')
            if not row['description'].strip():
                raise ImportErrorDetail(f'Row {number} needs a description.')
            rows.append({'description': row['description'], 'link': row['link'], 'user_name': row['user_name'], 'password': row['pw'], 'notes': row['notes']})
    if not rows:
        raise ImportErrorDetail('CSV contains no entries.')
    return rows
