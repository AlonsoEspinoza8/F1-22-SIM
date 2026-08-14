#!/bin/bash

# Navegar a la carpeta del proyecto
cd "/Users/alonsoespinozacorrea/F1-22-SIM"

# Activar el entorno virtual
python3 -m venv venv
source venv/bin/activate    
pip install --upgrade pip
pip install -r requirements.txt

# --- Asegurar que Ollama esté corriendo y que el modelo del ingeniero esté descargado ---
# (si falla algo acá, no cortamos el arranque del juego: el ingeniero de voz
# simplemente queda deshabilitado y el resto del dashboard funciona igual)
MODELO_OLLAMA="llama3.2:3b"

if ! pgrep -x "Ollama" > /dev/null; then
    echo "🦙 Abriendo Ollama..."
    open -a Ollama 2>/dev/null

    # Esperamos hasta 15s a que el servicio quede escuchando
    for i in $(seq 1 15); do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done
fi

if command -v ollama > /dev/null 2>&1; then
    if ollama list 2>/dev/null | grep -q "$MODELO_OLLAMA"; then
        echo "✅ Modelo '$MODELO_OLLAMA' ya está descargado."
    else
        echo "📥 Descargando el modelo '$MODELO_OLLAMA' para el ingeniero de voz (una sola vez, puede tardar unos minutos)..."
        ollama pull "$MODELO_OLLAMA"
    fi
else
    echo "⚠️ No se encontró el comando 'ollama'. Instalalo desde https://ollama.com si querés usar el ingeniero de voz."
fi

# Ejecutar el script de Python
python main.py
# python main.py --sin-gui