from langchain_google_genai import GoogleGenerativeAIEmbeddings
import numpy as np
from typing import Dict, List
import json

class MultimodalEmbedder:
    def __init__(self, google_api_key: str):
        self.text_embedder = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=google_api_key
        )
    
    def create_sensor_embedding(self, 
                               image_base64: str, 
                               audio_features: dict, 
                               metadata: dict) -> np.ndarray:
        """Crea embedding de datos multimodales para que el LLM pueda procesarlos"""
        
        # Convertir datos técnicos a descripción textual
        sensor_description = f"""
        DATOS TÉCNICOS DE ELECTROVÁLVULA:
        Timestamp: {metadata.get('timestamp', 'No disponible')}
        Ubicación: {metadata.get('location', 'No especificada')}
        Temperatura ambiente: {metadata.get('temperature', 'No disponible')}°C
        Presión del sistema: {metadata.get('pressure', 'No disponible')} bar
        
        CARACTERÍSTICAS DE AUDIO:
        - RMS (Valor eficaz): {audio_features.get('rms', 0):.6f}
        - Amplitud pico: {audio_features.get('peak_amplitude', 0):.6f}
        - Tasa de cruces por cero: {audio_features.get('zero_crossing_rate', 0):.6f}
        - Amplitud promedio: {audio_features.get('mean_amplitude', 0):.6f}
        - Desviación estándar: {audio_features.get('std_amplitude', 0):.6f}
        - Duración de captura: {audio_features.get('duration', 0)} segundos
        - Frecuencia de muestreo: {audio_features.get('sample_rate', 0)} Hz
        
        DESCRIPCIÓN VISUAL:
        [La descripción visual será proporcionada por separado por el analizador de imágenes]
        
        CONTEXTO OPERACIONAL:
        Los datos corresponden a una electroválvula industrial en operación.
        El audio captura vibraciones, ruidos mecánicos y flujo de fluidos.
        La imagen muestra el estado visual actual del componente.
        """
        
        # Crear embedding textual que el LLM puede procesar
        embedding = self.text_embedder.embed_query(sensor_description)
        return np.array(embedding)
    
    def create_baseline_context_embedding(self, baseline_samples: List[dict]) -> str:
        """Crea contexto embedizado de muestras baseline para el LLM"""
        
        if not baseline_samples:
            return "No hay datos de baseline disponibles."
        
        context = "CONTEXTO DE BASELINE (Funcionamiento Normal Histórico):\n\n"
        
        for i, sample in enumerate(baseline_samples[-10:], 1):  # Últimas 10 muestras
            audio = sample.get('audio_features', {})
            metadata = sample.get('metadata', {})
            
            context += f"""
MUESTRA BASELINE #{i}:
Fecha: {sample.get('timestamp', 'No disponible')}
Ubicación: {metadata.get('location', 'No especificada')}
Condiciones: Temp {metadata.get('temperature', 'N/A')}°C, Presión {metadata.get('pressure', 'N/A')} bar

Audio Normal:
- RMS: {audio.get('rms', 0):.6f}
- Pico: {audio.get('peak_amplitude', 0):.6f}
- Cruces cero: {audio.get('zero_crossing_rate', 0):.6f}
- Amplitud media: {audio.get('mean_amplitude', 0):.6f}
- Desv. estándar: {audio.get('std_amplitude', 0):.6f}

Visual Normal: {sample.get('image_description', 'No disponible')}
Estado: FUNCIONAMIENTO NORMAL CONFIRMADO
---
"""
        
        # Calcular estadísticas de referencia
        rms_values = [s.get('audio_features', {}).get('rms', 0) for s in baseline_samples]
        peak_values = [s.get('audio_features', {}).get('peak_amplitude', 0) for s in baseline_samples]
        
        if rms_values and peak_values:
            context += f"""
ESTADÍSTICAS DE REFERENCIA BASELINE:
- RMS típico: {np.mean(rms_values):.6f} (±{np.std(rms_values):.6f})
- Pico típico: {np.mean(peak_values):.6f} (±{np.std(peak_values):.6f})
- Muestras totales: {len(baseline_samples)}
- Rango temporal: Normal establecido
"""
        
        return context