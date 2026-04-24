$filePath = "C:\@Antigravity\Tinkay\RAG\scripts\Ingesta_PDF_WEB.py"
$content = Get-Content $filePath -Raw -Encoding UTF8
$url = "https://sara.mysatcomla.com/webhook/deploy-ingesta?action=deploy&file=Ingesta_PDF_WEB.py"

Write-Host "🚀 Desplegando Ingesta_PDF_WEB.py al servidor SARA..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri $url -Method POST -Body $content -ContentType "text/plain; charset=utf-8"
    Write-Host "✅ Respuesta del servidor:" -ForegroundColor Green
    Write-Host $response
} catch {
    Write-Host "❌ Error en el despliegue:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    if ($_.ErrorDetails) { Write-Host $_.ErrorDetails.Message }
}
