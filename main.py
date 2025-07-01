from fastapi import FastAPI
import gspread
from google.oauth2.service_account import Credentials

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "API is running"}

@app.get("/test-gsheet")
def test_gsheet():
    creds = Credentials.from_service_account_file('/etc/secrets/credentials.json')
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1akbF7aSVo4uJVQd0fFppHFm23xrAEi_s41Do2Ki-oTo").worksheet("База")
    return {"first_row": sheet.row_values(1)}

@app.get("/find-farmer")
def find_farmer(name: str):
    sheet = client.open_by_key(SHEET_ID).worksheet("База")
    data = sheet.get_all_records()
    results = [row for row in data if name.lower() in row.get("Назва", "").lower()]
    return {"results": results}

@app.get("/summary")
def summarize():
    sheet = client.open_by_key(SHEET_ID).worksheet("База")
    data = sheet.get_all_records()
    summary = {}

    for row in data:
        oblast = row.get("Область", "Невідомо")
        summary[oblast] = summary.get(oblast, 0) + 1

    return {"Кількість фермерів по областях": summary}