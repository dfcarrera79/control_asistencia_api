from src.config import config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

db_uri2 = config.db_uri2
engine2 = create_engine(db_uri2)


async def tiene_acceso(usucodigo: int, modcodigo: int, accion: int):
    sql = f"SELECT * FROM usuario.tiene_acceso({usucodigo}, {modcodigo}, {accion})"

    with Session(engine2) as session:
        rows = session.execute(text(sql)).fetchall()
        objetos = [row._asdict() for row in rows]
        return objetos
