# Tool para capturar imagen y audio (Aun no se implementa)
'''
import cv2
import sounddevice as sd
import numpy as np
from datetime import datetime
import base64
import io
from PIL import Image

class MultimediaSensorCapture:
    def __init__(self, camera_index=0, sample_rate=44100, duration=5):
        self.camera_index = camera_index
        self.sample_rate = sample_rate
        self.duration = duration
    
    def capture_image(self) -> str:
        """Captura imagen de la electroválvula con validación"""
        try:
            cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                print("⚠️ Advertencia: No se pudo acceder a la cámara")
                return None
                
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                # Convertir a base64 para el LLM
                _, buffer = cv2.imencode('.jpg', frame)
                image_base64 = base64.b64encode(buffer).decode('utf-8')
                print("✅ Imagen capturada exitosamente")
                return image_base64
            else:
                print("⚠️ Advertencia: No se pudo capturar frame de cámara")
                return None
        except Exception as e:
            print(f"❌ Error capturando imagen: {e}")
            return None
    
    def capture_audio(self) -> np.ndarray:
        """Captura audio del funcionamiento de la electroválvula con validación"""
        try:
            print(f"🎤 Capturando audio por {self.duration} segundos...")
            audio_data = sd.rec(
                int(self.duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1
            )
            sd.wait()
            print("✅ Audio capturado exitosamente")
            return audio_data.flatten()
        except Exception as e:
            print(f"❌ Error capturando audio: {e}")
            # Retornar audio silencioso como fallback
            return np.zeros(int(self.duration * self.sample_rate))
    
    def extract_audio_features(self, audio_data) -> dict:
        """Extrae características básicas del audio - SOLO MATEMÁTICAS SIMPLES"""
        try:
            if audio_data is None or len(audio_data) == 0:
                print("⚠️ Advertencia: Datos de audio vacíos, usando valores por defecto")
                return self._get_default_features()
                
            features = {
                "rms": float(np.sqrt(np.mean(audio_data**2))),
                "peak_amplitude": float(np.max(np.abs(audio_data))),
                "zero_crossing_rate": float(np.mean(np.diff(np.signbit(audio_data)))),
                "duration": self.duration,
                "sample_rate": self.sample_rate,
                "mean_amplitude": float(np.mean(np.abs(audio_data))),
                "std_amplitude": float(np.std(audio_data))
            }
            
            print("✅ Características de audio extraídas exitosamente")
            print(f"   - RMS: {features['rms']:.6f}")
            print(f"   - Peak: {features['peak_amplitude']:.6f}")
            print(f"   - Zero Crossing Rate: {features['zero_crossing_rate']:.6f}")
            
            return features
            
        except Exception as e:
            print(f"❌ Error extrayendo características de audio: {e}")
            return self._get_default_features()
    
    def _get_default_features(self) -> dict:
        """Características por defecto en caso de error"""
        return {
            "rms": 0.0,
            "peak_amplitude": 0.0,
            "zero_crossing_rate": 0.0,
            "duration": self.duration,
            "sample_rate": self.sample_rate,
            "mean_amplitude": 0.0,
            "std_amplitude": 0.0
        }
    
    def test_sensors(self) -> dict:
        """Método para probar que los sensores funcionan correctamente"""
        test_results = {
            "camera": False,
            "microphone": False,
            "errors": []
        }
        
        # Probar cámara
        try:
            cap = cv2.VideoCapture(self.camera_index)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    test_results["camera"] = True
                else:
                    test_results["errors"].append("Cámara no puede capturar frames")
            else:
                test_results["errors"].append("No se puede abrir la cámara")
            cap.release()
        except Exception as e:
            test_results["errors"].append(f"Error de cámara: {e}")
        
        # Probar micrófono
        try:
            test_audio = sd.rec(1, samplerate=self.sample_rate, channels=1)
            sd.wait()
            if test_audio is not None and len(test_audio) > 0:
                test_results["microphone"] = True
            else:
                test_results["errors"].append("Micrófono no captura audio")
        except Exception as e:
            test_results["errors"].append(f"Error de micrófono: {e}")
        
        return test_results

        '''