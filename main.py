
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import gspread
from typing import List, Optional
from oauth2client.service_account import ServiceAccountCredentials

app = FastAPI()

# Авторизація
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)

# Завантаження таблиці
spreadsheet = client.open("База фермерів")
worksheet = spreadsheet.sheet1

class Farmer(BaseModel):
    Назва: str
    Область: Optional[str] = ""
    Площа: Optional[str] = ""
    Культура: Optional[str] = ""
    Телефон: Optional[str] = ""
    Потреба: Optional[str] = ""
    Місяць: Optional[str] = ""
    Примітка: Optional[str] = ""
    Контакти: Optional[List[dict]] = []

@app.post("/add-farmer")
def add_farmer(farmer: Farmer):
    headers = worksheet.row_values(1)
    row = [""] * len(headers)

    # Динамічне оновлення колонок
    incoming_data = farmer.dict()
    for key, value in incoming_data.items():
        if key == "Контакти":
            for i, contact in enumerate(value):
                for sub_key, sub_value in contact.items():
                    col_name = f"{sub_key} {i + 1}"
                    if col_name not in headers:
                        worksheet.add_cols(1)
                        worksheet.update_cell(1, len(headers) + 1, col_name)
                        headers.append(col_name)
                    col_index = headers.index(col_name)
                    row[col_index] = sub_value
        else:
            if key not in headers:
                worksheet.add_cols(1)
                worksheet.update_cell(1, len(headers) + 1, key)
                headers.append(key)
            col_index = headers.index(key)
            row[col_index] = value

    worksheet.append_row(row)
    return {"status": "Фермера додано"}
