"""
Ingesta_PDF_WEB.py — RAG Genérico (PDF + TXT + MD + Web)
=========================================================
Script de ingesta para el sistema RAG KT / TINKAY.

Soporta:
  - PDFs locales (extracción con PyMuPDF)
  - Archivos .txt planos (lectura directa)
  - Archivos .md Markdown (lectura con limpieza de sintaxis)
  - Páginas web (scraping con requests + BeautifulSoup)

Almacena vectores en schema 'rag' de Supabase.

Argumentos compatibles con el nodo n8n 'Ingesta File':
  --file       : Ruta al archivo local (PDF, TXT o MD)
  --web        : URL de la página web a ingestar
  --source     : Nombre descriptivo de la fuente (ej: "Catálogo Tinkay")
  --url        : URL canónica del documento (ej: link de Google Drive)
  --negocio    : Slug del negocio (ej: "tinkay")
  --visibilidad: Visibilidad del documento (ej: "publico")
  --user       : Email del usuario que ejecuta la ingesta
  --manual     : Categoría o manual (opcional)
  --article    : Título del artículo (opcional)
  --keep       : No borrar el archivo tras la ingesta
  --no-dedup   : Omitir deduplicación de vectores previos
"""

import os
import re
import uuid
import time
import random
import asyncio
import argparse
import concurrent.futures
import requests
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from google import genai
from google.genai import types

# ── Configuración ────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent / ".env.rag_kt")

SUPABASE_URL    = os.environ.get("RAG_KT_SUPABASE_URL")
SUPABASE_KEY    = os.environ.get("RAG_KT_SUPABASE_KEY")
GEMINI_API_KEY  = os.environ.get("RAG_KT_GEMINI_API_KEY")

EMBEDDING_MODEL   = "gemini-embedding-2-preview"
EMBEDDING_DIMS    = 3072
CHUNK_SIZE        = 1200
CHUNK_OVERLAP     = 200
BATCH_INSERT_SIZE = 100
EMBED_BATCH_SIZE  = 20
MAX_CONCURRENCY   = 20
EMBED_CALL_TIMEOUT = 90
EMBED_MAX_RETRIES  = 5

# Tablas en schema 'rag'
TABLE_VECTORS     = "rag.vectors"
TABLE_COLLECTIONS = "rag.collections"

SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", ", ", " ", ""]

sem = asyncio.Semaphore(MAX_CONCURRENCY)
_gemini_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=MAX_CONCURRENCY + 5,
    thread_name_prefix="gemini_embed",
)


# ════════════════════════════════════════════════════════════════════
# 1. CHUNKING SEMÁNTICO
# ════════════════════════════════════════════════════════════════════

def recursive_split(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    separators: list = None,
) -> list[str]:
    """
    Divide texto recursivamente usando separadores semánticos en orden
    de prioridad: párrafos > líneas > oraciones > palabras > caracteres.
    """
    if separators is None:
        separators = SEPARATORS

    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chosen_sep = ""
    remaining_seps = []
    for i, sep in enumerate(separators):
        if sep == "":
            chosen_sep = ""
            remaining_seps = []
            break
        if sep in text:
            chosen_sep = sep
            remaining_seps = separators[i + 1:]
            break

    if chosen_sep == "" and not remaining_seps:
        result = []
        for i in range(0, len(text), chunk_size - chunk_overlap):
            result.append(text[i: i + chunk_size].strip())
        return [c for c in result if c]

    raw_splits = [s for s in text.split(chosen_sep) if s.strip()]
    chunks = []
    current_parts: list[str] = []
    current_len = 0

    for split in raw_splits:
        split = split.strip()
        if not split:
            continue

        sep_len  = len(chosen_sep) if current_parts else 0
        split_len = len(split)

        if current_len + sep_len + split_len > chunk_size and current_parts:
            chunk_text = chosen_sep.join(current_parts).strip()
            if chunk_text:
                chunks.append(chunk_text)

            overlap_parts: list[str] = []
            overlap_len = 0
            for part in reversed(current_parts):
                part_sep_len = len(chosen_sep) if overlap_parts else 0
                if overlap_len + part_sep_len + len(part) > chunk_overlap:
                    break
                overlap_parts.insert(0, part)
                overlap_len += part_sep_len + len(part)

            current_parts = overlap_parts
            current_len   = overlap_len

        current_parts.append(split)
        current_len += (len(chosen_sep) if len(current_parts) > 1 else 0) + split_len

    if current_parts:
        chunk_text = chosen_sep.join(current_parts).strip()
        if chunk_text:
            chunks.append(chunk_text)

    if remaining_seps:
        final: list[str] = []
        for chunk in chunks:
            if len(chunk) > chunk_size:
                final.extend(
                    recursive_split(chunk, chunk_size, chunk_overlap, remaining_seps)
                )
            else:
                final.append(chunk)
        return final

    return chunks


