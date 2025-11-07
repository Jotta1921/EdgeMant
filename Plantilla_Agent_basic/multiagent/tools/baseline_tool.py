class BaselineTool:
    def __init__(self, llm_detector, image_analyzer, memory_db):
        self.llm_detector = llm_detector
        self.image_analyzer = image_analyzer
        self.memory_db = memory_db
    
    def add_baseline_sample(self, image_base64, audio_features, metadata, sensor_embedding):
        """Añade una muestra de baseline con embeddings"""
        try:
            # Analizar imagen para descripción
            image_description = self.image_analyzer.describe_electrovalve_image(image_base64)
            
            # Añadir muestra al detector de anomalías
            self.llm_detector.add_baseline_sample(
                audio_features,
                image_description,
                metadata,
                sensor_embedding
            )
            
            return True, "Muestra de baseline añadida exitosamente"
            
        except Exception as e:
            error_msg = f"Error añadiendo muestra baseline: {str(e)}"
            print(error_msg)
            return False, error_msg
