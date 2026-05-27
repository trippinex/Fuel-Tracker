# Rebuild the production Tailwind CSS bundle.
# Run this whenever you add/remove Tailwind classes in templates or JS.
#
# Usage:  .\build_css.ps1
#
# The output (app/static/css/tailwind.css) is committed to git so the
# production VM does NOT need Node installed.

Set-Location -Path $PSScriptRoot

if (-not (Test-Path "node_modules\tailwindcss")) {
    Write-Host "Installing dependencies..."
    npm install --silent
}

Write-Host "Building Tailwind CSS..."
npx tailwindcss -i ./app/static/css/tailwind.input.css -o ./app/static/css/tailwind.css --minify

if (Test-Path "app\static\css\tailwind.css") {
    $size = (Get-Item "app\static\css\tailwind.css").Length
    Write-Host "Built tailwind.css: $size bytes"
} else {
    Write-Host "ERROR: tailwind.css was not produced." -ForegroundColor Red
    exit 1
}
