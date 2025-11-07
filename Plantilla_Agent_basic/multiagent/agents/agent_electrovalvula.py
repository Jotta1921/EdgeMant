# Agente LLM especializado en electroválvulas usando Gemini 2.5 Flash
from langchain_google_genai import ChatGoogleGenerativeAI
from multiagent.prompt_templates.prompt_electrovalvula import PROMPT_TEMPLATE_ELECTROVALVULA
import logging

# Configurar logging
logger = logging.getLogger(__name__)

class AgentElectrovalvula:
    def __init__(self, api_key: str, memory_db=None):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.2,
            max_output_tokens=1536,
        )
        self.prompt = PROMPT_TEMPLATE_ELECTROVALVULA
        self.memory_db = memory_db

    def _history_to_str(self, history):
        if not history:
            return ""
        # Limita el historial a los últimos 10 mensajes
        history = history[-10:]
        return "\n".join([f"{h['role']}: {h['message']}" for h in history])

    def _needs_rag(self, query: str) -> bool:
        """El LLM decide cognitivamente si necesita RAG basado en la consulta"""
        decision_prompt = f"""
        Analiza si esta consulta sobre electroválvulas requiere información técnica específica:
        
        Consulta: "{query}"
        
        MANUALES DISPONIBLES: Solo tengo manuales técnicos de ASCO y BURKERT.
        
        Responde "SI" ÚNICAMENTE si la consulta requiere:
        - Especificaciones técnicas de ASCO o BURKERT (presión, voltaje, temperatura, modelos)
        - Procedimientos de instalación/mantenimiento de estas marcas
        - Resolución de problemas técnicos específicos de ASCO o BURKERT
        - Series/modelos específicos de estas marcas
        
        Responde "NO" si:
        - Menciona otras marcas (Emerson, Festo, SMC, etc.)
        - Es pregunta conceptual general sobre electroválvulas
        - Saludo o conversación casual
        - No requiere datos técnicos específicos de manuales
        
        IMPORTANTE: Tolera errores tipográficos en nombres de marcas (ej: "asco", "ASCO", "Asci", "burkert", "BURKERT", "Burket").
        
        Responde una sola palabra: SI o NO
        """
        
        try:
            from langchain_core.messages import HumanMessage
            decision = self.llm.invoke([HumanMessage(content=decision_prompt)])
            result = "SI" in decision.content.upper()
            logger.info(f"🧠 Decisión RAG para '{query[:50]}...': {'SI' if result else 'NO'}")
            return result
        except Exception as e:
            logger.warning(f"❌ Error en decisión RAG: {e}")
            return False

    def _get_context_from_rag(self, query: str) -> str:
        """Obtiene contexto relevante usando el retriever (LLM maneja errores tipográficos naturalmente)"""
        try:
            from multiagent.agents.electrovalvula_retriever import ElectrovalvulaRetriever
            
            # Crear retriever
            retriever = ElectrovalvulaRetriever()
            
            # Buscar documentos relevantes con parámetros optimizados
            logger.info(f"🔍 Buscando información para: '{query}'")
            documents = retriever.retrieve(query, max_results=8, similarity_threshold=0.55)
            
            # Formatear contexto para el LLM
            if documents:
                context = "\n--- INFORMACIÓN TÉCNICA RELEVANTE ---\n"
                for i, doc in enumerate(documents, 1):
                    source = doc.metadata.get('source', 'Manual')
                    score = doc.metadata.get('similarity_score', 0)
                    context += f"\n{i}. Fuente: {source} (Relevancia: {score:.2f})\n"
                    context += f"Contenido: {doc.page_content}\n"
                
                logger.info(f"✅ Contexto RAG obtenido: {len(documents)} documentos")
                return context
            else:
                logger.info(f"⚠️ No se encontraron documentos relevantes")
                return ""
                
        except Exception as e:
            logger.warning(f"❌ Error en RAG: {e}")
            return ""

    def run(self, query: str, history=None, user_id=None, image_bytes: bytes = None):
        """Método principal con RAG cognitivo y capacidades multimodales"""
        logger.info(f"🚀 Procesando consulta: '{query[:50]}...'")
        
        # 1. DECISIÓN COGNITIVA: ¿Necesito RAG?
        needs_retrieval = self._needs_rag(query)
        
        # 2. OBTENER CONTEXTO RAG si es necesario
        rag_context = ""
        if needs_retrieval:
            logger.info(f"📚 Activando RAG para obtener contexto técnico")
            rag_context = self._get_context_from_rag(query)
        else:
            logger.info(f"💭 Respondiendo con conocimiento general (sin RAG)")
        
        # 3. PREPARAR PROMPT (igual que antes + contexto RAG)
        history_str = self._history_to_str(history)
        prompt = self.prompt
        
        # Agregar contexto técnico si existe
        if rag_context:
            prompt += f"\n{rag_context}\n"
            prompt += "\nIMPORTANTE: Usa EXCLUSIVAMENTE la información técnica relevante proporcionada arriba para responder. Si la consulta es sobre especificaciones específicas (presión, voltaje, temperatura, modelo), extrae SOLO los datos exactos de la documentación. Si no encuentras la información específica en la documentación, indícalo claramente. SIEMPRE cita la fuente del manual.\n"
        
        if history_str:
            prompt += f"\nHistorial reciente:\n{history_str}"
        prompt += f"\nUsuario: {query}"
        
        # 4. PROCESAMIENTO MULTIMODAL ORIGINAL (SIN CAMBIOS)
        from langchain_core.messages import HumanMessage
        import base64

        if image_bytes:
            logger.info(f"🖼️ Procesando consulta con imagen")
            img_b64 = base64.b64encode(image_bytes).decode("utf-8")
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                    }
                ]
            )
            response = self.llm.invoke([message])
        else:
            logger.info(f"💬 Procesando consulta de texto")
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt}
                ]
            )
            response = self.llm.invoke([message])

        # 5. PROCESAR RESPUESTA (igual que antes)
        content = getattr(response, 'content', '')
        if not content or not content.strip():
            content = "[ERROR]: El LLM no devolvió contenido. Por favor, intenta reformular tu pregunta."
        
        logger.info(f"✅ Respuesta generada exitosamente")
        return content

    def run_with_info(self, query: str, history=None, user_id=None, image_bytes: bytes = None):
        """Método que devuelve información extendida incluyendo si se usó RAG"""
        logger.info(f"🚀 Procesando consulta con info extendida: '{query[:50]}...'")
        
        # 1. DECISIÓN COGNITIVA: ¿Necesito RAG?
        needs_retrieval = self._needs_rag(query)
        
        # 2. OBTENER CONTEXTO RAG si es necesario
        rag_context = ""
        if needs_retrieval:
            logger.info(f"📚 Activando RAG para obtener contexto técnico")
            rag_context = self._get_context_from_rag(query)
        else:
            logger.info(f"💭 Respondiendo con conocimiento general (sin RAG)")
        
        # 3. PREPARAR PROMPT (igual que antes + contexto RAG)
        history_str = self._history_to_str(history)
        prompt = self.prompt
        
        # Agregar contexto técnico si existe
        if rag_context:
            prompt += f"\n{rag_context}\n"
            prompt += "\nIMPORTANTE: Usa EXCLUSIVAMENTE la información técnica relevante proporcionada arriba para responder. Si la consulta es sobre especificaciones específicas (presión, voltaje, temperatura, modelo), extrae SOLO los datos exactos de la documentación. Si no encuentras la información específica en la documentación, indícalo claramente. SIEMPRE cita la fuente del manual.\n"
        
        if history_str:
            prompt += f"\nHistorial reciente:\n{history_str}"
        prompt += f"\nUsuario: {query}"
        
        # 4. PROCESAMIENTO MULTIMODAL ORIGINAL (SIN CAMBIOS)
        from langchain_core.messages import HumanMessage
        import base64

        if image_bytes:
            logger.info(f"🖼️ Procesando consulta con imagen")
            img_b64 = base64.b64encode(image_bytes).decode("utf-8")
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                    }
                ]
            )
            response = self.llm.invoke([message])
        else:
            logger.info(f"💬 Procesando consulta de texto")
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt}
                ]
            )
            response = self.llm.invoke([message])

        # 5. PROCESAR RESPUESTA con información extendida
        content = getattr(response, 'content', '')
        if not content or not content.strip():
            content = "[ERROR]: El LLM no devolvió contenido. Por favor, intenta reformular tu pregunta."
        
        logger.info(f"✅ Respuesta generada exitosamente - RAG: {'SI' if needs_retrieval and rag_context else 'NO'}")
        
        return {
            "response": content,
            "rag_activated": needs_retrieval and bool(rag_context)
        }