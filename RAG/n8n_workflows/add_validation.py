import json
import uuid

with open('XT2mlHdZxQ01Sp6L_utf8.json', 'r', encoding='utf-8') as f:
    wf = json.load(f)

# 1. Definir nuevos nodos
validar_node = {
    "parameters": {
        "operation": "executeQuery",
        "query": "SELECT count(*) as total FROM rag.vectors WHERE metadata->>'source_url' = $1;",
        "options": {
            "queryReplacement": "={{ $('Subir a Drive').item.json.webViewLink }}"
        }
    },
    "id": str(uuid.uuid4()),
    "name": "Validar BDD",
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.2,
    "position": [-600, -96],
    "credentials": {
        "postgres": {
            "id": "FaUacjYgtrgjH96Z",
            "name": "Postgres KT Free IMUm7zBFmxNuggNj"
        }
    }
}

responder_node = {
    "parameters": {
        "options": {
            "responseHeaders": {
                "entries": [
                    {
                        "name": "Content-Type",
                        "value": "application/json"
                    }
                ]
            }
        },
        "responseBody": "={{ { \"success\": $json.total > 0, \"total_vectores\": $json.total, \"source_url\": $('Subir a Drive').item.json.webViewLink, \"output_script\": $('Ingesta File').item.json.stdout || $('Ingesta File').item.json.stderr } }}"
    },
    "id": str(uuid.uuid4()),
    "name": "Responder Ingesta",
    "type": "n8n-nodes-base.respondToWebhook",
    "typeVersion": 1,
    "position": [-400, -96]
}

# 2. Agregar nodos al flujo
wf['nodes'].append(validar_node)
wf['nodes'].append(responder_node)

# 3. Actualizar conexiones
# Ingesta File (9b2f0d56-8d43-4a25-bd0b-f48dc48507ce) -> Validar BDD
if 'connections' not in wf: wf['connections'] = {}
wf['connections']['Ingesta File'] = {
    "main": [[{"node": validar_node['name'], "type": "main", "index": 0}]]
}
# Validar BDD -> Responder Ingesta
wf['connections'][validar_node['name']] = {
    "main": [[{"node": responder_node['name'], "type": "main", "index": 0}]]
}

# 4. Limpiar y guardar
wf_clean = {
    "name": wf['name'],
    "nodes": wf['nodes'],
    "connections": wf['connections'],
    "settings": wf.get('settings', {"executionOrder": "v1"}),
    "meta": wf.get('meta', {})
}

with open('XT2mlHdZxQ01Sp6L_validation.json', 'w', encoding='utf-8') as f:
    json.dump(wf_clean, f, indent=2, ensure_ascii=False)
