
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

    
    # Оновлений мапінг: ім’я та телефон окремо
    key_map = {}

    possible_matches = {
        "назва": ["назва"],
        "область": ["область"],
        "район": ["район"],
        "площа": ["площа"],
        "показники": ["показники"],
        "нотатка": ["нотатка"]
    }

    for key, options in possible_matches.items():
        for header in headers:
            if header.lower() in options:
                key_map[key] = header
                break

    # обробка контактів окремо
    contact_phone_idx = next((i for i, h in enumerate(headers) if h.lower().strip() == "контакт"), None)
    contact_name_idx = next((i for i, h in enumerate(headers) if h.lower().strip() in ["піб", "контактна особа"]), None)

    new_row = [""] * len(headers)
    for key, value in data.dict().items():
        mapped_key = key_map.get(key)
        if mapped_key and mapped_key in headers:
            idx = headers.index(mapped_key)
            new_row[idx] = str(value)

    # обробка поля контакти: розділяємо на ПІБ та телефон
    if data.контакти and contact_phone_idx is not None and contact_name_idx is not None:
        parts = data.контакти.strip().rsplit(" ", 1)
        if len(parts) == 2:
            new_row[contact_name_idx] = parts[0]
            new_row[contact_phone_idx] = parts[1]
        else:
            new_row[contact_phone_idx] = data.контакти

    for key, value in data.dict().items():
        mapped_key = key_map.get(key)
        if mapped_key and mapped_key in headers:
            idx = headers.index(mapped_key)
            new_row[idx] = str(value)

    print("🟡 Додаємо рядок до Google Sheets:", new_row)

    base_ws.append_row(new_row, value_input_option="USER_ENTERED")

    # Логування
    log_ws.append_row([datetime.now().isoformat(), "Додано", data.назва, data.область, data.площа, data.контакти])

    return {"status": "OK", "message": f"Клієнта {data.назва} успішно додано"}
