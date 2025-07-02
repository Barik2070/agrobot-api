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

def log_change(action: str, name: str):
    try:
        log_sheet = client.open_by_key(SHEET_ID).worksheet("Лог")
    except Exception:
        # Якщо аркуша "Лог" немає — створюємо його
        spreadsheet = client.open_by_key(SHEET_ID)
        spreadsheet.add_worksheet(title="Лог", rows=1000, cols=5)
        log_sheet = spreadsheet.worksheet("Лог")
        log_sheet.append_row(["Час", "Дія", "Фермер"])

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_sheet.append_row([now, action, name])



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
    Контакти: Optional[list[dict]] = []

def add_contacts(sheet, headers, row_index, contacts):
    max_contacts = 50  # максимум 50 тріад: Контакт N, ПІБ N, Посада N
    for contact in contacts:
        for i in range(1, max_contacts + 1):
            tel_col = f"Контакт {i}"
            pib_col = f"ПІБ {i}"
            pos_col = f"Посада {i}"
            if tel_col in headers:
                tel_val = sheet.cell(row_index, headers.index(tel_col)+1).value
                if not tel_val:
                    sheet.update_cell(row_index, headers.index(tel_col)+1, contact.get("телефон", ""))
                    sheet.update_cell(row_index, headers.index(pib_col)+1, contact.get("ПІБ", ""))
                    sheet.update_cell(row_index, headers.index(pos_col)+1, contact.get("посада", ""))
                    break

# Старий клас замінено
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
    headers = sheet.row_values(1)
    row_index = len(sheet.get_all_values())
    if farmer.Контакти:
        add_contacts(sheet, headers, row_index, farmer.Контакти)
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
            headers = sheet.row_values(1)
            if farmer.Контакти:
                add_contacts(sheet, headers, i+2, farmer.Контакти)
            log_change("Оновлено", farmer.Назва)
            return {"message": "Фермера оновлено"}
    raise HTTPException(status_code=404, detail="Фермер не знайдений")

@app.post("/add-column")
def add_column(column_name: str):
    sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    headers = sheet.row_values(1)
    if column_name in headers:
        return {"message": f"Колонка '{column_name}' вже існує"}
    try:
        sheet.add_cols(1)
        sheet.update_cell(1, len(headers) + 1, column_name)
        return {"message": f"Колонку '{column_name}' успішно додано"}
    except Exception as e:
        return {"message": f"Не вдалося створити колонку '{column_name}': {str(e)}"}
