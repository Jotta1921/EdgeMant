from typing import Dict, List
import json
from datetime import datetime
import numpy as np

class LLMBasedAnomalyDetector:
    def __init__(self, llm, memory_db):
        self.llm = llm
        self.memory_db = memory_db
        self.baseline_data = []  # Solo para referencia histórica
        
    def add_baseline_sample(self, audio_features: dict, image_description: str, metadata: dict, sensor_embedding=None):
        """Almacena muestras de baseline para referencia del LLM"""
        baseline_sample = {
            "timestamp": metadata.get("timestamp", datetime.now().isoformat()),
            "audio_features": audio_features,
            "image_description": image_description,
            "metadata": metadata,
            "sensor_embedding": sensor_embedding.tolist() if sensor_embedding is not None else None,
            "status": "normal"
        }
        self.baseline_data.append(baseline_sample)
        
        # Almacenar en memoria para que el LLM pueda consultar
        self.memory_db.save_baseline_sample("electrovalve_baseline", baseline_sample)
    
    def analyze_anomaly(self, audio_features: dict, image_description: str, metadata: dict, sensor_embedding=None) -> Dict:
        """Usa el LLM para detectar anomalías comparando con baseline"""
        
        # Obtener baseline histórico de MongoDB
        baseline_samples = self.memory_db.get_baseline_samples(10)
        baseline_context = self._build_baseline_context_from_db(baseline_samples)
        
        # Crear prompt especializado
        analysis_prompt = self._create_anomaly_analysis_prompt(
            audio_features, image_description, metadata, baseline_context
        )
        
        # Solicitar análisis al LLM
        response = self.llm.invoke(analysis_prompt)
        
        # Parsear respuesta estructurada
        return self._parse_llm_response(response.content)
    
    def _build_baseline_context_from_db(self, baseline_samples: List[dict]) -> str:
        """Construye contexto de baseline desde MongoDB"""
        if not baseline_samples:
            return "No hay datos de baseline disponibles en la base de datos."
        
        context = "DATOS DE BASELINE (Funcionamiento Normal desde MongoDB):\n"
        for i, sample in enumerate(baseline_samples, 1):
            audio = sample.get('audio_features', {})
            metadata = sample.get('metadata', {})
            
            context += f"""
Muestra {i} ({sample.get('timestamp', 'No disponible')}):
- RMS Audio: {audio.get('rms', 0):.6f}
- Amplitud Pico: {audio.get('peak_amplitude', 0):.6f}
- Cruces por Cero: {audio.get('zero_crossing_rate', 0):.6f}
- Amplitud Media: {audio.get('mean_amplitude', 0):.6f}
- Desviación Estándar: {audio.get('std_amplitude', 0):.6f}
- Descripción Visual: {sample.get('image_description', 'N/A')}
- Ubicación: {metadata.get('location', 'N/A')}
- Temperatura: {metadata.get('temperature', 'N/A')}°C
- Presión: {metadata.get('pressure', 'N/A')} bar
"""
        
        # Calcular estadísticas de referencia
        rms_values = [s.get('audio_features', {}).get('rms', 0) for s in baseline_samples if s.get('audio_features')]
        peak_values = [s.get('audio_features', {}).get('peak_amplitude', 0) for s in baseline_samples if s.get('audio_features')]
        
        if rms_values and peak_values:
            context += f"""
ESTADÍSTICAS DE REFERENCIA BASELINE:
- RMS Promedio: {np.mean(rms_values):.6f} (±{np.std(rms_values):.6f})
- Amplitud Pico Promedio: {np.mean(peak_values):.6f} (±{np.std(peak_values):.6f})
- Total muestras baseline: {len(baseline_samples)}
"""
        
        return context
    
    def _create_anomaly_analysis_prompt(self, audio_features: dict, image_description: str, 
                                      metadata: dict, baseline_context: str) -> str:
        """Crea prompt especializado para análisis de anomalías - SIN SPECTRAL_CENTROID"""
        
        return f"""
Eres un ingeniero especialista en diagnóstico de electroválvulas industriales con 20 años de experiencia.

Tu tarea es analizar los datos actuales de la electroválvula y compararlos con el baseline de funcionamiento normal para detectar posibles anomalías.

{baseline_context}

DATOS ACTUALES A ANALIZAR:
Timestamp: {datetime.now().isoformat()}
Ubicación: {metadata.get('location', 'No especificada')}
Temperatura Ambiente: {metadata.get('temperature', 'No disponible')}°C
Presión del Sistema: {metadata.get('pressure', 'No disponible')} bar

CARACTERÍSTICAS DE AUDIO ACTUALES:
- RMS (Root Mean Square): {audio_features.get('rms', 0):.6f}
- Amplitud Pico: {audio_features.get('peak_amplitude', 0):.6f}
- Tasa de Cruces por Cero: {audio_features.get('zero_crossing_rate', 0):.6f}
- Amplitud Promedio: {audio_features.get('mean_amplitude', 0):.6f}
- Desviación Estándar: {audio_features.get('std_amplitude', 0):.6f}
- Duración de Captura: {audio_features.get('duration', 0)} segundos
- Frecuencia de Muestreo: {audio_features.get('sample_rate', 0)} Hz

DESCRIPCIÓN VISUAL ACTUAL:
{image_description}

GUÍA DE INTERPRETACIÓN DE MÉTRICAS:
- RMS: Indica la energía promedio del sonido (vibraciones, ruido mecánico)
- Amplitud Pico: Detecta eventos súbitos (golpes, impactos, golpe de ariete)
- Cruces por Cero: Relacionado con la frecuencia del sonido (grave/agudo, flujo laminar/turbulento)
- Amplitud Promedio: Nivel general de actividad acústica
- Desviación Estándar: Estabilidad del funcionamiento (bajo=estable, alto=errático)

CRITERIOS DE EVALUACIÓN:
- Desviaciones >20% del baseline pueden ser relevantes
- Desviaciones >50% del baseline son críticas
- Un aumento simultáneo de RMS + Pico + Desviación sugiere problemas mecánicos
- Cruces por cero altos pueden indicar turbulencia o cavitación
- Considerar siempre el contexto operacional (temperatura, presión)

INSTRUCCIONES DE ANÁLISIS:
1. Compara DETALLADAMENTE cada métrica actual con el baseline normal
2. Identifica desviaciones significativas y calcula porcentajes de cambio
3. Analiza patrones en conjunto, no métricas aisladas
4. Considera el contexto operacional (temperatura, presión, ubicación)
5. Evalúa la coherencia entre datos de audio y descripción visual

FORMATO DE RESPUESTA (ESTRICTAMENTE JSON):
{{
    "is_anomaly": true/false,
    "confidence": 0.0-1.0,
    "severity": "low/medium/high/critical",
    "anomaly_type": "acoustic/visual/operational/combined",
    "deviations_detected": [
        {{
            "metric": "nombre_métrica",
            "current_value": valor_actual,
            "baseline_range": "rango_normal",
            "deviation_percentage": porcentaje,
            "significance": "low/medium/high"
        }}
    ],
    "technical_diagnosis": "descripción técnica detallada del problema identificado basada en las métricas disponibles",
    "probable_causes": [
        "causa1: explicación basada en patrones de RMS, pico y desviación",
        "causa2: explicación basada en cruces por cero y contexto operacional"
    ],
    "recommended_actions": [
        {{
            "priority": "immediate/short_term/medium_term",
            "action": "descripción de la acción",
            "justification": "por qué es necesaria basado en los datos analizados"
        }}
    ],
    "risk_assessment": "evaluación del riesgo operacional basada en severidad y tipo de anomalía",
    "maintenance_schedule": "recomendación de mantenimiento preventivo/correctivo"
}}

IMPORTANTE: 
- Responde SOLO con el JSON válido, sin texto adicional
- Sé preciso en el análisis técnico usando las métricas disponibles
- Considera la seguridad operacional como prioridad máxima
- Basa tu diagnóstico en principios de ingeniería de mantenimiento predictivo
- Las métricas disponibles son suficientes para detectar la mayoría de anomalías en electroválvulas
"""

    def _parse_llm_response(self, llm_response: str) -> Dict:
        """Parsea la respuesta estructurada del LLM"""
        try:
            # Limpiar respuesta de posibles marcadores
            clean_response = llm_response.strip().strip('`').replace('```json', '').replace('```', '')
            
            # Parsear JSON
            result = json.loads(clean_response)
            
            # Validar estructura básica
            required_fields = ['is_anomaly', 'confidence', 'severity', 'technical_diagnosis']
            for field in required_fields:
                if field not in result:
                    result[field] = "Error: Campo faltante en respuesta"
            
            return result
            
        except json.JSONDecodeError as e:
            return {
                "error": f"Error parseando respuesta del LLM: {str(e)}",
                "raw_response": llm_response,
                "is_anomaly": False,
                "confidence": 0.0,
                "severity": "unknown",
                "technical_diagnosis": "Error en el análisis del LLM - respuesta no válida"
            }