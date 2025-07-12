import json
import os

CONFIG_FILE = "config.json"

def load_config():
    """
    Carrega o arquivo de configuração config.json.
    """
    if not os.path.exists(CONFIG_FILE):
        print("Arquivo config.json não encontrado.")
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print("Erro ao ler config.json:", e)
        return {}

def salvar_config(config, caminho=CONFIG_FILE):
    """
    Salva o dicionário de configuração no arquivo config.json.
    """
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"Configuração salva em: {caminho}")
    except Exception as e:
        print(f"Erro ao salvar configuração: {e}")

def carregar_termos_de_txt(caminho_txt):
    """
    Lê um arquivo .txt com uma expressão por linha e retorna como lista.
    """
    if not os.path.isfile(caminho_txt):
        print("Arquivo de termos não encontrado:", caminho_txt)
        return []
    try:
        with open(caminho_txt, "r", encoding="utf-8") as f:
            return [linha.strip() for linha in f if linha.strip()]
    except Exception as e:
        print(f"Erro ao carregar termos do arquivo .txt: {e}")
        return []
