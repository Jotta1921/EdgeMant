"""
Procesador especializado Chunks → Embeddings
Convierte chunks de texto en embeddings y los guarda en archivos JSON
CON PROTECCIÓN ANTI-DUPLICADOS para ahorrar dinero
NO sube a base de datos (eso va en otro archivo)
"""

import os
import json
from typing import List, Dict, Optional
from pathlib import Path
import sys

# Agregar el directorio padre al path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
except ImportError:
    print("❌ Dependencias faltantes. Instala: pip install langchain-google-genai")
    exit(1)

class ChunksToEmbeddingsProcessor:
    """
    Procesador que convierte Chunks → Embeddings
    - Lee chunks de texto (JSON)
    - Genera embeddings SOLO si no existen (ahorro de costos)
    - Los guarda en archivos JSON (NO sube a base de datos)
    """
    
    def __init__(self, 
                 google_api_key: str,
                 chunks_folder: str,
                 embeddings_output_folder: str):
        
        self.chunks_folder = Path(chunks_folder)
        self.embeddings_output_folder = Path(embeddings_output_folder)
        self.google_api_key = google_api_key
        
        # Crear carpeta de salida si no existe
        self.embeddings_output_folder.mkdir(exist_ok=True, parents=True)
        
        # Inicializar embeddings de Gemini
        print("🔧 Inicializando generador de embeddings...")
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",  # 768 dimensiones
            google_api_key=google_api_key
        )
        
        print(f"� Carpeta chunks entrada: {self.chunks_folder}")
        print(f"📁 Carpeta embeddings salida: {self.embeddings_output_folder}")
        print("� Los embeddings se guardan como archivos JSON (no en base de datos)")
    
    def check_existing_embeddings(self) -> Dict[str, int]:
        """Verifica qué embeddings ya existen en archivos para evitar duplicados"""
        print("🔍 Verificando embeddings existentes para evitar duplicados...")
        
        if not self.chunks_folder.exists():
            print(f"❌ Carpeta {self.chunks_folder} no existe")
            return {}
        
        report = {
            "total_files": 0,
            "total_chunks": 0,
            "existing_embeddings": 0,
            "missing_embeddings": 0,
            "files": {}
        }
        
        chunk_files = list(self.chunks_folder.glob("*_chunks.json"))
        if not chunk_files:
            print(f"❌ No se encontraron archivos *_chunks.json en {self.chunks_folder}")
            return report
        
        report["total_files"] = len(chunk_files)
        
        for json_file in chunk_files:
            try:
                # Nombre del archivo de embeddings correspondiente
                embeddings_file = self.embeddings_output_folder / f"{json_file.stem}_embeddings.json"
                
                with open(json_file, 'r', encoding='utf-8') as f:
                    chunks_data = json.load(f)
                
                existing = 0
                missing = 0
                
                if embeddings_file.exists():
                    # Cargar embeddings existentes
                    with open(embeddings_file, 'r', encoding='utf-8') as f:
                        existing_embeddings = json.load(f)
                    
                    # Verificar qué chunks ya tienen embeddings
                    existing_chunk_ids = {emb["id"] for emb in existing_embeddings}
                    
                    for chunk in chunks_data:
                        if chunk["id"] in existing_chunk_ids:
                            existing += 1
                        else:
                            missing += 1
                else:
                    # No existe archivo de embeddings, todos faltan
                    missing = len(chunks_data)
                
                report["files"][json_file.name] = {
                    "total": len(chunks_data),
                    "existing": existing,
                    "missing": missing,
                    "embeddings_file": embeddings_file.name
                }
                
                report["total_chunks"] += len(chunks_data)
                report["existing_embeddings"] += existing
                report["missing_embeddings"] += missing
                
                status = "✅ Completo" if missing == 0 else f"⚠️ {missing} faltantes"
                print(f"📄 {json_file.name}: {existing}/{len(chunks_data)} - {status}")
                
            except Exception as e:
                print(f"❌ Error verificando {json_file.name}: {e}")
        
        return report
    
    def generate_embeddings_for_missing_chunks(self) -> Dict[str, int]:
        """Genera embeddings SOLO para chunks que no existen y los guarda en archivos JSON"""
        
        if not self.chunks_folder.exists():
            print(f"❌ Carpeta {self.chunks_folder} no existe")
            return {"error": "Carpeta no existe"}
        
        chunk_files = list(self.chunks_folder.glob("*_chunks.json"))
        if not chunk_files:
            print(f"❌ No se encontraron archivos de chunks")
            return {"error": "No hay archivos de chunks"}
        
        stats = {
            "processed_files": 0,
            "total_chunks": 0,
            "new_embeddings": 0,
            "skipped_chunks": 0,
            "errors": 0
        }
        
        print(f"📊 Procesando {len(chunk_files)} archivos de chunks...")
        
        for json_file in chunk_files:
            try:
                # Archivo de embeddings correspondiente
                embeddings_file = self.embeddings_output_folder / f"{json_file.stem}_embeddings.json"
                
                with open(json_file, 'r', encoding='utf-8') as f:
                    chunks_data = json.load(f)
                
                print(f"\n📄 Procesando {json_file.name}: {len(chunks_data)} chunks")
                
                # Cargar embeddings existentes si existen
                existing_embeddings = []
                existing_chunk_ids = set()
                
                if embeddings_file.exists():
                    with open(embeddings_file, 'r', encoding='utf-8') as f:
                        existing_embeddings = json.load(f)
                    existing_chunk_ids = {emb["id"] for emb in existing_embeddings}
                
                new_embeddings_for_file = []
                
                for i, chunk in enumerate(chunks_data, 1):
                    # VERIFICAR SI YA EXISTE (CRÍTICO PARA AHORRO)
                    if chunk["id"] in existing_chunk_ids:
                        # Ya existe, saltar (AHORRO DE DINERO)
                        stats["skipped_chunks"] += 1
                        continue
                    
                    # NO EXISTE: Generar embedding (AQUÍ SE COBRA)
                    try:
                        print(f"💰 Generando embedding {i}/{len(chunks_data)}: {chunk['id']}")
                        embedding = self.embeddings.embed_query(chunk["text"])
                        
                        # Crear documento con embedding
                        embedding_doc = {
                            "id": chunk["id"],
                            "text": chunk["text"],
                            "embedding": embedding,
                            "metadata": chunk["metadata"]
                        }
                        
                        new_embeddings_for_file.append(embedding_doc)
                        stats["new_embeddings"] += 1
                        
                        print(f"✅ Embedding generado")
                        
                    except Exception as e:
                        print(f"❌ Error generando embedding: {e}")
                        stats["errors"] += 1
                
                # Combinar embeddings existentes con nuevos y guardar
                if new_embeddings_for_file:
                    all_embeddings = existing_embeddings + new_embeddings_for_file
                    
                    with open(embeddings_file, 'w', encoding='utf-8') as f:
                        json.dump(all_embeddings, f, ensure_ascii=False, indent=2)
                    
                    print(f"💾 Guardados {len(new_embeddings_for_file)} nuevos embeddings en {embeddings_file.name}")
                
                stats["processed_files"] += 1
                stats["total_chunks"] += len(chunks_data)
                
                print(f"✅ {json_file.name} completado")
                
            except Exception as e:
                print(f"❌ Error procesando {json_file.name}: {e}")
                stats["errors"] += 1
        
        return stats
    

