from fastapi import FastAPI
from pydantic import BaseModel
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

app = FastAPI()

SERVICE_ACCOUNT_FILE = "/etc/secrets/credentials.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class UpdateRequest(BaseModel):
    client_name: str
    column: str
    value: str

@app.post("/update")
def update_data(req: UpdateRequest):
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=credentials)

    sheet_id = os.getenv("SHEET_ID")
    sheet_range = 'Лист1!A1:Z1000'
    sheet = service.spreadsheets()

    # отримуємо наявні дані
    result = sheet.values().get(spreadsheetId=sheet_id, range=sheet_range).execute()
    values = result.get('values', [])

    headers = values[0]
    name_col = headers.index("Назва") if "Назва" in headers else None
    if name_col is None:
        return {"error": "Колонка 'Назва' не знайдена"}

    row_index = -1
    for i, row in enumerate(values[1:], start=2):
        if len(row) > name_col and row[name_col].strip().lower() == req.client_name.strip().lower():
            row_index = i
            break

    if req.column not in headers:
        return {"error": f"Колонка '{req.column}' не знайдена. Спочатку додайте її."}

    col_index = headers.index(req.column)
    cell = chr(ord('A') + col_index) + str(row_index if row_index != -1 else len(values)+1)

    # оновлюємо або додаємо новий рядок
    sheet.values().update(
        spreadsheetId=sheet_id,
        range=f'Лист1!{cell}',
        valueInputOption="USER_ENTERED",
        body={"values": [[req.value]]}
    ).execute()

    return {"status": "updated", "cell": cell}