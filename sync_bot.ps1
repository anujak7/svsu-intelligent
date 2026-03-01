# SVSU Bot Auto-Sync Script
# Run this script to update the chatbot's knowledge with the latest website data and PDFs.

Write-Host "--- Starting SVSU Bot Knowledge Sync ---" -ForegroundColor Cyan

# Check if python is installed
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Python is not installed or not in PATH." -ForegroundColor Red
    exit
}

# Run the ingestion script
Write-Host "Crawling SVSU Website and Processing PDFs..." -ForegroundColor Yellow
python ingest.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "--- Sync Complete! SVSU Intelligent is now updated. ---" -ForegroundColor Green
} else {
    Write-Host "--- Sync Failed. Please check the errors above. ---" -ForegroundColor Red
}
