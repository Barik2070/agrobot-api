
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

    
# обробка поля контакти: підтримка кількох контактів
    if data.контакти:
        contacts = [c.strip() for c in data.контакти.split(";") if c.strip()]
        for i, contact_entry in enumerate(contacts[:17]):
            # Парсимо: "ПІБ, Посада Телефон" або "ПІБ Телефон"
            contact_parts = contact_entry.strip().rsplit(" ", 1)
            name_and_pos = contact_parts[0]
            phone = contact_parts[1] if len(contact_parts) > 1 else ""

            name_parts = name_and_pos.split(",", 1)
            pib = name_parts[0].strip()
            pos = name_parts[1].strip() if len(name_parts) == 2 else ""

            if i == 0:
                name_idx = next((j for j, h in enumerate(headers) if h.lower().strip() in ["піб", "контактна особа"]), None)
                phone_idx = next((j for j, h in enumerate(headers) if h.lower().strip() == "контакт"), None)
                pos_idx = next((j for j, h in enumerate(headers) if h.lower().strip() == "посада"), None)
            else:
                name_idx = next((j for j, h in enumerate(headers) if h.lower().strip() == f"піб {i+1}"), None)
                phone_idx = next((j for j, h in enumerate(headers) if h.lower().strip() == f"контакт {i+1}"), None)
                pos_idx = next((j for j, h in enumerate(headers) if h.lower().strip() == f"посада {i+1}"), None)

            if name_idx is not None:
                new_row[name_idx] = pib
            if phone_idx is not None:
                new_row[phone_idx] = phone
            if pos_idx is not None:
                new_row[pos_idx] = pos
    base_ws.append_row(new_row, value_input_option="USER_ENTERED")

    # Логування
    log_ws.append_row([datetime.now().isoformat(), "Додано", data.назва, data.область, data.площа, data.контакти])

    return {"status": "OK", "message": f"Клієнта {data.назва} успішно додано"}
