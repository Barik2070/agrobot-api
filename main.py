from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

CREDS_FILE = "credentials.json"
SPREADSHEET_NAME = "База фермерів"
SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]

creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPE)
client = gspread.authorize(creds)
sheet = client.open(SPREADSHEET_NAME).worksheet("База")
log = client.open(SPREADSHEET_NAME).worksheet("Лог")

app = FastAPI()

class UpdateRequest(BaseModel):
    edrpou: str | None = None
    name: str | None = None
    field: str
    new_value: str
    create_column_if_missing: bool = False

@app.post("/update")
def update_client(req: UpdateRequest):
    headers = sheet.row_values(1)
    data = sheet.get_all_records()
    row_idx = None

    for i, row in enumerate(data):
        if req.edrpou and str(row.get("ЄДРПОУ", "")).strip() == req.edrpou:
            row_idx = i + 2
            break
        elif req.name and req.name.lower() in row.get("Назва", "").lower():
            row_idx = i + 2
            break

    if req.field not in headers:
        if req.create_column_if_missing:
            sheet.update_cell(1, len(headers) + 1, req.field)
            headers.append(req.field)
        else:
            return {
                "status": "missing_field",
                "message": f"Поле '{req.field}' не існує. Створити?",
                "need_confirmation": True
            }

    if row_idx:
        col_idx = headers.index(req.field) + 1
        old_value = sheet.cell(row_idx, col_idx).value
        sheet.update_cell(row_idx, col_idx, req.new_value)
        log.append_row([
            datetime.now().isoformat(),
            "Оновлення",
            req.edrpou or req.name,
            req.field,
            old_value,
            req.new_value
        ])
        return {"status": "updated", "message": f"Поле '{req.field}' оновлено"}

    new_row = [''] * len(headers)
    if "ЄДРПОУ" in headers and req.edrpou:
        new_row[headers.index("ЄДРПОУ")] = req.edrpou
    if "Назва" in headers and req.name:
        new_row[headers.index("Назва")] = req.name
    if req.field in headers:
        new_row[headers.index(req.field)] = req.new_value
    sheet.append_row(new_row)

    log.append_row([
        datetime.now().isoformat(),
        "Додавання",
        req.edrpou or req.name,
        req.field,
        "",
        req.new_value
    ])
    return {"status": "added", "message": f"Новий клієнт додано з полем '{req.field}'"}
