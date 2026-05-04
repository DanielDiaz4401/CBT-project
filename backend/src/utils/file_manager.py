import json
import pandas as pd

def export_json(data: dict, filename: str):
    """
    Exporta un diccionario a un archivo JSON.
    """
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
    return filename

def import_csv(file: UploadFile):
    """
    Importa un archivo CSV a un diccionario.
    """
    return pd.read_csv(file.file)