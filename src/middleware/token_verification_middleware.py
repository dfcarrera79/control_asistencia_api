# from fastapi import Request
from src.utils import utils


def token_verification_middleware(token: str):
    if not utils.verify_token(token):
        return {"error": "S", "mensaje": "Usuario no autorizado"}

# async def token_verification_middleware(request: Request, call_next):
#     token = request.headers.get('token')
#     if not utils.verify_token(token):
#         return {"error": "S", "mensaje": "Usuario no autorizado"}
#     response = await call_next(request)
#     return response
