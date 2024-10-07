from pydantic import BaseModel

class PeticionRequerimiento(BaseModel):
    tipoTransaccion: str
    codigoProceso: str
    monto: str
    cajero: str
    clave: str
    tid: str
    mid: str
    proveedor: str
    servicio: str
    cuenta: str
    autorizacion: str
    referencia: str
    lote: str
    sbContrapartidaNombre: str
    sbCedula: str
    sbDireccion: str
    sbTelefono: str
    sbReferencia: str
    sbReferenciaAdicional: str
    sbCiudadCliente: str
    sbCorreoDTV: str
    modeloTerminal: str

class RecargaRequest(BaseModel):
    peticionRequerimiento: PeticionRequerimiento
