from fastapi import FastAPI
import gspread
from google.oauth2.service_account import Credentials

app = FastAPI()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

@app.get("/")
def read_root():
    return {"message": "API is running"}

@app.get("/test-gsheet")
def test_gsheet():
    creds = Credentials.from_service_account_file('/etc/secrets/credentials.json', scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open("TestSheet").sheet1
    return {"first_row": sheet.row_values(1)}
