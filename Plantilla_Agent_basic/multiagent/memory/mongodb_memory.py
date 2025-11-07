from pymongo import MongoClient
import datetime

class MongoMemory:
    def __init__(self, mongo_uri: str, db_name: str = "agent_memory_plantilla", collection_name: str = "conversations"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        self.baseline_collection = self.db["baseline_data"]
        self.analysis_collection = self.db["analysis_records"]

    def save_message(self, user_id: str, role: str, message: str):
        """Guarda el mensaje junto con la hora en que se guardó."""
        data = {
            "user_id": user_id,
            "role": role,  # 'user' o 'agent'
            "message": message,
            "timestamp": datetime.datetime.utcnow()
        }
        self.collection.insert_one(data)

    def get_conversation(self, user_id: str):
        """Recupera todo el historial de la conversación para el usuario dado, ordenado por fecha."""
        return list(self.collection.find({"user_id": user_id}).sort("timestamp", 1))
    
    def save_baseline_sample(self, collection_name: str, baseline_sample: dict):
        """Guarda muestra de baseline para referencia del LLM"""
        baseline_sample["saved_timestamp"] = datetime.datetime.utcnow()
        self.baseline_collection.insert_one(baseline_sample)
    
    def save_analysis_record(self, collection_name: str, analysis_record: dict):
        """Guarda registro de análisis para histórico"""
        analysis_record["saved_timestamp"] = datetime.datetime.utcnow()
        self.analysis_collection.insert_one(analysis_record)
    
    def get_baseline_samples(self, limit: int = 10):
        """Obtiene muestras de baseline más recientes para el LLM"""
        return list(self.baseline_collection.find().sort("saved_timestamp", -1).limit(limit))
    
    def get_recent_analysis(self, limit: int = 5):
        """Obtiene análisis recientes para contexto del LLM"""
        return list(self.analysis_collection.find().sort("saved_timestamp", -1).limit(limit))