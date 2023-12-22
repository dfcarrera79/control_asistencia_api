import jwt
import random
import string
import smtplib

from config import config
from fastapi import HTTPException
from email.mime.text import MIMEText
from email.message import EmailMessage
from fastapi.security import HTTPBearer
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart


# Codify password function
def codify(_value):
    _value = _value.strip()
    posicionRecorrido = 0
    longitudCadena = len(_value)
    valorLetraenCurso = 0
    claveEncriptada = ""
    while (posicionRecorrido < longitudCadena):
        valorLetraenCurso = ord(_value[posicionRecorrido])
        valorLetraenCurso = (valorLetraenCurso * 2) - 5
        letraCHR = chr(valorLetraenCurso)
        claveEncriptada = claveEncriptada + letraCHR
        posicionRecorrido += 1
    return claveEncriptada


# Decodify password function
def deCodify(_value):
    _value = _value.strip()
    posicionRecorrido = 0
    longitudCadena = len(_value)
    valorLetraenCurso = 0
    claveDesencriptada = ""
    while (posicionRecorrido < longitudCadena):
        valorLetraenCurso = ord(_value[posicionRecorrido])
        valorLetraenCurso = int(
            (valorLetraenCurso + 5) / 2)  # Convert to integer
        letraCHR = chr(valorLetraenCurso)
        claveDesencriptada = claveDesencriptada + letraCHR
        posicionRecorrido += 1
    return claveDesencriptada


# Generate random string to generate a new password
def generate_random_string(num):
    characters = string.ascii_letters + string.digits
    result = ''
    # characters_length = len(characters)
    for _ in range(num):
        result += random.choice(characters)
    return result


# Send email function
async def email_alert(msg):
    user = config.email['user']
    password = config.email['password']
    try:
        server = smtplib.SMTP(config.email['host'], config.email['port'])
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
        server.quit()
        return {'ok': True, 'id': '', 'mensaje': ''}
    except Exception as error:
        return {'ok': False, 'id': None, 'mensaje': str(error)}

# Authentication
security = HTTPBearer()
SECRET_KEY = config.secret_key
ALGORITHM = config.algorithm
ENCRYPTION_KEY = config.encryption_key


# Token generation
def generate_token(username: str, password: str):
    expiration = datetime.utcnow() + timedelta(hours=1)  # Set token expiration time
    payload = {
        "sub": username,
        "password": password,
        "exp": expiration
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


# Token verification
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        username = payload.get("sub")
        password = payload.get("password")
        expiration = payload.get("exp")
        expiration_date = datetime.utcfromtimestamp(expiration)

        if not (username and password and expiration and expiration_date > datetime.utcnow()):
            raise HTTPException(status_code=401, detail="Invalid token")
        return True
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Invalid token")


def traducir_dia(dia_ingles):
    dias = {
        "monday": "lunes",
        "tuesday": "martes",
        "wednesday": "miercoles",
        "thursday": "jueves",
        "friday": "viernes",
        "saturday": "sabado",
        "sunday": "domingo"
    }
    return dias.get(dia_ingles, "Día no válido")


def calcular_horas(inicio1, fin1, inicio2, fin2, entrada, salida):
    horas_trabajadas = 0

    if inicio1 <= entrada.time() <= fin1:
        if salida:
            horas_trabajadas += (salida - entrada).seconds / 3600

    if inicio2 and fin2:
        if inicio2 <= entrada.time() <= fin2:
            if salida:
                horas_trabajadas += (salida - entrada).seconds / 3600

    return horas_trabajadas


def calcular_atrasos(inicio1, fin1, inicio2, fin2, entrada, salida):
    atrasos = 0

    if inicio1 <= entrada.time() <= fin1:

        atraso = entrada - datetime.combine(entrada.date(), inicio1)
        if atraso.total_seconds() > 300:
            atrasos += atraso.total_seconds() / 60

    if inicio2 and fin2:
        if inicio2 <= entrada.time() <= fin2:

            atraso = entrada - datetime.combine(entrada.date(), inicio2)
            if atraso.total_seconds() > 300:
                atrasos += atraso.total_seconds() / 60

    return atrasos


def generate_random_filename():
    # Generate a random string of letters and digits
    letters_digits = string.ascii_letters + string.digits
    random_filename = ''.join(random.choice(letters_digits) for _ in range(10))
    return random_filename