# ════════════════════════════════════════════════════════════════════
# 2. WEB SCRAPING
# ════════════════════════════════════════════════════════════════════

def scrape_web_page(url: str) -> str:
    """
    Descarga una página web y extrae su contenido de texto limpio.
    Usa BeautifulSoup si está disponible, sino regex.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; RAG-KT-Bot/1.0)"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    html = response.text

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # Eliminar elementos no textuales
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Intentar obtener contenido principal
        main = soup.find("main") or soup.find("article") or soup.find("body")
        if main:
            text = main.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

    except ImportError:
        # Fallback sin BeautifulSoup
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>",  "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

    # Limpiar líneas vacías excesivas
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# 3. EXTRACCIÓN DE ARCHIVOS LOCALES
# ════════════════════════════════════════════════════════════════════

def extract_text_from_pdf(file_path: str) -> list[dict]:
    """Extrae texto del PDF página por página y aplica chunking semántico."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError("❌ PyMuPDF (fitz) no está instalado. Ejecuta: pip install pymupdf")

    doc = fitz.open(file_path)
    total_pages = len(doc)
    print(f"📖 PDF — {total_pages} páginas: '{Path(file_path).name}'...", flush=True)

    text_items = []
    for page_idx in range(total_pages):
        page     = doc[page_idx]
        raw_text = page.get_text().strip().replace("\x00", "")
        if raw_text:
            chunks = recursive_split(raw_text)
            for chunk_idx, chunk in enumerate(chunks):
                text_items.append({
                    "page":        page_idx + 1,
                    "chunk_index": chunk_idx,
                    "text":        chunk,
                })
    doc.close()
    return text_items


def extract_text_from_txt(file_path: str) -> list[dict]:
    """Lee un archivo .txt plano y aplica chunking semántico."""
    print(f"📄 TXT — Leyendo: '{Path(file_path).name}'...", flush=True)

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        raw_text = f.read()

    chunks = recursive_split(raw_text)
    text_items = []
    for chunk_idx, chunk in enumerate(chunks):
        text_items.append({
            "page":        1,
            "chunk_index": chunk_idx,
            "text":        chunk,
        })
    return text_items


