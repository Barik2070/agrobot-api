from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict
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
    values = base_ws.get_all_records()

    # Перевірка на дублікати
    for row in values:
        if row.get("Назва", "").strip().lower() == data.назва.strip().lower():
            return {"status": "duplicate", "message": "Клієнт уже існує"}

    # Створення нового рядка
    new_row = [""] * len(headers)
    data_dict = data.dict()
    for key, value in data_dict.items():
        if key in headers:
            index = headers.index(key)
            new_row[index] = str(value)
        elif key == "нотатка" and "Нотатки" in headers:
            new_row[headers.index("Нотатки")] = str(value)

    # Додавання після останнього логічного запису
    base_ws.append_row(new_row, value_input_option="USER_ENTERED")
    log_ws.append_row([datetime.now().isoformat(), "Додано", data.назва, "", "", ""])
    return {"status": "OK", "message": "Клієнта додано"}