
from fastapi import FastAPI, Request
from pydantic import BaseModel
import os
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = FastAPI()

# Кореневий маршрут для перевірки
@app.get("/")
def read_root():
    return {"message": "Agrobot API is live"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Клас для структури запиту
class UpdateRequest(BaseModel):
    edrpou: str
    field: str
    value: str

# Google Sheets setup
def connect_to_gsheet():
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    credentials_path = "/etc/secrets/autonomous-time-462914-xxxxxx.json"
    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_key("ТУТ_ID_ТВОЄЇ_ТАБЛИЦІ").worksheet("База")
    log_sheet = client.open_by_key("ТУТ_ID_ТВОЄЇ_ТАБЛИЦІ").worksheet("Лог")
    return sheet, log_sheet

@app.post("/update")
def update_sheet(req: UpdateRequest):
    sheet, log_sheet = connect_to_gsheet()

    data = sheet.get_all_records()
    updated = False

    for idx, row in enumerate(data, start=2):
        if str(row.get("ЄДРПОУ")) == req.edrpou:
            if req.field not in row:
                sheet.add_cols(1)
                sheet.update_cell(1, len(row) + 2, req.field)
            col_index = sheet.row_values(1).index(req.field) + 1
            sheet.update_cell(idx, col_index, req.value)
            updated = True

            log_sheet.append_row([
                str(datetime.datetime.now()),
                "оновлення",
                req.edrpou,
                req.field,
                req.value
            ])
            break

    if not updated:
        headers = sheet.row_values(1)
        new_row = [""] * len(headers)
        try:
            edrpou_index = headers.index("ЄДРПОУ")
            field_index = headers.index(req.field)
        except ValueError:
            sheet.add_cols(1)
            sheet.update_cell(1, len(headers) + 1, req.field)
            field_index = len(headers)
            headers.append(req.field)
            new_row = [""] * len(headers)
            edrpou_index = headers.index("ЄДРПОУ")

        new_row[edrpou_index] = req.edrpou
        new_row[field_index] = req.value
        sheet.append_row(new_row)
        log_sheet.append_row([
            str(datetime.datetime.now()),
            "додавання",
            req.edrpou,
            req.field,
            req.value
        ])

    return {"status": "success"}
