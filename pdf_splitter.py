import fitz  # PyMuPDF
import os
import re
import traceback
from exceptions import CancelledOperationError
import argparse

# --- Funções Auxiliares (Comuns para ambas as estratégias) ---

def sanitizar_nome_arquivo(nome):
    """Remove caracteres inválidos, partes indesejadas e normaliza o case do nome de um arquivo."""
    # 1. Remove a parte da descrição (ex: ", de 01 de janeiro" ou "- Dispõe sobre...")
    # Procura por padrões comuns que iniciam a descrição.
    match = re.search(r'\s*,\s*de|\s*-\s', nome)
    if match:
        nome = nome[:match.start()]

    # 2. Remove 'nº' e suas variações (N.º, n°, n2, na, n", etc.)
    nome = re.sub(r'\s*n[°º."~2ae“]?\s*', ' ', nome, flags=re.IGNORECASE)

    # 3. Substitui barras por hífens
    nome = nome.replace('/', '-')

    # 4. Limpa espaços múltiplos e caracteres de arquivo inválidos
    nome = re.sub(r'\s+', ' ', nome).strip()
    nome = nome.replace(',', '') # Remove vírgulas
    nome = re.sub(r'[/:*?"<>|\r\n]', '', nome)

    # 5. Normaliza o case da primeira palavra, preservando o restante (ex: GD).
    partes = nome.split(' ', 1)
    if len(partes) > 0:
        partes[0] = partes[0].capitalize()
        nome = ' '.join(partes)

    return nome.strip()

def converter_ano_2_para_4_digitos(ano_str):
    """Converte um ano de 2 dígitos para 4 dígitos usando a lógica salva."""
    if len(ano_str) == 2:
        ano_int = int(ano_str)
        if ano_int > 50:  # Lógica salva: anos > 50 são do século 20 (19xx)
            return str(1900 + ano_int)
        else:  # Lógica salva: anos <= 50 são do século 21 (20xx)
            return str(2000 + ano_int)
    return ano_str  # Retorna o ano original se já tiver 4 dígitos

def extrair_nome_portaria(doc_original, inicio_pagina):
    texto_pagina = doc_original.load_page(inicio_pagina).get_text("text", sort=True)
    try:
        # Nova estratégia de regex: busca por Portaria e o padrão de número/ano.
        # A expressão foi modificada para ser mais flexível com quebras de linha no título.
        # Usamos [\s\S]{0,80}? para permitir que a busca continue por até 80 caracteres, mesmo que haja quebras de linha,
        # o que torna a detecção mais robusta contra variações de formatação do OCR.
        padrao = re.compile(r"(\bPortaria[\s\S]{0,80}?\d+[/-]\d{2,4}(?:-[^,\n\r]+)?[^,\n\r]*)", re.IGNORECASE)
        match = padrao.search(texto_pagina)
        
        if match:
            nome_bruto = match.group(1).strip()
            nome_sanitizado = sanitizar_nome_arquivo(nome_bruto)
            
            # A lógica de conversão de ano continua a mesma
            num_ano_match = re.search(r'(\d+)[/-](\d{2})', nome_sanitizado)
            if num_ano_match:
                num, ano = num_ano_match.groups()
                ano_4_digitos = converter_ano_2_para_4_digitos(ano)
                # Garante que a substituição seja feita no formato correto
                nome_sanitizado = re.sub(r'([/-])' + ano + r'\b', r'\g<1>' + ano_4_digitos, nome_sanitizado)

            return nome_sanitizado
        else:
            # Bloco de Debug: Salva o texto que falhou em um arquivo para análise
            try:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                debug_filename = f"debug_texto_falhou_{timestamp}.txt"
                # Salva o arquivo de debug no mesmo diretório do script
                script_dir = os.path.dirname(os.path.abspath(__file__))
                caminho_debug = os.path.join(script_dir, debug_filename)
                
                with open(caminho_debug, "w", encoding="utf-8") as f:
                    f.write("--- INÍCIO DO TEXTO DA PÁGINA QUE FALHOU ---\n\n")
                    f.write(texto_pagina)
                    f.write("\n\n--- FIM DO TEXTO ---")
                
                print(f"DEBUG: Padrão de portaria não encontrado. O texto da página foi salvo em: {caminho_debug}")

            except Exception as debug_e:
                print(f"DEBUG: Falha ao salvar o arquivo de debug: {debug_e}")
            
            print(f"DEBUG: No match found for portaria pattern in texto_pagina: {texto_pagina[:100]}")
            print(f"DEBUG: Full texto_pagina content:\n---\n{texto_pagina}\n---")
    except Exception as e:
        print(f"Erro ao extrair nome da portaria: {e}")
    return None





