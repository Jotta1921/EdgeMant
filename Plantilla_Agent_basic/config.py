# Configuración usando SOLO variables de entorno (seguro para Docker)
import os
from pymongo import MongoClient

# Obtener credenciales SOLO de variables de entorno
MONGO_URI = "mongodb+srv://facundo:H6EN4KcYcsPuENWp@cluster.tvofp4y.mongodb.net/?retryWrites=true&w=majority&appName=Cluster"
GEMINI_API_KEY = "AIzaSyA84pwlvS9QDjLCQq7P_H10GSM2DoMQ9gw"

# Validación de variables requeridas
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable is required")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY environment variable is required")

# Test de conexión opcional (solo si se ejecuta directamente)
if __name__ == "__main__":
    client = MongoClient(MONGO_URI)
    try:
        client.admin.command('ping')
        print("✅ Conexión exitosa a MongoDB")
    except Exception as e:
        print("❌ Error conectando a MongoDB:", e)