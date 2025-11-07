from multiagent.sensors.multimedia_capture import MultimediaSensorCapture
from datetime import datetime

class CaptureTool:
    def __init__(self):
        self.sensor_capture = MultimediaSensorCapture()
    
    def capture_sensor_data(self):
        """Captura datos de sensores (imagen y audio)"""
        try:
            image_base64 = self.sensor_capture.capture_image()
            audio_data = self.sensor_capture.capture_audio()
            audio_features = self.sensor_capture.extract_audio_features(audio_data)
            
            return {
                "image_base64": image_base64,
                "audio_features": audio_features,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error en captura de datos: {str(e)}")
            return None
