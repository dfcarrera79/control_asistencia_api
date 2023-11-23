import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access the environment variables
db_uri1 = os.getenv("PROD_DB_URI")
db_uri2 = os.getenv("DEV_DB_URI")

email = {
    "host": os.getenv("EMAIL_HOST"),
    "port": int(os.getenv("EMAIL_PORT")),
    "secure": bool(os.getenv("EMAIL_SECURE")),
    "user": os.getenv("EMAIL_USER"),
    "password": os.getenv("EMAIL_PASSWORD"),
}

secret_key = os.getenv("SECRET_KEY")
encryption_key = os.getenv("ENCRYPTION_KEY")
algorithm = os.getenv("ALGORITHM")

path1 = os.getenv("PROD_PATH")
path2 = os.getenv("DEV_PATH")
