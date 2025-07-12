import fitz  # PyMuPDF
import os
import re
from config_gui import load_config

# REGEX 1 - CPF linha única
cpf_regex_linha_unica = re.compile(
    r'\b\d{3}\.?\s?\d{3}\.?\s?\d{3}[-–]?\s?\d{2}\b'
)

# REGEX 2 - CPF com quebra de linha
cpf_regex_quebra_linha = re.compile(
    r'(\d{3}[.\s]?\d{3}[.\s]?\d{3})(?:\s*[-–]?\s*\n\s*|\s+)(\d{2})'
)

def anonimizar_cpf_em_pagina(page, cpf_regex_linha_unica, cpf_regex_quebra_linha):
    text_instances = []

    # Extrai blocos de texto da página
    blocks = page.get_text("blocks")

    for block in blocks:
        texto = block[4]
        # Verifica CPF em linha única
        for match in cpf_regex_linha_unica.finditer(texto):
            bbox = page.search_for(match.group())
            text_instances.extend(bbox)

        # Verifica CPF com quebra de linha
        for match in cpf_regex_quebra_linha.finditer(texto):
            grupo1 = match.group(1)
            grupo2 = match.group(2)
            texto_completo = grupo1 + grupo2
            bbox = page.search_for(grupo1)
            text_instances.extend(bbox)
            bbox2 = page.search_for(grupo2)
            text_instances.extend(bbox2)

    # Aplica tarjas pretas
    for inst in text_instances:
        page.draw_rect(inst, color=(0, 0, 0), fill=(0, 0, 0))

def anonymize_pdf(input_path, output_path, cpf_regex_linha_unica, cpf_regex_quebra_linha):
    doc = fitz.open(input_path)

    for page in doc:
        anonimizar_cpf_em_pagina(page, cpf_regex_linha_unica, cpf_regex_quebra_linha)

    doc.save(output_path, garbage=4, deflate=True, clean=True, incremental=False)
    doc.close()

if __name__ == "__main__":
    config = load_config()
    input_dir = config["paths"]["input_pdfs"]
    output_dir = config["paths"]["anonymized_pdfs"]

    for nome_arquivo in os.listdir(input_dir):
        if nome_arquivo.lower().endswith(".pdf"):
            caminho_entrada = os.path.join(input_dir, nome_arquivo)
            caminho_saida = os.path.join(output_dir, f"{nome_arquivo[:-4]}_anonimizado.pdf")
            anonymize_pdf(caminho_entrada, caminho_saida, cpf_regex_linha_unica, cpf_regex_quebra_linha)
            print(f"Anonimizado: {nome_arquivo}")