def normalizar_texto(texto):
    """Remove acentos, espaços extras e converte para minúsculas."""
    texto = texto.lower()
    texto = ' '.join(texto.split())
    return texto

# --- Estratégia de Divisão por Texto ---

def dividir_pdf_por_texto(caminho_pdf, textos_chave_com_sensibilidade, diretorio_saida, callback_progresso=None, cancel_callback=None):
    """
    Divide um PDF com base na presença de textos_chave em uma página.
    """
    try:
        os.makedirs(diretorio_saida, exist_ok=True)
        
        doc_original = fitz.open(caminho_pdf)
        if doc_original.page_count == 0:
            print(f"Aviso: O arquivo {caminho_pdf} está vazio ou corrompido.")
            if callback_progresso:
                callback_progresso(100, "Erro: Arquivo vazio ou corrompido.")
            return []

        pontos_de_corte = []
        total_paginas = doc_original.page_count
        for num_pagina in range(total_paginas):
            if cancel_callback:
                cancel_callback()
            if callback_progresso:
                progresso = int(((num_pagina + 1) / total_paginas) * 50) # 50% para a detecção
                callback_progresso.update_progress(progresso)
                callback_progresso.update_message(f"Analisando página {num_pagina + 1}/{total_paginas}...")

            pagina = doc_original.load_page(num_pagina)
            texto_pagina_original = pagina.get_text("text", sort=True)
            texto_pagina_normalizado = normalizar_texto(texto_pagina_original)

            any_pattern_found = False
            for pattern_string, is_case_sensitive in textos_chave_com_sensibilidade:
                text_to_search = texto_pagina_original if is_case_sensitive else texto_pagina_normalizado
                pattern_to_search = pattern_string if is_case_sensitive else normalizar_texto(pattern_string)
                
                if re.search(pattern_to_search, text_to_search):
                    any_pattern_found = True
                    break # Encontrou um, não precisa verificar os outros nesta página
            
            if any_pattern_found:
                pontos_de_corte.append(num_pagina)

        if not pontos_de_corte:
            print(f"Aviso: Nenhum dos textos_chave foi encontrado em {caminho_pdf} para permitir a divisão.")
            if callback_progresso:
                callback_progresso.update_progress(100)
                callback_progresso.update_message("Aviso: Nenhum padrão encontrado para divisão.")
            return [caminho_pdf]

        arquivos_gerados = []
        nome_base_original_pdf = os.path.splitext(os.path.basename(caminho_pdf))[0]

        # Garante que a primeira página seja sempre um ponto de corte se não foi detectada
        if 0 not in pontos_de_corte:
            pontos_de_corte.insert(0, 0)

        total_partes = len(pontos_de_corte)
        for i, inicio_pagina in enumerate(pontos_de_corte):
            fim_pagina = pontos_de_corte[i + 1] - 1 if i + 1 < len(pontos_de_corte) else doc_original.page_count - 1
            
            if inicio_pagina > fim_pagina:
                continue

            pagina_inicio_doc = doc_original.load_page(inicio_pagina)
            texto_inicio_doc = pagina_inicio_doc.get_text("text", sort=True) # Corrected indentation here
            nome_arquivo_extraido = extrair_nome_portaria(doc_original, inicio_pagina)
            
            nome_final_arquivo = nome_arquivo_extraido if nome_arquivo_extraido else f"{nome_base_original_pdf}_parte_{i + 1}"

            doc_novo = fitz.open()
            doc_novo.insert_pdf(doc_original, from_page=inicio_pagina, to_page=fim_pagina)
            
            caminho_saida_parte = os.path.join(diretorio_saida, f"{nome_final_arquivo}.pdf")
            doc_novo.save(caminho_saida_parte, garbage=4, deflate=True, clean=True)
            doc_novo.close()
            
            arquivos_gerados.append(caminho_saida_parte)

            if callback_progresso:
                progresso = 50 + int(((i + 1) / total_partes) * 50) # 50% para a criação dos arquivos
                callback_progresso.update_progress(progresso)
                callback_progresso.update_message(f"Criando parte {i + 1}/{total_partes}...")


        doc_original.close()
        print(f"PDF dividido com sucesso em {len(arquivos_gerados)} partes.")
        if callback_progresso:
            callback_progresso.update_progress(100)
            callback_progresso.update_message(f"Divisão concluída: {len(arquivos_gerados)} partes geradas.")
        return arquivos_gerados

    except Exception as e:
        print(f"Ocorreu um erro inesperado ao dividir por texto: {e}")
        traceback.print_exc()
        if callback_progresso:
            callback_progresso.update_progress(100)
            callback_progresso.update_message(f"Erro: {e}")
        return []