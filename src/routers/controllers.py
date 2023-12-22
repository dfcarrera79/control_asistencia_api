from sqlalchemy import text
from sqlalchemy.orm import Session
from middleware import token_middleware


class SessionHandler:
    def __init__(self, engine):
        self.engine = engine

    def execute_sql(self, sql: str, mensaje: str):
        try:
            with Session(self.engine) as session:
                rows = session.execute(text(sql)).fetchall()
                session.commit()
                objetos = [row._asdict() for row in rows]
                return {"error": "N", "mensaje": mensaje, "objetos": objetos}
        except Exception as error:
            return {"error": "S", "mensaje": str(error), "objetos": ""}

    def execute_sql_token(self, sql: str, token, mensaje: str):
        try:
            token_middleware.verify_token(token)
            with Session(self.engine) as session:
                rows = session.execute(text(sql)).fetchall()
                session.commit()
                objetos = [row._asdict() for row in rows]
                return {"error": "N", "mensaje": mensaje, "objetos": objetos}
        except Exception as error:
            return {"error": "S", "mensaje": str(error), "objetos": ""}

    def get_exceptions(self, sql: str, token: str, desde: str, hasta: str):
        try:
            token_middleware.verify_token(token)
            with Session(self.engine) as session:
                rows = session.execute(text(sql)).fetchall()
                session.commit()
                objetos = [row._asdict() for row in rows]

                # Si se proporcionan fechas "desde" y "hasta", filtra las excepciones por ese rango
                if desde and hasta:
                    objetos = [obj for obj in objetos if all(
                        desde <= fecha <= hasta for fecha in obj["dias"])]

                return {"error": "N", "mensaje": "Registro de excepción exitoso", "objetos": objetos}
        except Exception as error:
            return {"error": "S", "mensaje": str(error), "objetos": ""}
