"""
PDF to Chunks Processor - Versión LangChain Estándar
Usando PyPDFLoader y RecursiveCharacterTextSplitter según mejores prácticas
"""

import os
import json
from typing import List, Dict, Optional
from pathlib import Path
import hashlib
import logging

# LangChain imports - estándar de la industria
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFToChunksProcessor:
    """
    Procesador que convierte PDFs → Chunks usando LangChain estándar
    Basado en mejores prácticas de LangGraph/LangChain
    """
    
    def __init__(self, input_folder: str, output_folder: str, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        
        # Crear carpeta de salida
        self.output_folder.mkdir(exist_ok=True, parents=True)
        
        # Text splitter con configuración optimizada
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True
        )
        
        logger.info(f"📁 Input: {self.input_folder}")
        logger.info(f"📁 Output: {self.output_folder}")
        logger.info(f"⚙️ Config: {chunk_size} chars, {chunk_overlap} overlap")
    
    def extract_text_from_pdf(self, pdf_path: Path) -> List[Document]:
        """Extrae texto usando PyPDFLoader de LangChain - MUY robusto"""
        try:
            logger.info(f"🔄 Procesando: {pdf_path.name}")
            
            # PyPDFLoader es MUY superior a PyPDF2 básico
            loader = PyPDFLoader(str(pdf_path))
            documents = loader.load()
            
            # Filtrar páginas vacías
            valid_docs = []
            for i, doc in enumerate(documents):
                content = doc.page_content.strip()
                if content and len(content) > 50:  # Mínimo 50 caracteres
                    # Agregar metadata de página
                    doc.metadata.update({
                        'source': pdf_path.name,
                        'page': i + 1,
                        'char_count': len(content)
                    })
                    valid_docs.append(doc)
            
            logger.info(f"✅ {pdf_path.name}: {len(valid_docs)} páginas válidas de {len(documents)} totales")
            return valid_docs
            
        except Exception as e:
            logger.error(f"❌ Error procesando {pdf_path.name}: {e}")
            return []
    
    def create_chunks_from_documents(self, documents: List[Document], source_file: str) -> List[Dict]:
        """Crea chunks usando el text splitter de LangChain"""
        if not documents:
            return []
        
        try:
            # Split documents - método estándar de LangChain
            chunks = self.text_splitter.split_documents(documents)
            
            # Convertir a formato de chunks con metadata enriquecido
            chunk_data = []
            for i, chunk in enumerate(chunks):
                # Verificar que el chunk tenga contenido sustancial
                content = chunk.page_content.strip()
                if len(content) < 50:  # Saltar chunks muy pequeños
                    continue
                
                # Generar ID único
                chunk_id = self.generate_chunk_id(source_file, i)
                
                # Crear metadata completo
                chunk_info = {
                    "id": chunk_id,
                    "text": content,
                    "metadata": {
                        "source": source_file,
                        "chunk_index": i,
                        "chunk_length": len(content),
                        "original_page": chunk.metadata.get('page', 0),
                        "document_type": "manual_electrovalvula",
                        "processing_method": "langchain_pypdf"
                    }
                }
                chunk_data.append(chunk_info)
            
            logger.info(f"📄 Creados {len(chunk_data)} chunks válidos de {len(chunks)} totales")
            return chunk_data
            
        except Exception as e:
            logger.error(f"❌ Error creando chunks: {e}")
            return []
    
    def generate_chunk_id(self, source_file: str, chunk_index: int) -> str:
        """Genera ID único para cada chunk"""
        source_hash = hashlib.md5(source_file.encode()).hexdigest()[:8]
        return f"{source_hash}_chunk_{chunk_index:03d}"
    
    def save_chunks(self, chunks: List[Dict], output_file: Path):
        """Guarda chunks en JSON"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ Guardados {len(chunks)} chunks en {output_file}")
        except Exception as e:
            logger.error(f"❌ Error guardando chunks: {e}")
    
    def process_single_pdf(self, pdf_path: Path) -> List[Dict]:
        """Procesa un PDF completo"""
        # Extraer documentos
        documents = self.extract_text_from_pdf(pdf_path)
        if not documents:
            logger.warning(f"⚠️ No se extrajo contenido de {pdf_path.name}")
            return []
        
        # Crear chunks
        chunks = self.create_chunks_from_documents(documents, pdf_path.name)
        
        # Guardar
        output_file = self.output_folder / f"{pdf_path.stem}_chunks.json"
        self.save_chunks(chunks, output_file)
        
        return chunks
    
    def process_all_pdfs(self) -> Dict[str, List[Dict]]:
        """Procesa todos los PDFs"""
        all_chunks = {}
        
        pdf_files = list(self.input_folder.glob("*.pdf"))
        if not pdf_files:
            logger.error(f"❌ No PDFs encontrados en {self.input_folder}")
            return all_chunks
        
        logger.info(f"📚 Procesando {len(pdf_files)} archivos PDF")
        print("=" * 60)
        
        for pdf_file in pdf_files:
            chunks = self.process_single_pdf(pdf_file)
            if chunks:
                all_chunks[pdf_file.name] = chunks
                logger.info(f"✅ {pdf_file.name}: {len(chunks)} chunks")
            else:
                logger.warning(f"⚠️ {pdf_file.name}: Sin chunks válidos")
        
        # Resumen
        self.save_processing_summary(all_chunks)
        return all_chunks
    
    def save_processing_summary(self, all_chunks: Dict[str, List[Dict]]):
        """Guarda resumen del procesamiento"""
        summary = {
            "processing_method": "langchain_pypdf",
            "total_documents": len(all_chunks),
            "total_chunks": sum(len(chunks) for chunks in all_chunks.values()),
            "chunk_config": {
                "chunk_size": self.text_splitter._chunk_size,
                "chunk_overlap": self.text_splitter._chunk_overlap,
                "separators": self.text_splitter._separators
            },
            "documents": {}
        }
        
        for doc_name, chunks in all_chunks.items():
            summary["documents"][doc_name] = {
                "chunks_count": len(chunks),
                "total_characters": sum(len(chunk["text"]) for chunk in chunks),
                "avg_chunk_size": sum(len(chunk["text"]) for chunk in chunks) // len(chunks) if chunks else 0
            }
        
        summary_file = self.output_folder / "processing_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📊 Resumen: {summary['total_documents']} docs, {summary['total_chunks']} chunks")
        logger.info(f"📋 Guardado en: {summary_file}")


def main():
    """Función principal - Procesamiento con LangChain estándar"""
    print("🚀 PDF TO CHUNKS PROCESSOR - LANGCHAIN EDITION")
    print("=" * 60)
    print("✨ Usando PyPDFLoader + RecursiveCharacterTextSplitter")
    print("📖 Mejores prácticas de LangChain/LangGraph")
    print()
    
    # Configuración optimizada
    CHUNK_SIZE = 1000     # Más grande para mejor contexto
    CHUNK_OVERLAP = 200   # 20% overlap recomendado
    
    print(f"⚙️ Configuración:")
    print(f"   • Chunk size: {CHUNK_SIZE} caracteres")
    print(f"   • Overlap: {CHUNK_OVERLAP} caracteres ({CHUNK_OVERLAP/CHUNK_SIZE*100:.1f}%)")
    print(f"   • Método: LangChain PyPDFLoader")
    print()
    
    # Rutas
    current_dir = Path(__file__).parent
    input_folder = current_dir / "knowledge"
    output_folder = current_dir / "knowledge" / "knowledge_chunks"
    
    # Procesar
    processor = PDFToChunksProcessor(
        str(input_folder), 
        str(output_folder),
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    
    results = processor.process_all_pdfs()
    
    if results:
        print("\n🎉 ¡PROCESAMIENTO COMPLETADO CON LANGCHAIN!")
        print("🔥 Calidad de extracción SUPERIOR a PyPDF2")
        print("📋 Siguiente paso: chunks_to_embeddings.py")
        print(f"📂 Chunks en: {output_folder}")
        
        # Estadísticas
        total_chunks = sum(len(chunks) for chunks in results.values())
        print(f"\n📈 Estadísticas:")
        for doc, chunks in results.items():
            print(f"   • {doc}: {len(chunks)} chunks")
        print(f"   • TOTAL: {total_chunks} chunks")
    else:
        print("\n❌ Sin resultados")
        print(f"Verifica PDFs en: {input_folder}")


if __name__ == "__main__":
    main()