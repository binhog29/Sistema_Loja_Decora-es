#!/bin/bash

# Define as cores para a saída do terminal
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Mensagem de boas-vindas
echo -e "${GREEN}--- Iniciando o Sistema da Loja de Decorações ---${NC}"

# Verifica se o Flask está instalado
if ! command -v flask > /dev/null; then
    echo "Flask não encontrado. Instalando..."
    pip install flask
fi

# Inicia o servidor Flask
echo -e "${GREEN}Iniciando o servidor...${NC}"
echo "Acesse o seu aplicativo no navegador: http://127.0.0.1:5000"
python app.py
