import json
import fastapi
from fastapi import Request
from src.utils import utils
from src.config import config
from sqlalchemy.orm import Session
from email.message import EmailMessage
from sqlalchemy import create_engine, text
from src.routers.controllers import SessionHandler

# Establish connections to PostgreSQL databases for "apromed"
engine = create_engine(config.db_uri2)

# API Route Definitions
router = fastapi.APIRouter()

# Crear una instancia de la clase con tu motor de base de datos
query_handler = SessionHandler(engine)

@router.get("/validar_usuario")
async def validar_usuario(id: str, clave: str, sys: int):
    sql = f"SELECT * FROM usuario.login_usuario('{id.strip()}', {sys}) AS (codigo INTEGER, usu_login TEXT, usu_nomape TEXT, usu_clave TEXT)"
    try:
        with Session(engine) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = []

            for row in rows:
                objeto = {
                    "codigo": row.codigo,
                    "usu_login": row.usu_login,
                    "usu_nomape": row.usu_nomape,
                    "usu_clave": row.usu_clave,
                }
                objetos.append(objeto)
            
            
            if objetos[0]['codigo'] == 0:
                return {
                    "error": "S",
                    "mensaje": f"No se encuentra un usuario registrado como {id} en el sistema de control de asistencia",
                    "objetos": objetos,
                } 

            if objetos[0]["usu_clave"] == utils.codify(clave):
                # Generar token de autenticación
                token = utils.generate_token(id, clave)
                return {"error": "N", "mensaje": "", "objetos": objetos, 'token': token}
            else:
                return {
                    "error": "S",
                    "mensaje": f"La clave de acceso ingresada no es correcta, no puede acceder al sistema",
                    "objetos": objetos,
                }
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_empleado_app")
async def obtener_empleado_app(id: str):
    sql = f"SELECT codigo_empleado as codigo FROM usuario.tusuario WHERE tusuario.usu_codigo = {id.strip()}"
    return query_handler.obtener_empleado_app(sql, "", "No se encuentra registrado como empleado en el sistema SAGE ERP")


@router.get("/obtener_usuario")
async def obtener_usuario(id: str):
    sql = f"SELECT TUsuario.usu_nomape, TUsuario.usu_clave, TUsuario.usu_login, TEmpleado.nombres || ' ' || TEmpleado.apellidos AS full_name FROM rol.TEmpleado INNER JOIN usuario.TUsuario ON TEmpleado.codigo = TUsuario.codigo_empleado WHERE TRIM(TUsuario.usu_login) LIKE '{id.strip()}'"
    try:
        with Session(engine) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]

            if len(rows) == 0:
                return {
                    "error": "S",
                    "mensaje": f"No se encuentra un usuario registrado con el RUC Nro. {id} en el sistema de reclamos",
                    "objetos": rows,
                }

            return {"error": "N", "mensaje": "", "objetos": objetos[0]}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}
    
async def verificar_email(usuario: str, email: str) -> bool:
    sql = f"SELECT email FROM usuario.tusuario WHERE usu_login LIKE '{usuario.strip()}'"
    with Session(engine) as session:
        rows = session.execute(text(sql)).fetchall()
        emails = [row._mapping['email'] for row in rows]
        
    email_list = []
    for email_str in emails:
        email_list.extend(email_str.split(';'))

    return email.strip() in email_list   

@router.put("/resetear_clave_acceso")
async def resetear_clave_acceso(request: fastapi.Request):
    request_body = await request.body()
    data = json.loads(request_body)
    ruc = data['ruc']
    email = data['email']
    email_valid = await verificar_email(ruc, email)
    
    if email_valid:
        # Realizar la acción si el correo coincide
        clave = utils.generate_random_string(10)
        subject = 'Nueva clave de acceso'
        message = f"""Estimad@, mediante el presente email le enviamos la nueva clave generada y le recomendamos cambiarla lo antes posible por una personal.

        <p><strong>Nueva clave: </strong>{clave}</p>

        <p><a href='http://localhost:9000/#/cambiar_clave/{ruc.strip()}'>Cambiar la clave de acceso</a></p>"""

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = '"LoxaSoluciones" <soporte@loxasoluciones.com>'
        msg['To'] = email.strip()
        msg.set_content(message, subtype='html')
        try:
            response = await utils.email_alert(msg)
            nueva_clave = utils.codify(clave)
            sql = f"UPDATE usuario.tusuario SET usu_clave = '{nueva_clave}' WHERE usu_login like '{ruc.strip()}' RETURNING usu_codigo"
            
            if response['ok']:
                with Session(engine) as session:
                    rows = session.execute(text(sql)).fetchall()
                    session.commit()
                    objetos = [row._asdict() for row in rows]
                    return {"error": "N", "mensaje": "", "objetos": objetos}
        except Exception as error:
            return {"error": "S", "mensaje": str(error)}
    else:
        # Retornar un error si el correo no coincide
        return {"error": "S", "mensaje": "El correo ingresado no está registrado en SAGE"}
        

@router.put("/cambiar_clave")
async def cambiar_clave(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    login = data['login']
    clave = data['clave']
    try:
        nueva_clave = utils.codify(clave)
        sql = f"UPDATE usuario.tusuario SET usu_clave = '{nueva_clave.strip()}' WHERE usu_login = '{login.strip()}' RETURNING usu_codigo"
        with Session(engine) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Cambio de clave exitoso", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}
    