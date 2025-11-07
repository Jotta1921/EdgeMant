from multiagent.embedder.multimodal_embedder import MultimodalEmbedder
from datetime import datetime

class EmbeddingTool:
    def __init__(self, api_key):
        self.embedder = MultimodalEmbedder(api_key)
    
    def create_sensor_embeddings(self, image_base64, audio_features, metadata):
        """Crea embeddings multimodales de los datos de sensores"""
        try:
            metadata["timestamp"] = datetime.now().isoformat()
            sensor_embedding = self.embedder.create_sensor_embedding(
                image_base64, 
                audio_features, 
                metadata
            )
            return sensor_embedding
        except Exception as e:
            print(f"Error creando embeddings: {str(e)}")
            return None
