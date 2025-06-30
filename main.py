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
