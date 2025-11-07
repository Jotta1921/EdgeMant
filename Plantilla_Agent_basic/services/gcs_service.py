# services/gcs_service.py
import os
from google.cloud import storage

# Configurar el cliente de Google Cloud Storage
from config import GOOGLE_API_KEY, MONGO_URI


BUCKET_NAME = "gerenal_rag_agents" # Reemplaza con el nombre de tu bucket por ahora, Se buscará standardizar usando un solo bucket como direccion de almacenamiento para todos los futuros agentes.

def upload_qr_to_gcs(file_path, destination_blob_name):
    """Sube un archivo a Google Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(file_path)

    return f"https://storage.googleapis.com/{BUCKET_NAME}/{destination_blob_name}"
