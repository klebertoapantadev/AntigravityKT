# 🌸 Manual Técnico RAG - Tinkay

Este documento detalla la implementación del sistema de **Generación Aumentada por Recuperación (RAG)** para el ecosistema **Tinkay**, bajo una arquitectura multinegocio escalable.

---

## 🏗️ 1. Arquitectura Multinegocio
El sistema ha sido migrado de una estructura monolítica a un esquema relacional que permite separar el conocimiento por unidades de negocio utilizando el parámetro `negocio`.

- **Esquema de BD:** `rag`
- **Identificador Tinkay:** `tinkay`
- **Visibilidad Default:** `publico`

---

## 🔄 2. Proceso de Ingesta (Carga de Datos)

El flujo de ingesta toma fuentes externas (PDF o Web) y las transforma en vectores dentro de la base de datos.

### Componentes:
- **Flujo n8n:** `TinkayRAG_Ingesta_V1` (ID: `XT2mlHdZxQ01Sp6L`)
- **Script de Procesamiento:** `/opt/RAG/implementacion_SARA/Ingesta_PDF_WEB.py`

### Funcionamiento:
1. El webhook recibe la URL o el archivo PDF.
2. Se invoca al script de Python con los flags de negocio:
   ```bash
   python3 Ingesta_PDF_WEB.py --pdf [Ruta] --negocio "tinkay" --source [Nombre] --visibilidad "publico"
   ```
3. El script realiza:
   - Chunking semántico recursivo.
   - Generación de embeddings con Gemini.
   - Registro de la fuente en `rag.collections`.
   - Inserción de vectores en `rag.vectors` asociados al `collection_id`.

---

## 🔍 3. Proceso de Consulta (Recuperación)

Permite al agente SARA buscar información específica de Tinkay para responder preguntas.

### Componentes:
- **Flujo n8n:** `TinkayRAG_Consulta_V1` (ID: `3e30HCu1WMRq14oF`)
- **Motor de Búsqueda:** Función RPC `rag.match_documents`.

### Lógica de Filtrado:
A diferencia del sistema anterior, las consultas ahora filtran estrictamente por:
- `p_negocio = 'tinkay'`
- `p_estado = 'ACTIVO'`
- `p_visibilidad = 'publico'` (o privado según el usuario).

---

## 💬 4. Prueba de Consulta (Chat)

- **Flujo de Chat:** `eiseWnDVUMV8L49D`
- **Interfaz:** Dashboard Tinkay / SARA Chat Widget.
Este flujo actúa como el orquestador final que recibe la pregunta del usuario, llama al flujo de consulta y genera la respuesta final con Gemini.

---

## 🗄️ 5. Estructura Supabase (Esquema `rag`)

### Tablas Principales:
1. **`rag.collections`**: Almacena las fuentes de información.
   - `id`, `name`, `negocio`, `tipo`, `source_url`, `visibilidad`, `estado`.
2. **`rag.vectors`**: Almacena los fragmentos y sus vectores.
   - `id`, `collection_id` (FK), `content`, `embedding` (3072 dims).

### Funciones SQL:
- **`rag.match_documents`**: Realiza la búsqueda de similitud de coseno con filtros de negocio y estado.

---

## 🤖 6. Dependencias y Modelos

### Inteligencia Artificial (Google Gemini):
- **Embeddings:** `gemini-embedding-2-preview` (Dimensiones: 3072).
- **Generación:** `gemini-1.5-flash` (Rápido y eficiente para respuestas de chat).

### Infraestructura:
- **Orquestador:** n8n SARA (Auto-hosteado en `https://sara.mysatcomla.com`).
- **Base de Datos:** Supabase (`ufnpzxlvpwagavoytwco`).
- **Entorno Python:** PyMuPDF, Supabase-py, Google-GenAI.

---
*Manual generado por Antigravity - Proyecto TINKAY 2026*
