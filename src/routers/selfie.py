import os
import json
import random
import shutil
import string
import fastapi
import numpy as np
from PIL import Image
from src.config import config
import face_recognition
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from fastapi.responses import JSONResponse
from fastapi import FastAPI, UploadFile, File


# Establish connections to PostgreSQL databases for "reclamos" and "apromed" respectively
engine = create_engine(config.db_uri2)

# API Route Definitions
router = fastapi.APIRouter()


def compare_selfies(selfie1: UploadFile, selfie2_path: str):
    # Load the selfies from file paths
    image1 = face_recognition.load_image_file(selfie1.file)
    image2 = face_recognition.load_image_file(selfie2_path)

    # Get facial encodings
    encoding1 = face_recognition.face_encodings(image1)
    encoding2 = face_recognition.face_encodings(image2)

    if not encoding1 or not encoding2:
        return "No faces found in one or both images"

    # Calculate the similarity score
    similarity_score = np.linalg.norm(encoding1[0] - encoding2[0])

    # You can set a threshold to determine if the faces are the same person
    if similarity_score < 0.5:
        return True
    else:
        return False


def generate_random_filename():
    # Generate a random string of letters and digits
    letters_digits = string.ascii_letters + string.digits
    random_filename = ''.join(random.choice(letters_digits) for _ in range(10))
    return random_filename


@router.post("/subir_foto")
async def subir_foto(file: UploadFile = File(...)):
    directorio = os.path.join(os.getcwd(), 'src', 'public', 'fotos')
    try:
        os.makedirs(directorio, exist_ok=True)

        # Generate a random filename
        random_filename = generate_random_filename()
        file_extension = os.path.splitext(file.filename)[1]
        random_filename_with_extension = random_filename + file_extension

        # Save the file with the random filename
        file_path = os.path.join(directorio, random_filename_with_extension)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Convert the image to WebP format
        image = Image.open(file_path)
        webp_path = os.path.splitext(file_path)[0] + ".webp"
        image.save(webp_path, "WebP")

        # Delete the original image
        os.remove(file_path)

        # Concatenate directory and filename
        directory = os.path.join(directorio, os.path.basename(webp_path))

        return JSONResponse({
            "error": "N",
            "mensaje": "File uploaded and converted to WebP format successfully",
            "objetos": directory
        })
    except Exception as e:
        return JSONResponse({"error": "S", "mensaje": str(e)})


@router.post("/comparar_fotos/{codigo}")
async def comparar_fotos(file: UploadFile, codigo: int):

    path = await obtener_foto(codigo)
    imagen_path = path['objetos'][0]['path']

    compare = compare_selfies(file, imagen_path)

    if (compare == True):
        return {"error": "N", "mensaje": "Registro facial exitoso", "objetos": compare}

    if (compare == False):
        return {"error": "S", "mensaje": "Registro facial fallido", "objetos": compare}


@router.post("/registrar_foto")
async def registrar_foto(request: Request):
    request_body = await request.body()
    data = json.loads(request_body)
    filepath = data['filepath']
    codigo = data['usuario']

    try:
        with Session(engine) as session:
            sql = f"INSERT INTO rol.tfoto (usuario_codigo, path) VALUES('{codigo}', '{filepath}') returning id_foto"
            rows = session.execute(text(sql)).fetchall()
            session.commit()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "Foto registrada con éxito", "objetos": objetos}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}


@router.get("/obtener_foto")
async def obtener_foto(usuario: int):
    sql = f"SELECT path FROM rol.tfoto WHERE usuario_codigo={usuario}"
    try:
        with Session(engine) as session:
            rows = session.execute(
                text(sql)).fetchall()
            objetos = [row._asdict() for row in rows]
            return {"error": "N", "mensaje": "", "objetos": objetos}
    except Exception as e:
        return {"error": "S", "mensaje": str(e)}
