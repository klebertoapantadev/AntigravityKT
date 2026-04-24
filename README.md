# 🌸 Proyecto Tinkay

Este repositorio contiene el ecosistema digital de **Tinkay**, dividido en dos módulos principales para la gestión inteligente de clientes y operaciones.

## 🏗️ Estructura del Proyecto

```text
Tinkay/
├── RAG/            # Motor de IA y Generación Aumentada por Recuperación
│   ├── n8n_workflows/  # Flujos de automatización para ingesta y consulta
│   ├── scripts/        # Scripts de procesamiento (Python)
│   └── manual_rag.md   # Documentación técnica del RAG
└── PORTAL/         # Interfaz Web de Gestión (Next.js)
    ├── src/            # Código fuente del portal
    ├── public/         # Activos estáticos
    └── README.md       # Documentación del portal
```

## 🚀 Módulos

### 1. [RAG (Knowledge Base)](./RAG/manual_rag_tinkay.md)
El motor de conocimiento que alimenta a los agentes de IA (WhatsApp/Telegram). Soporta ingesta de PDFs, texto plano y sitios web.

### 2. [PORTAL (AgenteVentas)](./PORTAL/README.md)
Panel de control centralizado para:
- Gestión multitenant de negocios (Floristería, Eventos, Cafetería).
- Administración de conocimiento (CRUD de RAG).
- Visualización de chats y consumo de tokens.
- Monitoreo de procesos y logs.

## 🛠️ Tecnologías
- **Frontend:** Next.js + Vanilla CSS.
- **Backend:** n8n (Orquestación vía Webhooks).
- **Base de Datos:** Supabase (Auth + PostgREST).
- **IA:** Google Gemini (Embeddings & Flash).

---
*Desarrollado por Antigravity para Tinkay 2026*
