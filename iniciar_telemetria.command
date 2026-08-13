#!/bin/bash

# Navegar a la carpeta del proyecto
cd "/Users/alonsoespinozacorrea/F1-22-SIM"

# Activar el entorno virtual
python3 -m venv venv
source venv/bin/activate      # o venv\Scripts\activate en Windows
pip install -r requirements.txt

# Ejecutar el script de Python
# python tests/previous_main.py
python main.py