def extract_text_from_markdown(file_path: str) -> list[dict]:
    """
    Lee un archivo .md y aplica chunking semántico.
    Limpia la sintaxis Markdown antes de vectorizar.
    """
    print(f"📝 MD — Leyendo: '{Path(file_path).name}'...", flush=True)

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        raw_text = f.read()

    # Limpiar sintaxis Markdown básica para texto más limpio
    text = raw_text
    # Eliminar bloques de código (conservar el contenido)
    text = re.sub(r"```[a-zA-Z]*\n?(.*?)```", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Eliminar encabezados de sintaxis (# ## ###) pero conservar el texto
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Eliminar negrita e itálica
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*",     r"\1", text)
    text = re.sub(r"__(.+?)__",     r"\1", text)
    text = re.sub(r"_(.+?)_",       r"\1", text)
    # Eliminar enlaces Markdown [texto](url) → texto
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Eliminar imágenes ![alt](url)
    text = re.sub(r"!\[[^\]]*\]\([^\)]+\)", "", text)
    # Limpiar líneas horizontales
    text = re.sub(r"^[-*_]{3,}$", "", text, flags=re.MULTILINE)
    # Normalizar espacios múltiples y líneas en blanco
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    chunks = recursive_split(text)
    text_items = []
    for chunk_idx, chunk in enumerate(chunks):
        text_items.append({
            "page":        1,
            "chunk_index": chunk_idx,
            "text":        chunk,
        })
    return text_items


def extract_text_from_web(url: str) -> list[dict]:
    """Descarga página web, extrae texto y aplica chunking semántico."""
    print(f"🌐 WEB — Descargando: {url}", flush=True)
    raw_text = scrape_web_page(url)

    if not raw_text.strip():
        print("⚠️ No se encontró contenido de texto en la página.", flush=True)
        return []

    chunks = recursive_split(raw_text)
    text_items = []
    for chunk_idx, chunk in enumerate(chunks):
        text_items.append({
            "page":        1,
            "chunk_index": chunk_idx,
            "text":        chunk,
        })

    print(f"📊 Extraídos {len(text_items)} chunks de la web.", flush=True)
    return text_items


# ════════════════════════════════════════════════════════════════════
# 4. DETECTOR DE TIPO DE ARCHIVO
# ════════════════════════════════════════════════════════════════════

EXTENSION_HANDLERS = {
    ".pdf": ("pdf", extract_text_from_pdf),
    ".txt": ("txt", extract_text_from_txt),
    ".md":  ("md",  extract_text_from_markdown),
}

def detect_and_extract(file_path: str) -> tuple[str, list[dict]]:
    """
    Detecta el tipo de archivo por extensión y extrae su texto.
    Retorna (source_type, text_items).
    """
    ext = Path(file_path).suffix.lower()
    if ext not in EXTENSION_HANDLERS:
        raise ValueError(
            f"❌ Tipo de archivo no soportado: '{ext}'. "
            f"Soportados: {', '.join(EXTENSION_HANDLERS.keys())}"
        )
    source_type, handler = EXTENSION_HANDLERS[ext]
    text_items = handler(file_path)
    return source_type, text_items


# ════════════════════════════════════════════════════════════════════
# 5. INICIALIZACIÓN
# ════════════════════════════════════════════════════════════════════

def init_clients():
    """Inicializa clientes de Supabase y Gemini desde variables de entorno."""
    if not all([SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY]):
        raise RuntimeError(
            "❌ Faltan variables de entorno: "
            "RAG_KT_SUPABASE_URL, RAG_KT_SUPABASE_KEY, RAG_KT_GEMINI_API_KEY"
        )
    sb     = create_client(SUPABASE_URL, SUPABASE_KEY)
    gemini = genai.Client(api_key=GEMINI_API_KEY)
    return sb, gemini


# ════════════════════════════════════════════════════════════════════
# 6. EMBEDDINGS PARALELOS
# ════════════════════════════════════════════════════════════════════

def _embed_sync(gemini_client, contents):
    """Llamada síncrona con timeout y reintentos con backoff exponencial + jitter."""
    last_exc = None
    for attempt in range(EMBED_MAX_RETRIES):
        try:
            future = _gemini_executor.submit(
                gemini_client.models.embed_content,
                model=EMBEDDING_MODEL,
                contents=contents,
                config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMS),
            )
            res = future.result(timeout=EMBED_CALL_TIMEOUT)
            return res.embeddings[0].values
        except concurrent.futures.TimeoutError as e:
            last_exc = e
            wait = min(10 * (attempt + 1), 60) + random.uniform(0, 5)
            print(f"⏱️ Timeout (intento {attempt + 1}/{EMBED_MAX_RETRIES}). Reintentando en {wait:.1f}s...", flush=True)
        except Exception as e:
            last_exc = e
            wait = min(2 ** attempt * 3, 60) + random.uniform(0, 5)
            print(f"⚠️ Error embed (intento {attempt + 1}/{EMBED_MAX_RETRIES}): {e}. Reintentando en {wait:.1f}s...", flush=True)
        if attempt < EMBED_MAX_RETRIES - 1:
            time.sleep(wait)
    raise RuntimeError(f"embed_content falló tras {EMBED_MAX_RETRIES} intentos: {last_exc}")


async def embed_async(gemini_client, contents) -> list[float]:
    async with sem:
        return await asyncio.to_thread(_embed_sync, gemini_client, contents)


async def embed_batch_async(gemini_client, items: list[dict], label: str = "items") -> list[tuple]:
    """Genera embeddings en paralelo en lotes de EMBED_BATCH_SIZE."""
    results = []
    total   = len(items)
    for i in range(0, total, EMBED_BATCH_SIZE):
        batch        = items[i: i + EMBED_BATCH_SIZE]
        tasks        = [embed_async(gemini_client, item["contents"]) for item in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        results.extend(zip([item["meta"] for item in batch], batch_results))
        done = min(i + EMBED_BATCH_SIZE, total)
        print(f"⏳ Embeddings {label}: {done}/{total}", flush=True)
    return results


# ════════════════════════════════════════════════════════════════════
# 7. DEDUPLICACIÓN
# ════════════════════════════════════════════════════════════════════

def delete_existing_vectors(sb_client, source_url: str):
    """Elimina vectores previos con el mismo source_url."""
    try:
        result = (
            sb_client.schema("rag").table("vectors")
            .delete()
            .eq("metadata->>source_url", source_url)
            .execute()
        )
        count = len(result.data) if result.data else 0
        if count > 0:
            print(f"🗑️ Eliminados {count} vectores previos de: {source_url}", flush=True)
    except Exception as e:
        print(f"⚠️ Error en deduplicación (no fatal): {e}", flush=True)


# ════════════════════════════════════════════════════════════════════
# 8. PIPELINE PRINCIPAL
# ════════════════════════════════════════════════════════════════════

async def process_and_insert(
    sb_client,
    gemini_client,
    text_items:  list[dict],
    source_name: str,
    source_url:  str,
    source_type: str,
    created_by:  str = None,
    negocio:     str = None,
    visibilidad: str = None,
    manual:      str = None,
    article:     str = None,
):
    """Genera embeddings y los inserta en rag.vectors."""
    total = len(text_items)
    if total == 0:
        print(f"⚠️ No hay chunks para procesar para la fuente: {source_name}", flush=True)
        return 0

    print(f"📊 {total} chunks de texto detectados. Generando embeddings...", flush=True)

    embed_items = [
        {"contents": item["text"], "meta": item}
        for item in text_items
    ]
    results = await embed_batch_async(gemini_client, embed_items, label="texto")

    vectors = []
    for meta, result in results:
        if isinstance(result, Exception):
            print(
                f"⚠️ Error embedding chunk (pág {meta['page']}, idx {meta['chunk_index']}): {result}",
                flush=True,
            )
            continue

        vectors.append({
            "id":         str(uuid.uuid4()),
            "content":    meta["text"],
            "type":       "text",
            "embedding":  result,
            "created_by": created_by,
            "metadata": {
                "source":       source_name,
                "source_url":   source_url,
                "source_type":  source_type,
                "page_number":  meta["page"],
                "chunk_index":  meta["chunk_index"],
                "negocio":      negocio,
                "visibilidad":  visibilidad,
                "manual":       manual,
                "article":      article,
            },
        })

    # Inserción en batches
    if vectors:
        print(f"💾 Intentando insertar {len(vectors)} vectores en rag.vectors (source_url: {source_url})...", flush=True)
        try:
            for i in range(0, len(vectors), BATCH_INSERT_SIZE):
                batch = vectors[i: i + BATCH_INSERT_SIZE]
                print(f"🚀 Enviando lote {i//BATCH_INSERT_SIZE + 1} ({len(batch)} vectores)...", flush=True)
                res = sb_client.schema("rag").table("vectors").insert(batch).execute()
                
                # En supabase-py v2, execute() lanza excepciones para errores HTTP, 
                # pero en v1 o con ciertos códigos puede devolver un objeto con error.
                if hasattr(res, 'error') and res.error:
                    print(f"❌ Error de Supabase detectado en respuesta: {res.error}", flush=True)
            
            print(f"✅ {len(vectors)} vectores insertados correctamente.", flush=True)
        except Exception as e:
            print(f"❌ Error crítico durante la inserción: {str(e)}", flush=True)
            # Intentar ver si hay más info (PostgrestError)
            if hasattr(e, 'message'): print(f"Mensaje: {e.message}", flush=True)
            if hasattr(e, 'details'): print(f"Detalles: {e.details}", flush=True)
            if hasattr(e, 'hint'):    print(f"Sugerencia: {e.hint}", flush=True)
            raise
    else:
        print("⚠️ No se generaron vectores válidos tras el proceso de embedding.", flush=True)

    return len(vectors)


# ════════════════════════════════════════════════════════════════════
# 9. ENTRYPOINT
# ════════════════════════════════════════════════════════════════════

async def main_async():
    parser = argparse.ArgumentParser(
        description="RAG Genérico — Ingesta PDF + TXT + MD + Web"
    )

    # Fuente: archivo local O URL web (mutuamente excluyentes)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--file",
        help="Ruta al archivo local (.pdf, .txt, .md)",
    )
    group.add_argument(
        "--web",
        help="URL de la página web a ingestar",
    )

    # Metadatos
    parser.add_argument("--source",      required=True,  help="Nombre descriptivo de la fuente")
    parser.add_argument("--url",         required=False, help="URL canónica del documento (ej: link de Drive)")
    parser.add_argument("--negocio",     required=False, help="Slug del negocio (ej: tinkay)")
    parser.add_argument("--visibilidad", required=False, help="Visibilidad del documento (ej: publico)")
    parser.add_argument("--user",        required=False, help="Email del usuario que ejecuta la ingesta")
    parser.add_argument("--manual",      required=False, help="Categoría o manual")
    parser.add_argument("--article",     required=False, help="Título del artículo")

    # Flags de comportamiento
    parser.add_argument("--keep",     action="store_true", help="No borrar el archivo tras la ingesta")
    parser.add_argument("--no-dedup", action="store_true", help="Omitir deduplicación de vectores previos")

    args = parser.parse_args()

    # ── Determinar tipo de fuente y source_url canónica ──────────────
    if args.file:
        file_path  = args.file
        source_url = args.url or file_path

        if not os.path.exists(file_path):
            print(f"❌ El archivo '{file_path}' no existe.", flush=True)
            exit(1)

        # Detectar extensión y extraer texto
        try:
            source_type, text_items = detect_and_extract(file_path)
        except ValueError as e:
            print(str(e), flush=True)
            exit(1)

    else:  # --web
        source_type = "web"
        source_url  = args.web
        text_items  = []  # se llena después de init_clients (no requiere cliente)

    # ── Inicializar clientes ──────────────────────────────────────────
    try:
        sb_client, gemini_client = init_clients()
    except RuntimeError as e:
        print(str(e), flush=True)
        exit(1)

    print(f"🚀 Iniciando ingesta RAG ({source_type.upper()}): {source_url}", flush=True)

    try:
        # Extracción web (fuera de detect_and_extract porque no necesita clientes)
        if source_type == "web":
            text_items = extract_text_from_web(args.web)

        # Deduplicación
        if not args.no_dedup:
            delete_existing_vectors(sb_client, source_url)

        # Embeddings + inserción en rag.vectors
        count = await process_and_insert(
            sb_client,
            gemini_client,
            text_items,
            source_name=args.source,
            source_url=source_url,
            source_type=source_type,
            created_by=args.user,
            negocio=args.negocio,
            visibilidad=args.visibilidad,
            manual=args.manual,
            article=args.article,
        )

        # Registrar en rag.collections
        sb_client.schema("rag").table("collections").upsert(
            {
                "name":        args.source,
                "source_type": source_type,
                "source_url":  source_url,
                "negocio":     args.negocio,
                "visibilidad": args.visibilidad,
                "manual":      args.manual,
                "articulo":    args.article,
                "created_by":  args.user,
                "status":      "completed",
            },
            on_conflict="source_url",
        ).execute()

        print(f"✨ Ingesta completada: {count} vectores de '{args.source}'", flush=True)

    except Exception as e:
        print(f"🔥 Error crítico: {e}", flush=True)
        raise

    finally:
        # Limpiar archivo local si corresponde
        if args.file and not args.keep and os.path.exists(args.file):
            os.remove(args.file)
            print(f"🧹 Archivo temporal eliminado: {args.file}", flush=True)


if __name__ == "__main__":
    asyncio.run(main_async())
