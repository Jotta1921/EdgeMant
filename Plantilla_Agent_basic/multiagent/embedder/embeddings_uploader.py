"""
Embeddings Uploader para MongoDB Vector Store
=============================================

Este módulo se encarga de cargar los embeddings generados desde archivos JSON
hacia MongoDB Atlas Vector Store para realizar búsquedas de similitud.

Configuración Atlas:
- Database: agent_memory_plantilla  
- Collection: vectorStore
- Vector Index: vector_index (768 dimensions, cosine similarity)

Autor: EdgeMant System
"""

import json
import os
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
from datetime import datetime
import logging
from config import MONGO_URI

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingsUploader:
    """
    Gestor de carga de embeddings a MongoDB Atlas Vector Store
    """
    
    def __init__(self):
        """Inicializar conexión a MongoDB Atlas"""
        self.mongo_uri = MONGO_URI
        self.db_name = "agent_memory_plantilla"
        self.collection_name = "vectorStore"
        self.vector_index_name = "vector_index"
        
        # Establecer conexión
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.db_name]
        self.collection: Collection = self.db[self.collection_name]
        
        # Verificar conexión
        self._verify_connection()
        
        # Directorio de embeddings
        self.embeddings_dir = os.path.join(
            os.path.dirname(__file__), 
            "knowledge", 
            "embeddings"
        )
    
    def _verify_connection(self) -> None:
        """Verificar conexión a MongoDB Atlas"""
        try:
            self.client.admin.command('ping')
            logger.info("✅ Conexión exitosa a MongoDB Atlas")
            
            # Verificar database y collection
            db_list = self.client.list_database_names()
            if self.db_name not in db_list:
                logger.warning(f"⚠️ Database '{self.db_name}' no encontrada")
            else:
                logger.info(f"✅ Database '{self.db_name}' encontrada")
                
            collection_list = self.db.list_collection_names()
            if self.collection_name not in collection_list:
                logger.warning(f"⚠️ Collection '{self.collection_name}' no encontrada")
            else:
                logger.info(f"✅ Collection '{self.collection_name}' encontrada")
                
                # Verificar índice vector
                indexes = list(self.collection.list_indexes())
                vector_index_exists = any(
                    idx.get('name') == self.vector_index_name for idx in indexes
                )
                if vector_index_exists:
                    logger.info(f"✅ Vector index '{self.vector_index_name}' encontrado")
                else:
                    logger.warning(f"⚠️ Vector index '{self.vector_index_name}' no encontrado")
                    
        except Exception as e:
            logger.error(f"❌ Error conectando a MongoDB Atlas: {e}")
            raise
    
    def _load_embeddings_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Cargar embeddings desde archivo JSON
        
        Args:
            file_path: Ruta al archivo de embeddings
            
        Returns:
            Lista de documentos con embeddings
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Los archivos pueden ser un array directo o un objeto con clave 'embeddings'
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'embeddings' in data:
                return data['embeddings']
            else:
                logger.error(f"❌ Formato incorrecto en {file_path}: se esperaba array o objeto con 'embeddings'")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error cargando {file_path}: {e}")
            return []
    
    def _prepare_document(self, embedding_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preparar documento para inserción en MongoDB
        
        Args:
            embedding_data: Datos del embedding desde JSON
            
        Returns:
            Documento formateado para MongoDB
        """
        # Los archivos usan 'id' en lugar de 'chunk_id'
        chunk_id = embedding_data.get('id', embedding_data.get('chunk_id', ''))
        
        # Preparar documento MongoDB
        document = {
            # Campos de contenido
            'text': embedding_data.get('text', ''),
            'embedding': embedding_data.get('embedding', []),
            
            # Campos de identificación
            'chunk_id': chunk_id,
            'source': self._extract_source_from_id(chunk_id),
            
            # Campos de procesamiento
            'embedding_model': 'text-embedding-004',
            'embedding_dimensions': len(embedding_data.get('embedding', [])),
            'processing_timestamp': datetime.utcnow(),
            
            # Datos originales preservados
            'original_id': chunk_id
        }
        
        return document
    
    def _extract_source_from_id(self, chunk_id: str) -> str:
        """
        Extraer nombre del manual desde el chunk_id
        
        Args:
            chunk_id: ID del chunk (ej: "e9256bcc_chunk_000")
            
        Returns:
            Nombre del manual inferido
        """
        # Los IDs siguen el patrón: hash_chunk_number
        # Podemos inferir el source del nombre del archivo que estamos procesando
        if hasattr(self, '_current_file_source'):
            return self._current_file_source
        
        # Fallback: extraer del chunk_id si es posible
        if '_chunk_' in chunk_id:
            base_id = chunk_id.split('_chunk_')[0]
            return f"manual_{base_id}.pdf"
        
        return "unknown_manual.pdf"
    
    def _check_document_exists(self, chunk_id: str) -> bool:
        """
        Verificar si un documento ya existe en la collection
        
        Args:
            chunk_id: ID único del chunk
            
        Returns:
            True si existe, False si no
        """
        return self.collection.count_documents({'chunk_id': chunk_id}) > 0
    
    def upload_embeddings_file(self, filename: str) -> Dict[str, Any]:
        """
        Subir embeddings de un archivo específico
        
        Args:
            filename: Nombre del archivo de embeddings
            
        Returns:
            Resumen de la operación
        """
        file_path = os.path.join(self.embeddings_dir, filename)
        
        if not os.path.exists(file_path):
            logger.error(f"❌ Archivo no encontrado: {file_path}")
            return {'success': False, 'error': 'Archivo no encontrado'}
        
        logger.info(f"📤 Cargando embeddings desde: {filename}")
        
        # Inferir source del nombre del archivo
        source_name = filename.replace('_chunks_embeddings.json', '.pdf')
        self._current_file_source = source_name
        
        # Cargar embeddings
        embeddings_data = self._load_embeddings_file(file_path)
        
        if not embeddings_data:
            logger.error(f"❌ No se pudieron cargar embeddings de {filename}")
            return {'success': False, 'error': 'No se pudieron cargar embeddings'}
        
        logger.info(f"🔍 Encontrados {len(embeddings_data)} embeddings en {filename}")
        
        # Procesar embeddings
        documents_to_insert = []
        duplicates_found = 0
        
        for embedding_data in embeddings_data:
            chunk_id = embedding_data.get('id', embedding_data.get('chunk_id', ''))
            
            # Verificar duplicados
            if self._check_document_exists(chunk_id):
                duplicates_found += 1
                logger.debug(f"🔄 Chunk duplicado saltado: {chunk_id}")
                continue
            
            # Preparar documento
            document = self._prepare_document(embedding_data)
            documents_to_insert.append(document)
        
        # Insertar documentos
        inserted_count = 0
        if documents_to_insert:
            try:
                result = self.collection.insert_many(documents_to_insert)
                inserted_count = len(result.inserted_ids)
                logger.info(f"✅ Insertados {inserted_count} documentos de {filename}")
                
            except Exception as e:
                logger.error(f"❌ Error insertando documentos: {e}")
                return {
                    'success': False, 
                    'error': f'Error en inserción: {e}',
                    'processed': len(embeddings_data),
                    'duplicates': duplicates_found
                }
        
        # Resumen de operación
        summary = {
            'success': True,
            'filename': filename,
            'total_embeddings': len(embeddings_data),
            'inserted': inserted_count,
            'duplicates_skipped': duplicates_found,
            'processing_time': datetime.utcnow().isoformat()
        }
        
        logger.info(f"📊 Resumen {filename}: {inserted_count} insertados, {duplicates_found} duplicados")
        return summary
    
    def upload_all_embeddings(self) -> Dict[str, Any]:
        """
        Subir todos los archivos de embeddings disponibles
        
        Returns:
            Resumen completo de la operación
        """
        logger.info("🚀 Iniciando carga completa de embeddings a MongoDB Atlas")
        
        # Buscar archivos de embeddings
        embedding_files = [
            f for f in os.listdir(self.embeddings_dir) 
            if f.endswith('_embeddings.json')
        ]
        
        if not embedding_files:
            logger.error("❌ No se encontraron archivos de embeddings")
            return {'success': False, 'error': 'No hay archivos de embeddings'}
        
        logger.info(f"📁 Encontrados {len(embedding_files)} archivos de embeddings")
        
        # Procesar cada archivo
        file_results = []
        total_inserted = 0
        total_duplicates = 0
        total_processed = 0
        
        for filename in sorted(embedding_files):
            logger.info(f"📤 Procesando: {filename}")
            result = self.upload_embeddings_file(filename)
            
            file_results.append(result)
            
            if result['success']:
                total_inserted += result['inserted']
                total_duplicates += result['duplicates_skipped']
                total_processed += result['total_embeddings']
        
        # Resumen final
        final_summary = {
            'success': True,
            'total_files_processed': len(embedding_files),
            'total_embeddings_processed': total_processed,
            'total_inserted': total_inserted,
            'total_duplicates_skipped': total_duplicates,
            'file_results': file_results,
            'vector_store_info': {
                'database': self.db_name,
                'collection': self.collection_name,
                'vector_index': self.vector_index_name
            },
            'completion_time': datetime.utcnow().isoformat()
        }
        
        logger.info("🎯 ¡Carga de embeddings completada!")
        logger.info(f"📊 Resumen Final: {total_inserted} documentos insertados, {total_duplicates} duplicados")
        
        return final_summary
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de la collection
        
        Returns:
            Estadísticas de la vector store
        """
        try:
            # Contar documentos
            total_docs = self.collection.count_documents({})
            
            # Obtener sample de documento para verificar estructura
            sample_doc = self.collection.find_one({}, {'_id': 0, 'text': 1, 'source': 1, 'embedding_dimensions': 1})
            
            # Estadísticas por fuente
            pipeline = [
                {'$group': {
                    '_id': '$source',
                    'count': {'$sum': 1}
                }},
                {'$sort': {'count': -1}}
            ]
            
            source_stats = list(self.collection.aggregate(pipeline))
            
            stats = {
                'total_documents': total_docs,
                'documents_by_source': source_stats,
                'sample_document': sample_doc,
                'collection_info': {
                    'database': self.db_name,
                    'collection': self.collection_name,
                    'vector_index': self.vector_index_name
                }
            }
            
            logger.info(f"📊 Vector Store Stats: {total_docs} documentos totales")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {'error': str(e)}
    
    def close_connection(self):
        """Cerrar conexión a MongoDB"""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("🔌 Conexión a MongoDB cerrada")


def main():
    """Función principal para ejecutar la carga de embeddings"""
    try:
        # Crear uploader
        uploader = EmbeddingsUploader()
        
        # Verificar estado actual
        logger.info("📊 Verificando estado actual del Vector Store...")
        current_stats = uploader.get_collection_stats()
        print(f"\n📈 Estado actual: {current_stats.get('total_documents', 0)} documentos")
        
        # Cargar todos los embeddings
        logger.info("\n🚀 Iniciando carga de embeddings...")
        result = uploader.upload_all_embeddings()
        
        if result['success']:
            print(f"\n✅ ¡Carga exitosa!")
            print(f"📁 Archivos procesados: {result['total_files_processed']}")
            print(f"📤 Embeddings insertados: {result['total_inserted']}")
            print(f"🔄 Duplicados saltados: {result['total_duplicates_skipped']}")
            
            # Estadísticas finales
            final_stats = uploader.get_collection_stats()
            print(f"📊 Total documentos en Vector Store: {final_stats.get('total_documents', 0)}")
            
        else:
            print(f"\n❌ Error en la carga: {result.get('error', 'Error desconocido')}")
            
    except Exception as e:
        logger.error(f"❌ Error crítico: {e}")
        print(f"\n💥 Error crítico: {e}")
        
    finally:
        if 'uploader' in locals():
            uploader.close_connection()


if __name__ == "__main__":
    main()