def main():
    """Función principal - Solo chunks → embeddings (guardados en archivos JSON)"""
    print("🚀 GENERADOR DE EMBEDDINGS DESDE CHUNKS")
    print("="*50)
    print("Este proceso genera embeddings (COSTO) y los guarda en archivos JSON")
    print("CON PROTECCIÓN ANTI-DUPLICADOS para ahorrar dinero")
    print("💾 NO sube a MongoDB - solo genera archivos con embeddings")
    print()
    
    # Cargar configuración
    try:
        sys.path.append(str(Path(__file__).parent.parent.parent))
        from config import GEMINI_API_KEY
        google_api_key = GEMINI_API_KEY
    except Exception as e:
        print(f"❌ Error cargando configuración: {e}")
        print("Asegúrate de tener configurada la API key en config.py:")
        print("- GEMINI_API_KEY")
        return
    
    # Rutas (estructura actualizada)
    current_dir = Path(__file__).parent
    chunks_folder = current_dir / "knowledge" / "knowledge_chunks"
    embeddings_folder = current_dir / "knowledge" / "embeddings"
    
    # Crear procesador
    try:
        processor = ChunksToEmbeddingsProcessor(
            google_api_key=google_api_key,
            chunks_folder=str(chunks_folder),
            embeddings_output_folder=str(embeddings_folder)
        )
        
        # PASO 1: Verificar qué ya existe (GRATIS)
        print("\n🔍 VERIFICANDO ARCHIVOS DE EMBEDDINGS EXISTENTES (sin costo)...")
        check_report = processor.check_existing_embeddings()
        
        if check_report["missing_embeddings"] == 0:
            print("\n🎉 ¡TODOS LOS CHUNKS YA TIENEN EMBEDDINGS!")
            print("💰 No se generarán embeddings nuevos (AHORRO TOTAL)")
            print(f"💾 Embeddings disponibles en: {processor.embeddings_output_folder}")
            
            print(f"\n📊 ESTADÍSTICAS ACTUALES:")
            print(f"   • Total chunks: {check_report['total_chunks']}")
            print(f"   • Archivos con embeddings: {check_report['existing_files']}")
            
            return
        
        # Hay chunks faltantes
        print(f"\n💰 RESUMEN DE COSTOS:")
        print(f"   • Total chunks: {check_report['total_chunks']}")
        print(f"   • ✅ Ya tienen embeddings: {check_report['existing_embeddings']} (gratis)")
        print(f"   • 💰 A generar: {check_report['missing_embeddings']} (costo embeddings)")
        print(f"   • 📊 Archivos de chunks: {check_report['total_files']}")
        
        # Confirmación del usuario
        print(f"\n⚠️  SE GENERARÁN {check_report['missing_embeddings']} EMBEDDINGS NUEVOS")
        print("💾 Los embeddings se guardarán en archivos JSON locales")
        confirm = input("¿Continuar? (s/n): ").lower().strip()
        
        if confirm != 's':
            print("❌ Operación cancelada por el usuario")
            return
        
        # PASO 2: Generar embeddings faltantes (COSTO)
        print(f"\n💰 GENERANDO EMBEDDINGS (esto tiene costo)...")
        results = processor.generate_embeddings_for_missing_chunks()
        
        if "error" in results:
            print(f"❌ Error: {results['error']}")
            return
        
        # PASO 3: Estadísticas finales
        print(f"\n🎉 ¡PROCESO COMPLETADO!")
        print(f"📊 RESUMEN FINAL:")
        print(f"   • Archivos procesados: {results['processed_files']}")
        print(f"   • Total chunks: {results['total_chunks']}")
        print(f"   • 🆕 Nuevos embeddings: {results['new_embeddings']}")
        print(f"   • ⏭️  Saltados (existían): {results['skipped_chunks']}")
        print(f"   • ❌ Errores: {results['errors']}")
        print(f"   • 💰 Costo: {results['new_embeddings']} embeddings generados")
        
        print(f"\n� ARCHIVOS DE EMBEDDINGS GENERADOS:")
        print(f"   • Ubicación: {processor.embeddings_output_folder}")
        print(f"   • Formato: *_embeddings.json")
        
        print(f"\n✅ Embeddings listos para subir a vector store!")
        print(f"💡 Próximo paso: usar un procesador separado para subir a MongoDB")
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()