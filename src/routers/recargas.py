import json
import requests
import xmltodict
from src.config import config
from sqlalchemy.orm import Session
from fastapi import APIRouter, Request
from sqlalchemy import create_engine, text
from src.models.recarga_request import RecargaRequest


# Establish connections to PostgreSQL databases for "apromed"
engine = create_engine(config.db_uri2)

# API Route Definitions
router = APIRouter()


@router.post("/recargar")
async def realizar_recarga(data: RecargaRequest):
    # Convierte el objeto Python a un diccionario
    peticion = data.peticionRequerimiento
    print('[PETICION]: ', peticion.dict())

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
    transaccion_xml = xmltodict.unparse(xml_peticion, pretty=False).replace('<?xml version="1.0" encoding="utf-8"?>', '')

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
        peticion_result = response_data['soap:Envelope']['soap:Body']['peticionRequerimientoResponse']['peticionRequerimientoResult']
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

    try:
        sql = f"""
        INSERT INTO comun.trecargas (
            grupo, cadena, comercio, proveedor, producto, lote, pos, cajero,
            fecha, hora, pvp, referencia, iso, telefono, codigo_proveedor, codigo_producto
        ) VALUES ('{data['grupo']}', '{data['cadena']}', '{data['comercio']}', '{data['proveedor']}', '{data['producto']}', '{data['lote']}', '{data['pos']}', '{data['cajero']}',
            '{data['fecha']}', '{data['hora']}', {data['pvp']}, {data['referencia']}, '{data['iso']}', '{data['telefono']}', '{data['codigo_proveedor']}', '{data['codigo_producto']}'
        ) RETURNING codigo
        """
        print('[SQL]: ', sql)
        with Session(engine) as session:
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Registro de recarga exitoso", "objetos": objetos}
    except Exception as error:
        return {"error": "S", "mensaje": str(error)}
