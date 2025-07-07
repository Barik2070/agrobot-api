
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

# FastAPI ініціалізація
app = FastAPI()

# --- Моделі запитів ---
class AddRowRequest(BaseModel):
    назва: str
    область: Optional[str] = ""
    район: Optional[str] = ""
    площа: Optional[float] = 0
    показники: Optional[str] = ""
    контакти: Optional[str] = ""
    нотатка: Optional[str] = ""

class UpdateRowRequest(BaseModel):
    ключ: str  # ЄДРПОУ або Назва
    поле: str
    нове_значення: str

class AddColumnRequest(BaseModel):
    назва_колонки: str

class ReportRequest(BaseModel):
    фільтр: Dict[str, str]

class LogActionRequest(BaseModel):
    дія: str
    назва: str
    поле: Optional[str] = ""
    старе: Optional[str] = ""
    нове: Optional[str] = ""

class FeedbackRequest(BaseModel):
    запит: str
    gpt_відповідь: Optional[str] = ""
    оцінка: Optional[int] = 0
    коментар: str
    виправлення: Optional[str] = ""

# --- Ендпоінти ---
@app.post("/add_row")
def add_row(data: AddRowRequest):
    headers = base_ws.row_values(1)
    row = [""] * len(headers)
    data_dict = data.dict()
    for key, value in data_dict.items():
        if key in headers:
            index = headers.index(key)
            row[index] = str(value)
        elif key == "нотатка" and "Нотатки" in headers:
            row[headers.index("Нотатки")] = str(value)

    base_ws.append_row(row, value_input_option="USER_ENTERED")
    log_ws.append_row([datetime.now().isoformat(), "Додано", data.назва, "", "", ""])
    return {"status": "OK", "message": "Клієнта додано"}

@app.post("/update_row")
def update_row(data: UpdateRowRequest):
    headers = base_ws.row_values(1)
    values = base_ws.get_all_records()
    for i, row in enumerate(values):
        if row.get("ЄДРПОУ") == data.ключ or row.get("Назва") == data.ключ:
            old_value = row.get(data.поле, "")
            if data.поле not in headers:
                return {"error": "Поле не знайдено"}
            col = headers.index(data.поле) + 1
            base_ws.update_cell(i + 2, col, data.нове_значення)
            log_ws.append_row([datetime.now().isoformat(), "Оновлено", data.ключ, data.поле, old_value, data.нове_значення])
            return {"status": "OK", "message": "Оновлено"}
    return {"error": "Клієнта не знайдено"}

@app.post("/add_column")
def add_column(data: AddColumnRequest):
    headers = base_ws.row_values(1)
    if data.назва_колонки not in headers:
        base_ws.add_cols(1)
        base_ws.update_cell(1, len(headers)+1, data.назва_колонки)
        return {"status": "OK", "message": "Колонка додана"}
    return {"message": "Колонка вже існує"}

@app.post("/report")
def report(data: ReportRequest):
    values = base_ws.get_all_records()
    result = []
    for row in values:
        match = True
        for key, val in data.фільтр.items():
            if str(row.get(key, "")).lower() != str(val).lower():
                match = False
                break
        if match:
            result.append(row)
    return {"rows": result}

@app.post("/log")
def log_action(data: LogActionRequest):
    log_ws.append_row([datetime.now().isoformat(), data.дія, data.назва, data.поле, data.старе, data.нове])
    return {"status": "OK", "message": "Записано"}

@app.post("/feedback")
def feedback(data: FeedbackRequest):
    feedback_ws.append_row([
        data.запит,
        data.gpt_відповідь or "",
        data.оцінка or 0,
        data.коментар,
        "Так" if data.виправлення else "Ні",
        data.виправлення or ""
    ])
    return {"status": "OK", "message": "Фідбек збережено"}
