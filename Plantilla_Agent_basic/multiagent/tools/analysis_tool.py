class AnalysisTool:
    def __init__(self, llm_detector, image_analyzer, memory_db):
        self.llm_detector = llm_detector
        self.image_analyzer = image_analyzer
        self.memory_db = memory_db
    
    def analyze_sensor_data(self, image_base64, audio_features, metadata, sensor_embedding):
        """Analiza los datos de sensores y detecta anomalías"""
        try:
            # Analizar imagen con LLM
            image_description = self.image_analyzer.describe_electrovalve_image(image_base64)
            
            # Detectar anomalías usando LLM con embeddings
            anomaly_result = self.llm_detector.analyze_anomaly(
                audio_features, 
                image_description, 
                metadata, 
                sensor_embedding
            )
            
            # Guardar análisis en memoria
            analysis_record = {
                "audio_features": audio_features,
                "image_description": image_description,
                "metadata": metadata,
                "anomaly_result": anomaly_result,
                "sensor_embedding": sensor_embedding.tolist()
            }
            
            self.memory_db.save_analysis_record("electrovalve_analysis", analysis_record)
            
            return anomaly_result, image_description
            
        except Exception as e:
            print(f"Error en análisis de datos: {str(e)}")
            return None, None
