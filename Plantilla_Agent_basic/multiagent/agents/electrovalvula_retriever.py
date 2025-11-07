"""
Electroválvula Retriever Agent
=============================

Agente LangGraph especializado en recuperar información relevante sobre electroválvulas
desde el Vector Store de MongoDB Atlas usando búsqueda semántica.

Este agente:
1. Recibe consultas en lenguaje natural sobre electroválvulas
2. Genera embeddings de la consulta
3. Realiza búsqueda de similitud en MongoDB Atlas Vector Store
4. Devuelve los chunks más relevantes con contexto

Autor: EdgeMant System
"""

import os
from typing import List, Dict, Any, Optional, TypedDict
from pymongo import MongoClient
from pymongo.collection import Collection
import logging
from datetime import datetime

# LangGraph y LangChain imports
from langgraph.graph import StateGraph, END
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.schema import Document

# Configuración local
from config import MONGO_URI, GEMINI_API_KEY

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RetrieverState(TypedDict):
    """Estado del agente retriever"""
    query: str
    query_embedding: Optional[List[float]]
    retrieved_documents: List[Document]
    search_results: List[Dict[str, Any]]
    similarity_threshold: float
    max_results: int
    error: Optional[str]

class ElectrovalvulaRetriever:
    """
    Agente retriever especializado en electroválvulas usando LangGraph
    """
    
    def __init__(self):
        """Inicializar retriever con conexiones a MongoDB y Gemini"""
        # Configuración MongoDB
        self.mongo_uri = MONGO_URI
        self.db_name = "agent_memory_plantilla"
        self.collection_name = "vectorStore"
        self.vector_index_name = "vector_index"
        
        # Configuración embeddings
        self.embeddings_model = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=GEMINI_API_KEY
        )
        
        # Conexión MongoDB
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.db_name]
        self.collection: Collection = self.db[self.collection_name]
        
        # Verificar conexión
        self._verify_setup()
        
        # Configurar LangGraph
        self.graph = self._create_graph()
    
    def _verify_setup(self) -> None:
        """Verificar conexiones y configuración"""
        try:
            # Verificar MongoDB
            self.client.admin.command('ping')
            doc_count = self.collection.count_documents({})
            logger.info(f"✅ MongoDB conectado: {doc_count} documentos en Vector Store")
            
            # Verificar embeddings model
            test_embedding = self.embeddings_model.embed_query("test")
            logger.info(f"✅ Gemini embeddings: {len(test_embedding)} dimensiones")
            
        except Exception as e:
            logger.error(f"❌ Error en setup: {e}")
            raise
    
    def _create_graph(self) -> StateGraph:
        """Crear el grafo LangGraph para el retriever"""
        workflow = StateGraph(RetrieverState)
        
        # Nodos del workflow
        workflow.add_node("generate_embedding", self._generate_query_embedding)
        workflow.add_node("vector_search", self._perform_vector_search)
        workflow.add_node("format_results", self._format_search_results)
        
        # Flujo del grafo
        workflow.set_entry_point("generate_embedding")
        workflow.add_edge("generate_embedding", "vector_search")
        workflow.add_edge("vector_search", "format_results")
        workflow.add_edge("format_results", END)
        
        return workflow.compile()
    
    def _generate_query_embedding(self, state: RetrieverState) -> RetrieverState:
        """
        Nodo: Generar embedding de la consulta
        """
        try:
            logger.info(f"🔍 Generando embedding para: '{state['query']}'")
            
            # Generar embedding de la consulta
            query_embedding = self.embeddings_model.embed_query(state["query"])
            
            state["query_embedding"] = query_embedding
            logger.info(f"✅ Embedding generado: {len(query_embedding)} dimensiones")
            
        except Exception as e:
            logger.error(f"❌ Error generando embedding: {e}")
            state["error"] = f"Error en embedding: {e}"
        
        return state
    
    def _perform_vector_search(self, state: RetrieverState) -> RetrieverState:
        """
        Nodo: Realizar búsqueda vectorial en MongoDB Atlas
        """
        if state.get("error") or not state.get("query_embedding"):
            return state
        
        try:
            logger.info("🔎 Realizando búsqueda vectorial...")
            
            # Pipeline de agregación para búsqueda vectorial
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": self.vector_index_name,
                        "path": "embedding",
                        "queryVector": state["query_embedding"],
                        "numCandidates": 100,
                        "limit": state.get("max_results", 10)
                    }
                },
                {
                    "$project": {
                        "text": 1,
                        "chunk_id": 1,
                        "source": 1,
                        "original_id": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]
            
            # Ejecutar búsqueda
            cursor = self.collection.aggregate(pipeline)
            search_results = list(cursor)
            
            # Filtrar por threshold si está definido
            threshold = state.get("similarity_threshold", 0.0)
            if threshold > 0:
                search_results = [
                    result for result in search_results 
                    if result.get("score", 0) >= threshold
                ]
            
            state["search_results"] = search_results
            logger.info(f"✅ Encontrados {len(search_results)} documentos relevantes")
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda vectorial: {e}")
            state["error"] = f"Error en búsqueda: {e}"
        
        return state
    
    def _format_search_results(self, state: RetrieverState) -> RetrieverState:
        """
        Nodo: Formatear resultados como documentos LangChain
        """
        if state.get("error") or not state.get("search_results"):
            state["retrieved_documents"] = []
            return state
        
        try:
            documents = []
            
            for result in state["search_results"]:
                # Crear documento LangChain
                doc = Document(
                    page_content=result.get("text", ""),
                    metadata={
                        "chunk_id": result.get("chunk_id", ""),
                        "source": result.get("source", ""),
                        "original_id": result.get("original_id", ""),
                        "similarity_score": result.get("score", 0.0),
                        "retrieval_timestamp": datetime.utcnow().isoformat()
                    }
                )
                documents.append(doc)
            
            state["retrieved_documents"] = documents
            logger.info(f"✅ Formateados {len(documents)} documentos")
            
        except Exception as e:
            logger.error(f"❌ Error formateando resultados: {e}")
            state["error"] = f"Error en formateo: {e}"
        
        return state
    
    def retrieve(
        self, 
        query: str, 
        max_results: int = 5,
        similarity_threshold: float = 0.0
    ) -> List[Document]:
        """
        Recuperar documentos relevantes para una consulta
        
        Args:
            query: Consulta en lenguaje natural
            max_results: Máximo número de resultados
            similarity_threshold: Umbral mínimo de similitud
            
        Returns:
            Lista de documentos LangChain con contexto relevante
        """
        logger.info(f"🚀 Iniciando retrieval para: '{query}'")
        
        # Estado inicial
        initial_state = RetrieverState(
            query=query,
            query_embedding=None,
            retrieved_documents=[],
            search_results=[],
            similarity_threshold=similarity_threshold,
            max_results=max_results,
            error=None
        )
        
        # Ejecutar grafo
        try:
            final_state = self.graph.invoke(initial_state)
            
            if final_state.get("error"):
                logger.error(f"❌ Error en retrieval: {final_state['error']}")
                return []
            
            documents = final_state.get("retrieved_documents", [])
            logger.info(f"🎯 Retrieval completado: {len(documents)} documentos")
            
            return documents
            
        except Exception as e:
            logger.error(f"❌ Error crítico en retrieval: {e}")
            return []
    
    def search_by_topic(self, topic: str, max_results: int = 3) -> List[Document]:
        """
        Búsqueda especializada por tema técnico
        
        Args:
            topic: Tema técnico (ej: "presión", "instalación", "mantenimiento")
            max_results: Número máximo de resultados
            
        Returns:
            Documentos más relevantes sobre el tema
        """
        # Expandir consulta con términos técnicos
        expanded_query = f"electroválvula {topic} funcionamiento operación"
        
        return self.retrieve(
            query=expanded_query,
            max_results=max_results,
            similarity_threshold=0.7
        )
    
    def get_installation_info(self) -> List[Document]:
        """Obtener información específica sobre instalación"""
        return self.search_by_topic("instalación montaje conexión", max_results=5)
    
    def get_maintenance_info(self) -> List[Document]:
        """Obtener información específica sobre mantenimiento"""
        return self.search_by_topic("mantenimiento limpieza servicio", max_results=5)
    
    def get_troubleshooting_info(self) -> List[Document]:
        """Obtener información sobre resolución de problemas"""
        return self.search_by_topic("problema error falla diagnóstico", max_results=5)
    
    def close_connection(self):
        """Cerrar conexión a MongoDB"""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("🔌 Conexión MongoDB cerrada")


def test_retriever():
    """Función de prueba del retriever"""
    print("🧪 PRUEBA DEL ELECTROVÁLVULA RETRIEVER")
    print("=" * 50)
    
    try:
        # Crear retriever
        retriever = ElectrovalvulaRetriever()
        
        # Pruebas de consultas
        test_queries = [
            "¿Cómo instalar una electroválvula?",
            "Problemas de presión en electroválvula",
            "Mantenimiento preventivo electroválvula",
            "Especificaciones técnicas ASCO",
            "Conexiones eléctricas Burkert"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n📋 Prueba {i}: {query}")
            print("-" * 40)
            
            documents = retriever.retrieve(query, max_results=3)
            
            if documents:
                print(f"✅ Encontrados {len(documents)} documentos:")
                for j, doc in enumerate(documents, 1):
                    score = doc.metadata.get('similarity_score', 0)
                    source = doc.metadata.get('source', 'N/A')
                    content_preview = doc.page_content[:100] + "..."
                    
                    print(f"  {j}. Score: {score:.3f} | Source: {source}")
                    print(f"     Content: {content_preview}")
            else:
                print("❌ No se encontraron documentos")
        
        # Estadísticas finales
        print(f"\n📊 Estado del Vector Store:")
        doc_count = retriever.collection.count_documents({})
        print(f"  Total documentos: {doc_count}")
        
        retriever.close_connection()
        print("\n🎯 ¡Pruebas completadas!")
        
    except Exception as e:
        print(f"❌ Error en pruebas: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_retriever()