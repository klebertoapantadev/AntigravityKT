# 📘 Manual Técnico RAG - TINKAY

Este documento describe la arquitectura técnica, los flujos de automatización y los scripts del sistema **RAG (Retrieval-Augmented Generation)** del proyecto **Tinkay**.

---

## 🏗️ 1. Arquitectura General

El sistema RAG de Tinkay opera sobre el servidor auto-hosteado **SARA** (`https://sara.mysatcomla.com`), con n8n como orquestador y Supabase como base de datos vectorial.

```
Usuario / API
     │
     ▼
 n8n SARA (Auto-hosteado)
     │
     ├─► Scripts Python (/opt/RAG/implementacion_SARA/)
     │         │
     │         └─► Supabase Tinkay (ufnpzxlvpwagavoytwco)
     │               └─► Esquema: rag
     │                     ├─► tabla: collections
     │                     └─► tabla: vectors
     └─► Webhook endpoints (GET/POST)
```

---

## 🔄 2. Flujos n8n en SARA

### 2.1 — `AUX_GetFiles_<V1>` · ID: `fJdydtk52ec3vYzG`

**Propósito:** Explorar y descargar los archivos Python desplegados en el servidor SARA. Herramienta de inspección y mantenimiento del entorno.

**Webhook:** `GET https://sara.mysatcomla.com/webhook/GetFiles`

**Lógica del flujo:**

```
Webhook GET
    │
    ▼
Parsear Parametros (Code)
    │  Lee query.fileName del request
    ▼
Verificar Nombre Archivo (IF)
    │
    ├─ [Con fileName] ──► Leer Archivo en Base64 (Execute Command)
    │                          │ cat <archivo> | base64 -w 0
    │                          ▼
    │                    Decodificar y Devolver Archivo (Code)
    │                          │ Devuelve { contenido, bytes }
    │
    └─ [Sin fileName] ──► Listar Archivos del Servidor (Execute Command)
                               │ ls -1 /opt/RAG/implementacion_SARA/
                               ▼
                         Formatear Lista (Code)
                               │ Devuelve { archivos[], total, directorio }
```

**Nodos del flujo:**

| Nodo | Tipo | Función |
|------|------|---------|
| `Webhook GET` | webhook | Recibe peticiones GET en `/webhook/GetFiles` |
| `Parsear Parametros` | code | Extrae `query.fileName` del request |
| `Verificar Nombre Archivo` | if | Bifurca según si hay `fileName` o no |
| `Listar Archivos del Servidor` | executeCommand | Ejecuta `ls -1` en el directorio RAG |
| `Formatear Lista` | code | Formatea la salida del `ls` en JSON |
| `Leer Archivo en Base64` | executeCommand | Ejecuta `cat <archivo> \| base64 -w 0` |
| `Decodificar y Devolver Archivo` | code | Decodifica base64 y retorna el contenido como texto |

**Uso:**

```bash
# Listar todos los archivos
GET https://sara.mysatcomla.com/webhook/GetFiles

# Respuesta:
{
  "archivos": ["Ingesta_PDF_WEB.py", "sara_pdf_ingest_v2.py", ...],
  "total": 5,
  "directorio": "/opt/RAG/implementacion_SARA/"
}

# Descargar un archivo por nombre
GET https://sara.mysatcomla.com/webhook/GetFiles?fileName=Ingesta_PDF_WEB.py

# Respuesta:
{
  "contenido": "#!/usr/bin/env python3\n...",
  "archivoLeido": true,
  "bytes": 11606
}
```

**Notas técnicas:**
- Usa `lastNode` como `responseMode` — el último nodo ejecutado define la respuesta HTTP.
- La descarga se realiza vía `cat | base64` + decodificación en el nodo Code para evitar dependencia del nodo `readBinaryFile` (incompatible con el modo `lastNode`).
- El manejo de errores (`onError: continueErrorOutput`) en el nodo de lectura permite devolver un JSON de error descriptivo si el archivo no existe.

---

### 2.2 — Flujo de Ingesta RAG · IDs: `eiseWnDVUMV8L49D` / `3e30HCu1WMRq14oF`

> 📄 Documentación pendiente — ver workflows en `c:\@Antigravity\Tinkay\RAG\n8n_workflows\`

---

## 🐍 3. Scripts Python en Servidor

Los scripts de ingesta residen en el servidor SARA en:

```
/opt/RAG/implementacion_SARA/
```

### Archivos actuales del servidor

| Archivo | Descripción |
|---------|-------------|
| `Ingesta_PDF_WEB.py` | Script principal multi-formato (PDF, TXT, MD, Web) |
| `sara_pdf_ingest_v2.py` | Versión 2 del script de ingesta |
| `sara_pdf_ingest_v3.py` | Versión 3 del script de ingesta |
| `zoho_learn_ingest.py` | Script de ingesta desde Zoho Learn |
| `temp_b64` | Directorio temporal para archivos en base64 |

> 💡 Para ver los archivos actualizados, usar `GET /webhook/GetFiles` del flujo `AUX_GetFiles_<V1>`.

---

## 🗄️ 4. Base de Datos Supabase

- **Proyecto ID:** `ufnpzxlvpwagavoytwco`
- **Esquema principal:** `rag`

### Tablas

| Tabla | Función |
|-------|---------|
| `rag.collections` | Catálogo de fuentes ingestadas (nombre, URL, tipo, negocio) |
| `rag.vectors` | Embeddings vectoriales y fragmentos de texto |

---

## 🌐 5. Dominios y Conectividad

| Servicio | URL |
|----------|-----|
| n8n SARA | `https://sara.mysatcomla.com` |
| Supabase Tinkay | `https://ufnpzxlvpwagavoytwco.supabase.co` |
| Webhook GetFiles | `https://sara.mysatcomla.com/webhook/GetFiles` |

---

*Documentación generada por Antigravity — Proyecto TINKAY*
