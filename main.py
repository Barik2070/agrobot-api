from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import Optional, List
import re
import os

app = FastAPI()

# Авторизація Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("google-credentials.json", scope)
client = gspread.authorize(credentials)

SPREADSHEET_NAME = "База"
SHEET_BASE = "База"
SHEET_LOG = "Лог"

sheet = client.open(SPREADSHEET_NAME)

class Client(BaseModel):
    edrpou: Optional[str] = ""
    name: str
    region: Optional[str] = ""
    district: Optional[str] = ""
    crop: Optional[str] = ""
    area: Optional[str] = ""
    contacts: Optional[str] = ""
    note: Optional[str] = ""

# --- Сервісні функції ---
def get_headers():
    try:
        return sheet.worksheet(SHEET_BASE).row_values(1)
    except:
        return []

def normalize_header(header):
    return header.strip().lower().replace("_", " ")

def ensure_column_exists(column_name):
    headers = get_headers()
    if column_name not in headers:
        sheet.worksheet(SHEET_BASE).add_cols(1)
        sheet.worksheet(SHEET_BASE).update_cell(1, len(headers)+1, column_name)

def parse_contacts(raw):
    result = {}
    contacts = [c.strip() for c in raw.split(";") if c.strip()]
    for i, contact in enumerate(contacts):
        name, phone, title = "", "", ""
        parts = contact.split(",")
        for part in parts:
            part = part.strip()
            if re.search(r"\d{7,}", part):
                phone = part
            elif any(k in part.lower() for k in ["дир", "менедж", "голов"]):
                title = part
            else:
                name = part
        result[f"ПІБ {i+1}"] = name
        result[f"Контакт {i+1}"] = phone
        result[f"Посада {i+1}"] = title
    return result

def find_row_by_name_or_edrpou(name, edrpou):
    values = sheet.worksheet(SHEET_BASE).get_all_values()
    headers = get_headers()
    try:
        name_idx = headers.index("Назва")
    except ValueError:
        return None
    edrpou_idx = headers.index("ЄДРПОУ") if "ЄДРПОУ" in headers else -1
    for i, row in enumerate(values[1:], start=2):
        if name.lower() in row[name_idx].lower() or (edrpou and edrpou_idx != -1 and edrpou == row[edrpou_idx]):
            return i
    return None

def get_next_row():
    data = sheet.worksheet(SHEET_BASE).get_all_values()
    return len(data) + 1

# --- Ендпоінти ---
@app.post("/add_or_update_client")
def add_or_update_client(client_data: Client):
    ws = sheet.worksheet(SHEET_BASE)
    headers = get_headers()

    # Забезпечити наявність всіх колонок
    base_fields = ["ЄДРПОУ", "Назва", "Область", "Район", "Види діяльності", "Площа", "нотатка"]
    for base in base_fields:
        ensure_column_exists(base)

    contact_dict = parse_contacts(client_data.contacts or "")
    for col in contact_dict:
        ensure_column_exists(col)

    headers = get_headers()
    row_data = [""] * len(headers)

    for field in base_fields:
        if field == "ЄДРПОУ":
            val = client_data.edrpou
        elif field == "Назва":
            val = client_data.name
        elif field == "Область":
            val = client_data.region
        elif field == "Район":
            val = client_data.district
        elif field == "Види діяльності":
            val = client_data.crop
        elif field == "Площа":
            val = client_data.area
        elif field == "нотатка":
            val = client_data.note
        else:
            val = ""
        try:
            idx = headers.index(field)
            row_data[idx] = val
        except:
            continue

    for key, val in contact_dict.items():
        try:
            idx = headers.index(key)
            row_data[idx] = val
        except:
            continue

    row_number = find_row_by_name_or_edrpou(client_data.name, client_data.edrpou)
    if row_number:
        ws.update(f"A{row_number}:{chr(65+len(row_data)-1)}{row_number}", [row_data])
    else:
        ws.insert_row(row_data, get_next_row())

    # Лог
    sheet.worksheet(SHEET_LOG).append_row([client_data.name, client_data.region, client_data.crop, client_data.note])
    return {"status": "ok"}

@app.get("/list_columns")
def list_columns():
    return {"columns": get_headers()}

@app.get("/get_client_by_partial_name")
def get_client_by_partial_name(q: str):
    ws = sheet.worksheet(SHEET_BASE)
    all_data = ws.get_all_records()
    matches = [row for row in all_data if q.lower() in row.get("Назва", "").lower()]
    return {"results": matches}

@app.post("/delete_client")
def delete_client(name: str):
    ws = sheet.worksheet(SHEET_BASE)
    data = ws.get_all_values()
    headers = data[0]
    try:
        idx = headers.index("Назва")
    except ValueError:
        raise HTTPException(status_code=400, detail="Колонка 'Назва' не знайдена")
    for i, row in enumerate(data[1:], start=2):
        if name.lower() in row[idx].lower():
            ws.delete_rows(i)
            return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Не знайдено")

@app.get("/search_clients")
def search_clients(region: Optional[str] = "", district: Optional[str] = "", crop: Optional[str] = ""):
    ws = sheet.worksheet(SHEET_BASE)
    all_data = ws.get_all_records()
    results = []
    for row in all_data:
        if region and region.lower() not in row.get("Область", "").lower():
            continue
        if district and district.lower() not in row.get("Район", "").lower():
            continue
        if crop and crop.lower() not in row.get("Види діяльності", "").lower():
            continue
        results.append(row)
    return {"results": results}
