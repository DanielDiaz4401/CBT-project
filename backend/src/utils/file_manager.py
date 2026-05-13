import os
import json
import hashlib
import aiofiles
import pandas as pd
from fastapi import UploadFile

def export_json(data: dict, filename: str):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
    return filename

def import_csv(file: UploadFile):
    return pd.read_csv(file.file)

async def save_file_async(content: bytes, filename: str) -> tuple[str, str, int]:
    """
    Guarda un archivo de forma asíncrona sin bloquear el event loop.
    Devuelve la ruta física, el hash del contenido y el tamaño en bytes.
    """
    content_hash = hashlib.sha256(content).hexdigest()
    os.makedirs("storage/files", exist_ok=True)
    
    extension = filename.split(".")[-1] if "." in filename else "csv"
    file_path = f"storage/files/{content_hash}.{extension}"
    file_size = len(content)
    
    # Solo escribimos en disco si el archivo no existe (deduplicación)
    if not os.path.exists(file_path):
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
            
    return file_path, content_hash, file_size