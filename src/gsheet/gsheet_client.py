import gspread
import ssl
import urllib3
import requests
from google.oauth2.service_account import Credentials
from utils.env_data import EnvData


def get_gspread_client():
    """
    Create a Google Sheets client using service account info from environment variables.
    Returns a gspread client object.
    """
    try:
        creds_info = {
            "type": EnvData.TYPE,
            "project_id": EnvData.PROJECT_ID,
            "private_key_id": EnvData.PRIVATE_KEY_ID,
            "private_key": EnvData.PRIVATE_KEY.replace("\\n", "\n"),
            "client_email": EnvData.CLIENT_EMAIL,
            "auth_uri": EnvData.AUTH_URI,
            "token_uri": EnvData.TOKEN_URI,
            "auth_provider_x509_cert_url": EnvData.AUTH_PROVIDER_X509_CERT_URL,
            "client_x509_cert_url": EnvData.CLIENT_X509_CERT_URL
        }

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        credentials = Credentials.from_service_account_info(creds_info, scopes=scopes)
        client = gspread.authorize(credentials)
        print(" Google Sheet client created successfully")
        return client

    except Exception as e:
        print(f" Error creating Google Sheet client: {e}")
        return None


def get_uhc_file_sheet():
    """
    Get the UHC_FILE Google Sheet
    """
    try:
        client = get_gspread_client()
        # Use spreadsheet name and worksheet name from env_data.py
        spreadsheet = client.open(EnvData.SPREADSHEET_NAME)
        sheet = spreadsheet.worksheet(EnvData.WORKSHEET_NAME)
        return sheet
    except Exception as e:
        print(f"Error accessing {EnvData.SPREADSHEET_NAME} Google Sheet: {e}")
        print(f"Error type: {type(e).__name__}")
        return None
