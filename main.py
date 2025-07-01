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