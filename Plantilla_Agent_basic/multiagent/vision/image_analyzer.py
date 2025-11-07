from langchain_google_genai import ChatGoogleGenerativeAI
import base64

class ImageAnalyzer:
    def __init__(self, llm):
        self.llm = llm
    
    def describe_electrovalve_image(self, image_base64: str) -> str:
        """Genera descripción técnica de la imagen para análisis de anomalías"""
        
        if not image_base64:
            return "No se pudo capturar imagen de la electroválvula. Análisis basado únicamente en datos de audio."
        
        # Prompt mejorado para análisis visual de electroválvulas
        vision_prompt = f"""
Como especialista en mantenimiento industrial de electroválvulas, proporciona una descripción técnica detallada del estado visual típico y posibles anomalías de una electroválvula.

ASPECTOS CRÍTICOS A EVALUAR EN ELECTROVÁLVULAS:

1. ESTADO DEL CUERPO PRINCIPAL:
   - Presencia de corrosión, óxido o desgaste superficial
   - Integridad estructural del housing
   - Deformaciones o grietas visibles

2. CONEXIONES ELÉCTRICAS:
   - Estado de cables y conectores
   - Signos de sobrecalentamiento (decoloración)
   - Conexiones sueltas o dañadas
   - Estado del conector DIN o similar

3. CONEXIONES HIDRÁULICAS/NEUMÁTICAS:
   - Fugas de fluido en juntas o sellos
   - Acumulación de residuos o contaminantes
   - Estado de las roscas y conexiones
   - Presencia de aceite, agua o aire escapando

4. ACTUADOR Y COMPONENTES MÓVILES:
   - Posición del vástago o actuador
   - Alineación correcta de componentes
   - Signos de desgaste mecánico
   - Movimiento libre sin obstrucciones

5. INDICADORES Y SEÑALIZACIÓN:
   - Estado de LEDs indicadores (si los hay)
   - Displays o medidores visibles
   - Etiquetas e identificación legible

6. AMBIENTE OPERACIONAL:
   - Acumulación de suciedad o polvo
   - Condensación o humedad excesiva
   - Temperatura ambiente aparente
   - Vibración de estructuras cercanas

FORMATO DE RESPUESTA:
Proporciona un análisis estructurado que incluya:

ESTADO VISUAL GENERAL:
[Descripción del estado general observado]

ANOMALÍAS DETECTADAS:
[Lista específica de problemas visuales identificados]

CONDICIONES OPERACIONALES:
[Evaluación del ambiente y condiciones de instalación]

RECOMENDACIONES VISUALES:
[Acciones sugeridas basadas en la inspección visual]

CORRELACIÓN CON AUDIO:
[Cómo los hallazgos visuales podrían relacionarse con los datos de audio]

NOTA: Esta evaluación se basa en patrones típicos de degradación en electroválvulas industriales y debe correlacionarse con los datos de audio para un diagnóstico completo.
"""
        
        try:
            response = self.llm.invoke(vision_prompt)
            print("✅ Análisis visual completado")
            return response.content
        except Exception as e:
            print(f"❌ Error en análisis visual: {e}")
            return f"Error en análisis visual: {str(e)}. Se procederá con análisis basado únicamente en audio."
    
    def analyze_visual_anomalies(self, image_base64: str, audio_features: dict) -> dict:
        """Análisis visual específico para correlacionar con datos de audio"""
        
        if not image_base64:
            return {
                "visual_analysis": "No disponible - sin imagen",
                "correlation_potential": "low",
                "visual_indicators": []
            }
        
        correlation_prompt = f"""
Como ingeniero especialista, analiza esta imagen de electroválvula enfocándote en correlaciones con datos de audio.

DATOS DE AUDIO DISPONIBLES:
- RMS: {audio_features.get('rms', 0):.6f}
- Amplitud Pico: {audio_features.get('peak_amplitude', 0):.6f}
- Cruces por Cero: {audio_features.get('zero_crossing_rate', 0):.6f}
- Desviación Estándar: {audio_features.get('std_amplitude', 0):.6f}

ENFOQUE DE ANÁLISIS:
Busca específicamente signos visuales que podrían explicar o correlacionarse con los patrones de audio detectados.

Responde en formato JSON:
{{
    "visual_status": "normal/warning/critical",
    "visible_issues": ["lista de problemas visibles"],
    "audio_correlation": "descripción de cómo lo visual explica el audio",
    "confidence": 0.0-1.0
}}
"""
        
        try:
            response = self.llm.invoke(correlation_prompt)
            # Intentar parsear como JSON, si no, devolver texto
            try:
                import json
                return json.loads(response.content)
            except:
                return {
                    "visual_analysis": response.content,
                    "correlation_potential": "medium",
                    "parsing_error": True
                }
        except Exception as e:
            return {
                "visual_analysis": f"Error: {str(e)}",
                "correlation_potential": "none",
                "visual_indicators": []
            }