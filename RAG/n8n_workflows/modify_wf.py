import json

with open('XT2mlHdZxQ01Sp6L_utf8.json', 'r', encoding='utf-8') as f:
    wf = json.load(f)

# Modificar nodos en el array principal
for node in wf.get('nodes', []):
    if node['name'] == 'Guardar en Disco':
        node['parameters']['jsCode'] = """const fs = require('fs');
const items = $input.all();

for (let i = 0; i < items.length; i++) {
  const binaryBuffer = await this.helpers.getBinaryDataBuffer(i, 'data');
  const safeFilename = $('Normalizar Nombre').item.json.nombre_archivo_limpio;
  const filePath = '/opt/RAG/temp_pdfs/' + safeFilename;
  
  // Asegurar que el directorio existe
  if (!fs.existsSync('/opt/RAG/temp_pdfs/')) {
    fs.mkdirSync('/opt/RAG/temp_pdfs/', { recursive: true });
  }

  fs.writeFileSync(filePath, binaryBuffer);
  
  // Pasar filePath al siguiente nodo
  items[i].json.filePath = filePath;
}

return items;"""
    
    if node['name'] == 'Ingesta File':
        node['parameters']['command'] = "=python3 /opt/RAG/implementacion_SARA/Ingesta_PDF_WEB.py --file=\"{{ $('Guardar en Disco').item.json.filePath }}\" --source=\"{{ $('Normalizar Nombre').item.json.name }}\" --url=\"{{ $('Subir a Drive').item.json.webViewLink }}\" --negocio=\"tinkay\" --visibilidad=\"publico\" --user=\"admin@tinkay.com\""

# Eliminar activeVersion para evitar conflictos y que n8n use el root
if 'activeVersion' in wf:
    del wf['activeVersion']

with open('XT2mlHdZxQ01Sp6L_modified.json', 'w', encoding='utf-8') as f:
    json.dump(wf, f, indent=2, ensure_ascii=False)
