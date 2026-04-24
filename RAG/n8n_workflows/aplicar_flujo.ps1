# Script para aplicar el flujo mejorado via API REST de n8n
# Uso: .\aplicar_flujo.ps1 -ApiKey "tu_api_key_aqui"
param(
    [Parameter(Mandatory=$true)]
    [string]$ApiKey
)

$baseUrl = "https://sara.mysatcomla.com"
$workflowId = "9X5Ohy3YqmKRyk05"
$jsonPath = "$PSScriptRoot\9X5Ohy3YqmKRyk05.json"

$headers = @{
    "X-N8N-API-KEY" = $ApiKey
    "Content-Type"  = "application/json"
}

# 1. Verificar conexion con la API
Write-Host "🔗 Verificando conexión con n8n SARA..." -ForegroundColor Cyan
try {
    $me = Invoke-RestMethod -Uri "$baseUrl/api/v1/workflows/$workflowId" -Headers $headers -Method GET
    Write-Host "✅ Conectado. Flujo actual: $($me.name)" -ForegroundColor Green
} catch {
    Write-Host "❌ Error de conexión: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 2. Leer el JSON local
Write-Host "📄 Leyendo JSON del flujo mejorado..." -ForegroundColor Cyan
$nuevoFlujo = Get-Content $jsonPath -Raw -Encoding UTF8

# 3. Aplicar el nuevo flujo via PUT
Write-Host "🚀 Aplicando nuevo flujo a n8n..." -ForegroundColor Cyan
try {
    $resultado = Invoke-RestMethod -Uri "$baseUrl/api/v1/workflows/$workflowId" `
        -Headers $headers `
        -Method PUT `
        -Body $nuevoFlujo
    Write-Host "✅ Flujo actualizado exitosamente!" -ForegroundColor Green
    Write-Host "   ID: $($resultado.id)" -ForegroundColor Gray
    Write-Host "   Nombre: $($resultado.name)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Error al actualizar flujo: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host $_.ErrorDetails.Message -ForegroundColor Red
    exit 1
}

# 4. Probar accion list inmediatamente
Write-Host "`n📂 Probando accion 'list' en el servidor..." -ForegroundColor Cyan
Write-Host "   (Activa el webhook en n8n primero si no responde)" -ForegroundColor Yellow
try {
    $lista = Invoke-RestMethod -Uri "$baseUrl/webhook/deploy-ingesta?action=list" -Method GET
    Write-Host "✅ Archivos en /opt/RAG/implementacion_SARA/:" -ForegroundColor Green
    Write-Host $lista -ForegroundColor White
} catch {
    Write-Host "⚠️  Webhook no activo o path incorrecto. Activa el webhook en n8n primero." -ForegroundColor Yellow
}

Write-Host "`n✨ Proceso completado." -ForegroundColor Cyan
