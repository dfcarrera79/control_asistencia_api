# from fastapi import Request
from src.utils import utils


def verify_token(token: str):
    if not utils.verify_token(token):
        return {"error": "S", "mensaje": "Usuario no autorizado"}
