from pydantic import BaseModel

class Transaccion(BaseModel):
    tipoTransaccion: str
    secuencial: str
    lote: str
    codigoProceso: str
    monto: str
    cajero: str
    claveCajero: str
    terminalId: str
    merchant: str
    empresa: str
    servicio: str
    telefono: str
    autorizacion: str = ''
    numeroCuenta: str = ''
    numeroRecibo: str = ''
    fechaDeposito: str = ''
    cedula: str
    nombres: str
    direccion: str

class RecargaRequest(BaseModel):
    Transaccion: Transaccion
