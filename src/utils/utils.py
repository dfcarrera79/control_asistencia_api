import jwt
import random
import string
import smtplib
from src.config import config
from fastapi import HTTPException
from email.mime.text import MIMEText
from email.message import EmailMessage
from fastapi.security import HTTPBearer
from datetime import datetime, timedelta, time
from email.mime.multipart import MIMEMultipart


def get_horarios(horarios: list):
    resultados = []

    for subarreglo in horarios:
        for elemento in subarreglo:
            start = elemento["start"]
            title = elemento["title"]
            # Si time está vacío, asignar una cadena vacía
            time = elemento["time"] if elemento["time"] else ""
            resultados.append([start, title, time])

    return resultados


def nuevas_asistencias(asistencias: list, excepciones: list):
    nuevas_asistencias = []
    for diccionario in asistencias:
        fecha = diccionario['entrada'].strftime('%Y/%m/%d')
        if fecha not in excepciones and diccionario['salida'] is not None:
            nuevas_asistencias.append(diccionario)

    return nuevas_asistencias


def obtener_fechas(fecha_desde, fecha_hasta):
    fecha_desde_dt = datetime.strptime(fecha_desde, '%Y/%m/%d')
    mes_desde = fecha_desde_dt.month
    año_desde = fecha_desde_dt.year

    fecha_hasta_dt = fecha_hasta
    mes_hasta = fecha_hasta_dt.month
    año_hasta = fecha_hasta_dt.year

    # Crear lista de meses y años entre las fechas de inicio y fin
    fechas = []
    for año in range(año_desde, año_hasta + 1):
        inicio = mes_desde if año == año_desde else 1
        fin = mes_hasta + 1 if año == año_hasta else 13
        for mes in range(inicio, fin):
            fechas.append([mes, año])

    return fechas


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
    expiration = datetime.utcnow() + timedelta(hours=24)  # Set token expiration time
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


def calcular_horas(fecha, jornada, inicio1, fin1, inicio2, fin2, entrada, salida):
    horas_trabajadas = 0
    if jornada == 1:
        inicio_fecha = datetime.combine(entrada.date(), inicio1)
        fin_fecha = datetime.combine(salida.date(), fin1)
    elif jornada == 2:
        inicio_fecha = datetime.combine(fecha, inicio2)
        fin_fecha = datetime.combine(fecha, fin2)
    else:
        return 0  # Si la jornada no es 1 o 2, no se computan horas

    # Ajustar la hora de entrada si es anterior al inicio de la jornada
    if entrada < inicio_fecha:
        tiempo_diferencia = inicio_fecha - entrada
        if tiempo_diferencia.seconds <= 9000:  # Menos de 2.5 horas antes de inicio
            entrada = inicio_fecha

    # Ajustar la hora de salida si es posterior al fin de la jornada
    if salida > fin_fecha:
        tiempo_diferencia = salida - fin_fecha
        if tiempo_diferencia.seconds <= 9000:  # Menos de 2.5 horas después de fin
            salida = fin_fecha

    # Calcular horas trabajadas para la jornada correspondiente
    if entrada >= inicio_fecha and entrada <= fin_fecha:
        if salida:
            horas_trabajadas += (salida - entrada).seconds / 3600

    return horas_trabajadas


def calcular_atrasos(jornada, inicio1, fin1, inicio2, fin2, entrada, salida):
    atrasos = 0

    if jornada == 1 and salida:
        inicio_fecha = datetime.combine(entrada.date(), inicio1)
        fin_fecha = datetime.combine(salida.date(), fin1)
        if inicio_fecha <= entrada <= fin_fecha:
            atraso = (entrada - inicio_fecha).total_seconds()
            if atraso > 300:  # Más de 5 minutos de atraso
                atrasos += atraso / 60  # Convertir a minutos

    elif jornada == 2 and salida:
        inicio_fecha = datetime.combine(entrada.date(), inicio2)
        fin_fecha = datetime.combine(salida.date(), fin2)
        if inicio_fecha <= entrada <= fin_fecha:
            atraso = (entrada - inicio_fecha).total_seconds()
            if atraso > 300:  # Más de 5 minutos de atraso
                atrasos += atraso / 60  # Convertir a minutos

    return atrasos


def generate_random_filename():
    # Generate a random string of letters and digits
    letters_digits = string.ascii_letters + string.digits
    random_filename = ''.join(random.choice(letters_digits) for _ in range(10))
    return random_filename


def obtener_numero_mes(mes):
    if mes == 'Enero':
        return 1
    elif mes == 'Febrero':
        return 2
    elif mes == 'Marzo':
        return 3
    elif mes == 'Abril':
        return 4
    elif mes == 'Mayo':
        return 5
    elif mes == 'Junio':
        return 6
    elif mes == 'Julio':
        return 7
    elif mes == 'Agosto':
        return 8
    elif mes == 'Septiembre':
        return 9
    elif mes == 'Octubre':
        return 10
    elif mes == 'Noviembre':
        return 11
    elif mes == 'Diciembre':
        return 12
    else:
        return ''


def time_to_seconds(time_str: str):
    # Split the string into hours and minutes
    hours, minutes = map(int, time_str.split(':'))

    # Calculate the total seconds
    total_seconds = hours * 3600 + minutes * 60
    return total_seconds


def datetime_to_seconds(datetime_str: datetime.time):
    # Convert the datetime string to a datetime object
    hours = datetime_str.hour
    minutes = datetime_str.minute
    seconds = datetime_str.second
    microseconds = datetime_str.microsecond

    # Calculate the total seconds
    total_seconds = hours * 3600 + minutes * 60 + seconds + microseconds / 1e6

    return total_seconds


def construir_condiciones_where(departamento: str, desde: str, hasta: str):
    condiciones = []

    if departamento not in [None, '', 'N']:
        condiciones.append(f"TPlantillaRol.descripcion LIKE '{departamento}'")

    if desde not in [None, '', 'N'] and hasta not in [None, '', 'N']:
        condiciones.append(
            f"CAST(TS.fecha as date) BETWEEN '{desde}' AND '{hasta}'")

    return condiciones


def get_element(data):
    # Prioridad 1: Email y celular no están vacíos
    for item in data:
        if item["email"] and item["celular"]:
            return item

    # Prioridad 2: Solo email está presente
    for item in data:
        if item["email"]:
            return item

    # Prioridad 3: Solo celular está presente
    for item in data:
        if item["celular"]:
            return item

    # Prioridad 4: Ni email ni celular están presentes
    return data[-1] if data else None
