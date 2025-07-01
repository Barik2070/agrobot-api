from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import gspread
import datetime
from google.oauth2.service_account import Credentials

SHEET_ID = "1akbF7aSVo4uJVQdOFfPpHfM23xrAEi_s41Do2Ki-oTo"
SHEET_NAME = "База"
LOG_SHEET_NAME = "Лог"

app = FastAPI()

# Авторизація
scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file('/etc/secrets/credentials.json', scopes=scopes)
client = gspread.authorize(creds)

# Pydantic модель
class Farmer(BaseModel):
    Назва: str
    Область: Optional[str] = ""
    Площа: Optional[int] = 0
    Культура: Optional[str] = ""
    Телефон: Optional[str] = ""
    Потреба: Optional[str] = ""
    Місяць: Optional[str] = ""
    Примітка: Optional[str] = ""

@app.get("/")
def read_root():
    return {"message": "API is running"}

@app.get("/test-gsheet")
def test_gsheet():
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    return {"first_row": sheet.row_values(1)}

@app.get("/find-farmer")
def find_farmer(name: str):
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    results = [row for row in data if name.lower() in row.get("Назва", "").lower()]
    return {"results": results}

@app.get("/summary")
def summarize():
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    summary = {}
    for row in data:
        oblast = row.get("Область", "Невідомо")
        summary[oblast] = summary.get(oblast, 0) + 1
    return {"Кількість фермерів по областях": summary}

@app.post("/add-farmer")
def add_farmer(farmer: Farmer):
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    for row in data:
        if farmer.Назва.lower() == row.get("Назва", "").lower():
            raise HTTPException(status_code=400, detail="Фермер уже існує")
    headers = sheet.row_values(1)
    new_row = [getattr(farmer, col, "") for col in headers]
    sheet.append_row(new_row)
    log_change("Додано", farmer.Назва)
    return {"message": "Фермера додано"}

@app.post("/update-farmer")
def update_farmer(farmer: Farmer):
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    headers = sheet.row_values(1)
    for i, row in enumerate(data):
        if farmer.Назва.lower() == row.get("Назва", "").lower():
            for j, col in enumerate(headers):
                if hasattr(farmer, col) and getattr(farmer, col):
                    sheet.update_cell(i + 2, j + 1, getattr(farmer, col))
            log_change("Оновлено", farmer.Назва)
            return {"message": "Фермера оновлено"}
    raise HTTPException(status_code=404, detail="Фермер не знайдений")

@app.post("/add-column")
def add_column(column_name: str):
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    headers = sheet.row_values(1)
    if column_name in headers:
        return {"message": "Колонка вже існує"}
    sheet.add_cols(1)
    sheet.update_cell(1, len(headers) + 1, column_name)
    return {"message": f"Колонку '{column_name}' додано"}

def log_change(action: str, name: str):
    try:
        log_sheet = client.open_by_key(SHEET_ID).worksheet(LOG_SHEET_NAME)
    except gspread.WorksheetNotFound:
        log_sheet = client.open_by_key(SHEET_ID).add_worksheet(title=LOG_SHEET_NAME, rows="1000", cols="10")
        log_sheet.append_row(["Час", "Дія", "Фермер"])
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_sheet.append_row([now, action, name])

@app.post("/feedback")
def save_feedback(feedback: dict):
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet("GPT_Feedback")
    except gspread.WorksheetNotFound:
        sheet = client.open_by_key(SHEET_ID).add_worksheet(title="GPT_Feedback", rows="1000", cols="10")
        sheet.append_row(["Дата", "Користувач", "Запит", "GPT_відповідь", "Коментар", "Оцінка", "Потреба змінити логіку?", "GPT_виправлення"])

    values = [
        str(datetime.datetime.now()),
        feedback.get("user", ""),
        feedback.get("prompt", ""),
        feedback.get("response", ""),
        feedback.get("comment", ""),
        feedback.get("rating", ""),
        feedback.get("needs_fix", ""),
        feedback.get("correction", "")
    ]
    sheet.append_row(values)
    return {"message": "Фідбек збережено"}


@app.get("/feedback-summary")
def feedback_summary():
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet("GPT_Feedback")
    except gspread.WorksheetNotFound:
        raise HTTPException(status_code=404, detail="Аркуш GPT_Feedback не знайдено")

    data = sheet.get_all_records()
    total = len(data)
    low_ratings = [r for r in data if str(r.get("Оцінка", "")) in ("1", "2", "3")]
    needs_fix = [r for r in data if str(r.get("Потреба змінити логіку?")).lower() == "так"]

    return {
        "Всього фідбеків": total,
        "Низька оцінка (1–3)": len(low_ratings),
        "Записів з потребою зміни логіки": len(needs_fix),
        "Останній фідбек": data[-1] if total else {}
    }

@app.get("/feedback-insights")
def feedback_insights():
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet("GPT_Feedback")
    except gspread.WorksheetNotFound:
        raise HTTPException(status_code=404, detail="Аркуш GPT_Feedback не знайдено")

    data = sheet.get_all_records()
    if not data:
        return {"insights": "Немає фідбеку для аналізу."}

    lessons = []
    for row in reversed(data[-10:]):
        if row.get("Оцінка") in ("1", "2", "3") or str(row.get("Потреба змінити логіку?")).lower() == "так":
            insight = f"❗ Помилка у відповіді: '{row.get('GPT_відповідь', '')[:60]}...'. Коментар: {row.get('Коментар', '')}"
            if row.get("GPT_виправлення"):
                insight += f" → Пропозиція: {row['GPT_виправлення']}"
            lessons.append(insight)

    if not lessons:
        return {"insights": "Останні відповіді отримали високі оцінки — змін не потрібно."}

    return {"insights": lessons}
