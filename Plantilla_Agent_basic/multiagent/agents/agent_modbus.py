# Agente LLM especializado en comunicación Modbus usando Gemini 2.5 Flash
from langchain_google_genai import ChatGoogleGenerativeAI
from multiagent.tools.modbus_tool import ModbusTool
from langchain_core.tools import tool
import logging
import json

# Configurar logging
logger = logging.getLogger(__name__)


class AgentModbus:
    def __init__(self, api_key: str, memory_db=None):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.2,
            max_output_tokens=1536,
        )

        self.memory_db = memory_db
        self.modbus_tool = ModbusTool()

        # Configurar herramientas para el LLM
        self.tools = self._setup_modbus_tools()

        # Prompt especializado para Modbus
        # self.prompt = PROMPT_MODBUS
        self.prompt = """
Eres un experto técnico especializado en comunicación Modbus TCP.

Tu función es ayudar con:

1. **Lectura de Coils**: Consultar el estado de salidas digitales (ON/OFF)
2. **Escritura de Coils**: Controlar dispositivos (encender/apagar)
3. **Lectura de Registros de Holding**: Obtener valores de configuración o datos de proceso
4. **Lectura de Registros de Entrada**: Leer valores de sensores o entradas analógicas

**INFORMACIÓN IMPORTANTE:**
- Modbus TCP usa típicamente el puerto 502
- Los dispositivos esclavos tienen IDs únicos (1-247)
- Las direcciones empiezan en 0
- Las coils son salidas digitales (True/False)
- Los registros contienen valores numéricos (16-bit)

**CAPACIDADES MÚLTIPLES:**
- Puedes leer/escribir múltiples coils o registros en una sola operación
- Para coils: puedes especificar direcciones individuales o listas de direcciones
- Para registros: puedes leer múltiples registros específicos o contiguos
- Las operaciones múltiples son más eficientes que las individuales
- Cuando termines de escribir coils o registros, lee el estado de estás para verificar si se cambiaron exitosamente, si no es el caso, vuelve a intentar escribir sobre las coils o registros que no se cambiaron
- Los intentos de escritura no deben superar los 3 intentos

**FORMATO DE RESPUESTA:**
- Siempre explica qué hace cada operación
- Proporciona información clara sobre los parámetros necesarios
- Si hay errores, explica las posibles causas y soluciones
- Mantén un tono técnico pero accesible
- Cuando sea posible, agrupa operaciones similares para mayor eficiencia

**HERRAMIENTAS DISPONIBLES:**
- write_modbus_coil: Para encender/apagar dispositivos (una o múltiples coils)
- read_modbus_coil: Para consultar estado de salidas digitales (una o múltiples coils)
- read_modbus_holding_registers: Para leer configuraciones del dispositivo (uno o múltiples registros)
- read_modbus_input_registers: Para leer valores de sensores (uno o múltiples registros)

**EJEMPLOS DE USO:**
- Una coil: COIL_ADDRESSES=100
- Múltiples coils: COIL_ADDRESSES=[100, 101, 102]
- Coils con estados específicos: COIL_ADDRESSES={100: True, 101: False}
- Un registro: ADDRESSES=200
- Múltiples registros: ADDRESSES=[200, 201, 202]

Responde de manera clara y precisa a las consultas sobre comunicación Modbus.
        """

    def _setup_modbus_tools(self):
        """Configura las herramientas Modbus para el LLM"""

        @tool("write_modbus_coil")
        def write_coil_tool(
            HOST: str, PORT: int, COIL_ADDRESSES, SLAVE_UNIT: int, STATE: bool = None
        ) -> str:
            """
            Escribe el estado de una o múltiples coils (salidas digitales) en un dispositivo Modbus TCP.

            Args:
                HOST: Dirección IP del dispositivo Modbus TCP (ej: '192.168.1.10')
                PORT: Puerto TCP (típicamente 502)
                COIL_ADDRESSES: Puede ser:
                    - int: Una sola coil (ej: 100)
                    - List[int]: Múltiples coils con mismo estado (ej: [100, 101, 102])
                    - Dict[int, bool]: Coils con estados específicos (ej: {100: True, 101: False})
                SLAVE_UNIT: ID del dispositivo esclavo (ej: 1)
                STATE: Estado a escribir para todas las coils (solo si COIL_ADDRESSES es int o List[int])
            """
            result = self.modbus_tool.write_modbus_coil(
                HOST, PORT, COIL_ADDRESSES, SLAVE_UNIT, STATE
            )
            return json.dumps(result, indent=2, ensure_ascii=False)

        @tool("read_modbus_coil")
        def read_coil_tool(
            HOST: str, PORT: int, COIL_ADDRESSES, SLAVE_UNIT: int
        ) -> str:
            """
            Lee el estado de una o múltiples coils (salidas digitales) de un dispositivo Modbus TCP.

            Args:
                HOST: Dirección IP del dispositivo Modbus TCP (ej: '192.168.1.10')
                PORT: Puerto TCP (típicamente 502)
                COIL_ADDRESSES: Puede ser:
                    - int: Una sola coil (ej: 100)
                    - List[int]: Múltiples coils específicas (ej: [100, 101, 102])
                SLAVE_UNIT: ID del dispositivo esclavo (ej: 1)
            """
            result = self.modbus_tool.read_modbus_coil(
                HOST, PORT, COIL_ADDRESSES, SLAVE_UNIT
            )
            return json.dumps(result, indent=2, ensure_ascii=False)

        @tool("read_modbus_holding_registers")
        def read_holding_registers_tool(
            HOST: str, PORT: int, ADDRESSES, SLAVE_UNIT: int
        ) -> str:
            """
            Lee valores de uno o múltiples registros de holding (configuraciones) de un dispositivo Modbus TCP.

            Args:
                HOST: Dirección IP del dispositivo Modbus TCP (ej: '192.168.1.10')
                PORT: Puerto TCP (típicamente 502)
                ADDRESSES: Puede ser:
                    - int: Un solo registro (ej: 100)
                    - List[int]: Múltiples registros específicos (ej: [100, 101, 102])
                SLAVE_UNIT: ID del dispositivo esclavo (ej: 1)
            """
            result = self.modbus_tool.read_modbus_holding_registers(
                HOST, PORT, ADDRESSES, SLAVE_UNIT
            )
            return json.dumps(result, indent=2, ensure_ascii=False)

        @tool("read_modbus_input_registers")
        def read_input_registers_tool(
            HOST: str, PORT: int, ADDRESSES, SLAVE_UNIT: int
        ) -> str:
            """
            Lee valores de uno o múltiples registros de entrada (sensores) de un dispositivo Modbus TCP.

            Args:
                HOST: Dirección IP del dispositivo Modbus TCP (ej: '192.168.1.10')
                PORT: Puerto TCP (típicamente 502)
                ADDRESSES: Puede ser:
                    - int: Un solo registro (ej: 100)
                    - List[int]: Múltiples registros específicos (ej: [100, 101, 102])
                SLAVE_UNIT: ID del dispositivo esclavo (ej: 1)
            """
            result = self.modbus_tool.read_modbus_input_registers(
                HOST, PORT, ADDRESSES, SLAVE_UNIT
            )
            return json.dumps(result, indent=2, ensure_ascii=False)

        return [
            write_coil_tool,
            read_coil_tool,
            read_holding_registers_tool,
            read_input_registers_tool,
        ]

    def _history_to_str(self, history):
        """Convierte el historial a string"""
        if not history:
            return ""
        # Limita el historial a los últimos 10 mensajes
        history = history[-10:]
        return "\n".join([f"{h['role']}: {h['message']}" for h in history])

    def _needs_modbus_operation(self, query: str) -> bool:
        """Determina si la consulta requiere una operación Modbus"""
        modbus_keywords = [
            "modbus",
            "coil",
            "register",
            "holding",
            "input",
            "esclavo",
            "slave",
            "192.168",
            "502",
            "tcp",
            "leer",
            "escribir",
            "estado",
            "encender",
            "apagar",
            "bomba",
            "válvula",
            "sensor",
            "temperatura",
            "presión",
        ]

        query_lower = query.lower()
        return any(keyword in query_lower for keyword in modbus_keywords)

    def run(self, query: str, history=None, user_id=None):
        """Método principal para procesar consultas Modbus"""
        logger.info(f"🚀 Procesando consulta Modbus: '{query[:50]}...'")

        # Verificar si la consulta requiere operación Modbus
        needs_modbus = self._needs_modbus_operation(query)

        if needs_modbus:
            logger.info(f"🔧 Activando herramientas Modbus")
            return self._run_with_tools(query, history, user_id)
        else:
            logger.info(f"💬 Respondiendo con conocimiento general sobre Modbus")
            return self._run_general_response(query, history, user_id)

    def _run_with_tools(self, query: str, history=None, user_id=None):
        """Ejecuta el agente con herramientas Modbus"""
        try:
            from langchain_core.messages import HumanMessage

            # Preparar prompt con contexto
            history_str = self._history_to_str(history)
            prompt = self.prompt

            if history_str:
                prompt += f"\nHistorial reciente:\n{history_str}"
            prompt += f"\nUsuario: {query}"

            # Configurar LLM con herramientas
            llm_with_tools = self.llm.bind_tools(self.tools)

            # Crear mensaje
            message = HumanMessage(content=prompt)

            # Invocar LLM con herramientas
            response = llm_with_tools.invoke([message])

            # Verificar si el LLM quiere usar herramientas
            if hasattr(response, "tool_calls") and response.tool_calls:
                logger.info(
                    f"🔧 LLM decidió usar herramientas: {len(response.tool_calls)}"
                )
                return self._execute_tool_calls(response, query)
            else:
                # Respuesta directa del LLM
                content = getattr(response, "content", "")
                if not content or not content.strip():
                    content = "No pude procesar tu consulta. Por favor, proporciona más detalles sobre la operación Modbus que necesitas."

                logger.info(f"✅ Respuesta directa generada")
                return content

        except Exception as e:
            logger.error(f"❌ Error en ejecución con herramientas: {e}")
            return f"Error al procesar la consulta Modbus: {str(e)}"

    def _run_general_response(self, query: str, history=None, user_id=None):
        """Ejecuta respuesta general sin herramientas"""
        try:
            from langchain_core.messages import HumanMessage

            history_str = self._history_to_str(history)
            prompt = self.prompt

            if history_str:
                prompt += f"\nHistorial reciente:\n{history_str}"
            prompt += f"\nUsuario: {query}"

            message = HumanMessage(content=prompt)
            response = self.llm.invoke([message])

            content = getattr(response, "content", "")
            if not content or not content.strip():
                content = "No pude generar una respuesta. Por favor, reformula tu pregunta sobre Modbus."

            logger.info(f"✅ Respuesta general generada")
            return content

        except Exception as e:
            logger.error(f"❌ Error en respuesta general: {e}")
            return f"Error al procesar la consulta: {str(e)}"

    def _execute_tool_calls(self, response, original_query):
        """Ejecuta las llamadas a herramientas del LLM"""
        try:
            tool_results = []

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                logger.info(
                    f"🔧 Ejecutando herramienta: {tool_name} con args: {tool_args}"
                )

                # Ejecutar la herramienta correspondiente
                if tool_name == "write_modbus_coil":
                    result = self.modbus_tool.write_modbus_coil(**tool_args)
                elif tool_name == "read_modbus_coil":
                    result = self.modbus_tool.read_modbus_coil(**tool_args)
                elif tool_name == "read_modbus_holding_registers":
                    result = self.modbus_tool.read_modbus_holding_registers(**tool_args)
                elif tool_name == "read_modbus_input_registers":
                    result = self.modbus_tool.read_modbus_input_registers(**tool_args)
                else:
                    result = {"error": f"Herramienta '{tool_name}' no encontrada"}

                tool_results.append({"tool_name": tool_name, "result": result})

                logger.info(f"✅ Herramienta {tool_name} ejecutada")

            # Generar respuesta final con los resultados
            return self._generate_final_response(original_query, tool_results)

        except Exception as e:
            logger.error(f"❌ Error ejecutando herramientas: {e}")
            return f"Error al ejecutar las operaciones Modbus: {str(e)}"

    def _generate_final_response(self, query, tool_results):
        """Genera una respuesta final basada en los resultados de las herramientas"""
        try:
            from langchain_core.messages import HumanMessage

            # Preparar contexto con resultados
            results_context = "\n--- RESULTADOS DE OPERACIONES MODBUS ---\n"
            for i, tool_result in enumerate(tool_results, 1):
                tool_name = tool_result["tool_name"]
                result = tool_result["result"]
                results_context += f"\n{i}. Herramienta: {tool_name}\n"
                results_context += (
                    f"Resultado: {json.dumps(result, indent=2, ensure_ascii=False)}\n"
                )

            final_prompt = f"""
                            {self.prompt}

                            Consulta original: {query}

                            {results_context}

                            Analiza los resultados de las operaciones Modbus y proporciona una respuesta clara y útil al usuario.
                            Explica qué significan los resultados y cualquier acción recomendada.
                            Si hay errores, explica las posibles causas y soluciones.
                            Mantén un tono técnico pero accesible.
            """

            message = HumanMessage(content=final_prompt)
            response = self.llm.invoke([message])

            content = getattr(response, "content", "")
            if not content or not content.strip():
                content = "Operaciones Modbus completadas. Consulta los resultados técnicos arriba."

            logger.info(
                f"✅ Respuesta final generada con {len(tool_results)} herramientas"
            )
            return content

        except Exception as e:
            logger.error(f"❌ Error generando respuesta final: {e}")
            return f"Operaciones completadas pero error al generar respuesta final: {str(e)}"
