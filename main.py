
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# Авторизація Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google-credentials.json", scope)
client = gspread.authorize(creds)

# Відкриваємо таблиці
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1akbF7aSVo4uJVQdOFfPpHfM23xrAEi_s41Do2Ki-oTo/edit")
base_ws = sheet.worksheet("База")
log_ws = sheet.worksheet("Лог")
feedback_ws = sheet.worksheet("GPT_Feedback")

app = FastAPI()

class AddRowRequest(BaseModel):
    назва: str
    область: Optional[str] = ""
    район: Optional[str] = ""
    площа: Optional[float] = 0
    показники: Optional[str] = ""
    контакти: Optional[str] = ""
    нотатка: Optional[str] = ""

@app.post("/add_row")
def add_row(data: AddRowRequest):
    headers = base_ws.row_values(1)
    existing_rows = base_ws.get_all_records()

    # Перевірка на дублікати (по назві)
    if any(row.get("Назва", "").strip().lower() == data.назва.strip().lower() for row in existing_rows):
        return {"status": "duplicate", "message": "Клієнт уже існує"}

    # Формування нового рядка
    new_row = [""] * len(headers)
    for key, value in data.dict().items():
        normalized_key = key.capitalize()
        if normalized_key in headers:
            idx = headers.index(normalized_key)
            new_row[idx] = str(value)
        elif key == "нотатка" and "Нотатки" in headers:
            new_row[headers.index("Нотатки")] = str(value)

    # Додавання рядка після останнього логічного запису (відповідно до кількості записів)
    insert_row_index = len(existing_rows) + 2  # +1 заголовок, +1 новий рядок
    base_ws.insert_row(new_row, index=insert_row_index, value_input_option="USER_ENTERED")

    # Логування
    log_ws.append_row([datetime.now().isoformat(), "Додано", data.назва, data.область, data.площа, data.контакти])

    return {"status": "OK", "message": f"Клієнта {data.назва} додано на рядок {insert_row_index}"}
