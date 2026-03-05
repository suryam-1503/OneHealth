from dotenv import load_dotenv
import os
load_dotenv()


class EnvData:

    ONEHEALTH_USERNAME = os.getenv("ONEHEALTH_USERNAME")
    ONEHEALTH_PASSWORD = os.getenv("ONEHEALTH_PASSWORD")
    TYPE = os.getenv("TYPE")
    PROJECT_ID = os.getenv("PROJECT_ID")
    PRIVATE_KEY_ID = os.getenv("PRIVATE_KEY_ID")
    PRIVATE_KEY = os.getenv("PRIVATE_KEY")
    CLIENT_EMAIL = os.getenv("CLIENT_EMAIL")
    CLIENT_ID = os.getenv("CLIENT_ID")
    AUTH_URI = os.getenv("AUTH_URI")
    TOKEN_URI = os.getenv("TOKEN_URI")
    AUTH_PROVIDER_X509_CERT_URL = os.getenv("AUTH_PROVIDER_URL")
    CLIENT_X509_CERT_URL = os.getenv("CLIENT_CERT_URL")
    UNIVERSAL_DOMAIN = os.getenv("UNIVERSAL_DOMAIN")
    GOOGLE_SHEETS_LINK = os.getenv("LINK")
    SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", default='Access_ClaritySync_v2')
    WORKSHEET_NAME = os.getenv("WORKSHEET_NAME", default='UHC_FILE')
    BASE_URL=os.getenv("BASE_URL")
    HEADLESS = os.getenv("HEADLESS", "false").strip().lower() == "true"


  