# Agente LLM principal de mantenimiento (decisor) usando Gemini 2.0 Flash
from langchain_google_genai import ChatGoogleGenerativeAI
from multiagent.prompt_templates.prompt_main import PROMPT_TEMPLATE_MAIN

class AgentMain:
    def __init__(self, api_key: str, memory_db=None):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.2,
            max_output_tokens=1024,
        )
        self.prompt = PROMPT_TEMPLATE_MAIN
        self.memory_db = memory_db

    def _history_to_str(self, history):
        if not history:
            return ""
        # Limita el historial a los últimos 10 mensajes para optimizar tokens
        history = history[-10:]
        return "\n".join([f"{h['role']}: {h['message']}" for h in history])

    def decide_agent(self, query: str, history=None, user_id=None) -> str:
        history_str = self._history_to_str(history)
        prompt = self.prompt
        if history_str:
            prompt += f"\nHistorial reciente:\n{history_str}"
        prompt += f"\nUsuario: {query}"
        response = self.llm.invoke(prompt)
        
        # Buscar múltiples patrones para detectar derivación a electroválvula
        response_upper = response.content.upper()
        electrovalvula_patterns = [
            "AGENT_ELECTROVALVULA",
            "AGENTE_ELECTROVALVULA", 
            "ELECTROVÁLVULA",
            "ELECTROVALVULA",
            "DERIVANDO A AGENT_ELECTROVALVULA",
            "CONSULTA TÉCNICA SOBRE ELECTROVÁLVULAS"
        ]
        
        # Buscar patrones para derivación a Modbus
        modbus_patterns = [
            "AGENT_MODBUS",
            "AGENTE_MODBUS",
            "MODBUS",
            "DERIVANDO A AGENT_MODBUS",
            "COMUNICACIÓN MODBUS",
            "PROTOCOLO MODBUS",
            "COIL", "REGISTER", "ESCLAVO", "SLAVE",
            "192.168", "502", "TCP"
        ]
        
        for pattern in modbus_patterns:
            if pattern in response_upper:
                print(f"🎯 DECISIÓN: Derivando a Modbus (detectado: {pattern})")
                return "modbus"
        
        for pattern in electrovalvula_patterns:
            if pattern in response_upper:
                print(f"🎯 DECISIÓN: Derivando a electroválvula (detectado: {pattern})")
                return "electrovalvula"
        
        print(f"🎯 DECISIÓN: Respondiendo con agente main")
        print(f"📝 Respuesta del LLM decisor: {response.content[:200]}...")
        return "main"

    def run(self, query: str, history=None, user_id=None) -> str:
        history_str = self._history_to_str(history)
        prompt = self.prompt
        if history_str:
            prompt += f"\nHistorial reciente:\n{history_str}"
        prompt += f"\nUsuario: {query}"
        response = self.llm.invoke(prompt)
        return response.content
