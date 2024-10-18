import json
import requests
import xmltodict
from src.utils import utils
from datetime import datetime
from src.config import config
from sqlalchemy.orm import Session
from fastapi import APIRouter, Request
from src.middleware import token_middleware
from sqlalchemy import create_engine, text
from src.routers.controllers import SessionHandler
from src.models.recarga_request import RecargaRequest

# Establish connections to PostgreSQL databases for "apromed"
engine = create_engine(config.db_uri2)

# Crear una instancia de la clase con tu motor de base de datos
query_handler = SessionHandler(engine)

# API Route Definitions
router = APIRouter()


@router.post("/recargar")
async def realizar_recarga(data: RecargaRequest):
    peticion = data.peticionRequerimiento

    xml_peticion = {
        "peticionRequerimiento": {
            "@xmlns": "http://tempuri.org/",
            "tipoTransaccion": peticion.tipoTransaccion,
            "codigoProceso": peticion.codigoProceso,
            "monto": peticion.monto,
            "cajero": peticion.cajero,
            "clave": peticion.clave,
            "tid": peticion.tid,
            "mid": peticion.mid,
            "proveedor": peticion.proveedor,
            "servicio": peticion.servicio,
            "cuenta": peticion.cuenta,
            "autorizacion": peticion.autorizacion,
            "referencia": peticion.referencia,
            "lote": peticion.lote,
            "sbContrapartidaNombre": peticion.sbContrapartidaNombre,
            "sbCedula": peticion.sbCedula,
            "sbDireccion": peticion.sbDireccion,
            "sbTelefono": peticion.sbTelefono,
            "sbReferencia": peticion.sbReferencia,
            "sbReferenciaAdicional": peticion.sbReferenciaAdicional,
            "sbCiudadCliente": peticion.sbCiudadCliente,
            "sbCorreoDTV": peticion.sbCorreoDTV,
            "modeloTerminal": peticion.modeloTerminal,
        }
    }

    # Convierte el diccionario a XML sin la declaración XML
    transaccion_xml = xmltodict.unparse(xml_peticion, pretty=False).replace(
        '<?xml version="1.0" encoding="utf-8"?>', '')

    # Estructura el XML dentro del formato SOAP 1.1 esperado
    soap_envelope = f'''<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
        <soap:Body>
            {transaccion_xml}
        </soap:Body>
    </soap:Envelope>'''

    url = "http://190.123.39.50/wsrecargas_test/wsrecargas.asmx"
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': '"http://tempuri.org/peticionRequerimiento"'
    }

    # Envía la solicitud POST al servicio de recargas
    try:
        response = requests.post(url, data=soap_envelope, headers=headers)
        response.raise_for_status()

        # Convierte la respuesta de XML a diccionario de Python
        response_data = xmltodict.parse(response.content)

        # Extraer el resultado de la respuesta
        peticion_result = response_data['soap:Envelope']['soap:Body'][
            'peticionRequerimientoResponse']['peticionRequerimientoResult']
        peticion_result_dict = xmltodict.parse(peticion_result)

        return {
            "error": "N",
            "mensaje": "Solicitud procesada exitosamente",
            "datos": peticion_result_dict['Transaccion']
        }

    except requests.exceptions.RequestException as e:
        return {"error": "S", "mensaje": f"Error al conectar con el servicio de recargas: {str(e)}", "datos": ""}


@router.post("/registrar_recarga")
async def registrar_recarga(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)

    # Generar lote, fecha y hora con la fecha actual
    lote = datetime.now().strftime("%y%m%d")
    fecha = datetime.now().strftime("%Y-%m-%d")  # YYYY-MM-DD
    hora = datetime.now().strftime("%H:%M:%S")  # HH:MM:SS

    try:
        sql = f"""
        INSERT INTO comun.trecargas (
            grupo, cadena, comercio, proveedor, producto, lote, pos, cajero,
            fecha, hora, pvp, referencia, iso, telefono, codigo_proveedor, codigo_producto
        ) VALUES ('{data['grupo']}', '{data['cadena']}', '{data['comercio']}', '{data['proveedor']}', '{data['producto']}', '{lote}', '{data['pos']}', '{data['cajero']}',
            '{fecha}', '{hora}', {data['pvp']}, {data['referencia']}, '{data['iso']}', '{data['telefono']}', '{data['codigo_proveedor']}', '{data['codigo_producto']}'
        ) RETURNING codigo
        """
        with Session(engine) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            # Añadir lote, fecha y hora a cada objeto retornado
            for obj in objetos:
                obj.update({"lote": lote, "fecha": fecha, "hora": hora})

            return {"error": "N", "mensaje": "Registro de recarga exitoso", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.get("/datos_factura")
async def datos_factura(request: Request, ced_ruc: str):

    # if len(ced_ruc) == 13:
    #     ced_ruc = ced_ruc[:10]
    token = request.headers.get('token')
    sql = f"""
    SELECT clp_codigo, clp_cedruc, clp_descri, clp_calles, email, celular
    FROM referente.treferente
    WHERE clp_cedruc LIKE '%' || '{ced_ruc}' || '%' 
    """

    try:
        token_middleware.verify_token(token)
        with Session(engine) as session:
            rows = session.execute(text(sql)).fetchall()
            if len(rows) == 0:
                return {"error": "S", "mensaje": "No se encontraron datos de factura"}
            session.commit()
            objetos = [row._asdict() for row in rows]
            resultado = utils.get_element(objetos)
            return {"error": "N", "mensaje": "Datos de factura", "objetos": resultado}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}


@router.put("/registrar_factura")
async def registrar_recarga(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    token = request.headers.get('token')

    factura_text = f"clp_codigo: {data['codigo']}\nced_ruc: {data['ced_ruc']}\nclp_descri: {data['clp_descri']}\nclp_calles: {data['clp_calles']}\ncelular: {data['celular']}\nemail: {data['email']}"

    # Inicia la construcción de la consulta SQL
    sql = f"UPDATE comun.trecargas SET detalle_factura = '{json.dumps(factura_text)}', autorizacion = {data['autorizacion']}"

    # Agrega el trn_codigo solo si no es 0
    if data['trn_codigo'] != 0:
        sql += f", trn_codigo = {data['trn_codigo']}"

    # Completa la consulta con la cláusula WHERE
    sql += f" WHERE codigo = {data['codigo']} RETURNING codigo"

    return query_handler.execute_sql_token(sql, token, "Factura generada con éxito.")


@router.get("/listar_conciliaciones")
async def listar_conciliaciones(request: Request, fecha: str):
    token = request.headers.get('token')
    sql = f"SELECT codigo, grupo, cadena, comercio, proveedor, producto, lote, pos, cajero, fecha, hora, pvp, autorizacion, referencia, iso, telefono, codigo_proveedor, codigo_producto FROM comun.trecargas WHERE trn_codigo IS NOT NULL and fecha = '{fecha}'"
    return query_handler.execute_sql_token(sql, token, "")
