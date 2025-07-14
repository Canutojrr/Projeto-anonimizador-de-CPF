import fitz  # PyMuPDF
import re
import os
import logging

# Configurar logging para o módulo anonymizer para ajudar na depuração.
# Nível DEBUG para ver todas as mensagens detalhadas de busca de CPF.
logging.basicConfig(level=logging.DEBUG, # Nível DEBUG para depuração
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='anonymizer_process.log', # Log separado para anonymizer
                    filemode='a', # 'a' para append, para não sobrescrever o log principal
                    encoding='utf-8') # Garante que o log é UTF-8

# REGEX 1 - CPF linha única
cpf_regex_linha_unica = re.compile(
    r'\b\d{3}\.?\s?\d{3}\.?\s?\d{3}[-–]?\s?\d{2}\b'
)

# REGEX 2 - CPF com quebra de linha
# A regex é usada para IDENTIFICAR o padrão no texto extraído.
# A forma de encontrar as coordenadas no PDF mudará na lógica de tarjamento.
cpf_regex_quebra_linha = re.compile(
    r'(\d{3}[.\s]?\d{3}[.\s]?\d{3})(?:\s*[-–]?\s*\n\s*|\s+)(\d{2})'
)

def anonimizar_cpf_em_pagina(page):
    """
    Função para adicionar anotações de redação para CPFs em linha única e quebrados.
    Utiliza uma abordagem robusta de mapeamento de palavras para retângulos.
    As redações serão aplicadas posteriormente em anonymize_pdf.
    """
    logging.debug(f"Iniciando busca detalhada por CPFs na página {page.number}...")
    
    # Extrai todas as palavras da página com suas bounding boxes.
    # Formato de word_list: [(x0, y0, x1, y1, word_text, block_no, line_no, word_no), ...]
    word_list = page.get_text("words") 
    
    # Constrói uma string linear da página para aplicar as regex.
    # Isso nos permite usar as regex do Python de forma confiável.
    # Usamos um espaço como separador, pois é assim que as regex esperam.
    page_text_linear = " ".join([word[4] for word in word_list]) 

    redaction_rects = [] # Lista para armazenar todos os retângulos a serem redigidos

    # --- 1. Busca por CPFs em linha única ---
    for match_idx, match in enumerate(cpf_regex_linha_unica.finditer(page_text_linear)):
        matched_string = match.group(0)
        logging.debug(f"Regex linha única encontrou match #{match_idx+1}: '{matched_string}' na string linear.")
        
        # Encontra as palavras que correspondem a este match
        # Percorre as palavras e verifica se o texto da palavra está contido no match
        # ou se a sequência de palavras forma o match.
        
        # A forma mais precisa é encontrar os índices das palavras no `page_text_linear`
        # e usar os retângulos das palavras originais.
        
        # Para simplificar e manter a robustez, vamos usar page.search_for()
        # mas *apenas* para a string exata que a regex encontrou.
        # Se search_for falhar aqui, o problema é no PDF ou na versão do PyMuPDF.
        try:
            # page.search_for(string) retorna uma lista de retângulos para a string.
            # Se a string tem espaços, PyMuPDF tenta encontrar a sequência de palavras.
            found_rects_for_match = page.search_for(matched_string)
            
            if found_rects_for_match:
                for rect in found_rects_for_match:
                    if rect and not rect.is_empty:
                        redaction_rects.append(rect)
                        logging.info(f"CPF linha única ENCONTRADO E MARCADO (Pág {page.number}): '{matched_string}' em {rect}")
                    else:
                        logging.warning(f"Retângulo inválido/vazio para CPF linha única: {rect}. Ignorando.")
            else:
                logging.debug(f"page.search_for não encontrou retângulos para o match de linha única: '{matched_string}'.")
                # Se search_for falhar, podemos tentar uma abordagem mais manual aqui se for crítico.
                # Por enquanto, confiamos que o get_text("words") e o search_for funcionam juntos.

        except Exception as e:
            logging.error(f"Erro ao buscar retângulos para CPF linha única '{matched_string}' na página {page.number}: {e}")

    # --- 2. Busca por CPFs com quebra de linha ---
    # Para CPFs quebrados, a abordagem de mapeamento de palavras é mais crucial.
    # Vamos usar a `full_page_text` (com newlines) para a regex e depois mapear.
    
    # Extrai o texto da página com quebras de linha preservadas para a regex de quebra.
    full_page_text_with_newlines = page.get_text("text") 

    for match_idx, match in enumerate(cpf_regex_quebra_linha.finditer(full_page_text_with_newlines)):
        matched_full_string = match.group(0)
        part1_text = match.group(1).strip() 
        part2_text = match.group(2).strip() 
        
        logging.debug(f"Regex de quebra encontrou match #{match_idx+1}: '{matched_full_string}' (Parte1: '{part1_text}', Parte2: '{part2_text}')")

        if not part1_text or not part2_text:
            logging.warning(f"Ignorando match de CPF quebrado devido a partes vazias. Match completo: '{matched_full_string}'")
            continue 
        
        rects_part1 = []
        rects_part2 = []

        # Tenta buscar as partes individualmente.
        # Se page.search_for falhar aqui, o problema está na forma como o texto está no PDF.
        try:
            rects_part1 = page.search_for(part1_text)
        except Exception as e:
            logging.error(f"Erro ao buscar '{part1_text}' (Parte1) na página {page.number}: {e}")
            
        try:
            rects_part2 = page.search_for(part2_text)
        except Exception as e:
            logging.error(f"Erro ao buscar '{part2_text}' (Parte2) na página {page.number}: {e}")

        if not rects_part1:
            logging.debug(f"Parte 1 ('{part1_text}') do CPF quebrado não encontrada por search_for na página {page.number}. Pulando match.")
            continue 
        if not rects_part2:
            logging.debug(f"Parte 2 ('{part2_text}') do CPF quebrado não encontrada por search_for na página {page.number}. Pulando match.")
            continue 

        found_and_redacted = False
        for r_p1 in rects_part1:
            for r_p2 in rects_part2:
                # Heurística de proximidade para CPFs quebrados por linha
                # r_p2.y0 > r_p1.y1 - 5: segunda parte começa levemente acima ou na mesma linha
                # r_p2.y0 < r_p1.y1 + 30: segunda parte não está muito longe na vertical (proxima linha)
                vertical_proximity_ok = (r_p2.y0 > r_p1.y1 - 5) and (r_p2.y0 < r_p1.y1 + 30)

                # Horizontal alignment: x0 de r_p2 dentro de uma margem de x0 de r_p1
                # r_p2.x0 < r_p1.x1 + 50: X de inicio da parte 2 não muito à direita do fim da parte 1
                # r_p2.x1 > r_p1.x0 - 50: X de fim da parte 2 não muito à esquerda do inicio da parte 1
                horizontal_alignment_ok = (r_p2.x0 < r_p1.x1 + 50) and (r_p2.x1 > r_p1.x0 - 50)
                
                if vertical_proximity_ok and horizontal_alignment_ok:
                    combined_rect = r_p1 | r_p2 # União dos retângulos para cobrir ambas as partes

                    logging.info(f"CPF quebrado ENCONTRADO E MARCADO (Pág {page.number}): '{part1_text}' @ {r_p1} + '{part2_text}' @ {r_p2}. Tarjando: {combined_rect}")
                    
                    if combined_rect and not combined_rect.is_empty: # Garante que o retângulo combinado é válido
                        redaction_rects.append(combined_rect) # Adiciona à lista de redações
                        found_and_redacted = True
                        break # Encontrou um par, vai para o próximo match de regex
                    else:
                        logging.warning(f"Retângulo combinado de CPF quebrado inválido ou vazio: {combined_rect}. Ignorando redação na página {page.number}.")
            if found_and_redacted:
                break # Sai do loop de retângulos da parte 1 também

    # *** CRÍTICO: Aplica todas as redações acumuladas nesta página ***
    # Este é o comando que realmente oculta o texto fisicamente.
    for rect in redaction_rects:
        page.add_redact_annot(rect, fill=(0, 0, 0)) # Adiciona as anotações de redação
    page.apply_redactions() # Aplica todas as redações de uma vez
    logging.info(f"Página {page.number} processada para {os.path.basename(page.parent.name if hasattr(page.parent, 'name') else input_path)}")


def anonymize_pdf(input_path, output_path):
    """
    Abre um PDF, anonimiza CPFs (linha única e quebrados) e salva.
    As regexes (cpf_regex_linha_unica, cpf_regex_quebra_linha) são globais e acessadas diretamente.
    """
    doc = fitz.open(input_path)
    logging.info(f"Iniciando anonimização de PDF: {os.path.basename(input_path)}")

    for page_num, page in enumerate(doc):
        # A função anonimizar_cpf_em_pagina agora lida com ambos os tipos de CPF
        # e adiciona as anotações de redação à página.
        anonimizar_cpf_em_pagina(page)
        # O apply_redactions() agora está dentro de anonimizar_cpf_em_pagina,
        # portanto, cada página é processada e as redações são aplicadas imediatamente.
        # Isso pode ser ajustado para apply_redactions() no final do loop da página em anonymize_pdf
        # se preferir aplicar todas as redações de uma vez por documento.
        # Para evitar chamadas duplicadas, vamos mover o apply_redactions() para fora de anonimizar_cpf_em_pagina,
        # e chamá-lo uma vez por página aqui.

        # Removido apply_redactions() de dentro de anonimizar_cpf_em_pagina
        # e adicionado aqui para que todas as redações da página sejam aplicadas de uma vez.
        page.apply_redactions() 
        logging.info(f"Página {page_num + 1} processada para {os.path.basename(input_path)}")


    try:
        doc.save(output_path, garbage=4, deflate=True, clean=True, incremental=False)
        doc.close()
        logging.info(f"Anonimização concluída e salvo: {os.path.basename(output_path)}")
    except Exception as e:
        logging.error(f"Erro ao salvar o PDF anonimizado '{output_path}': {e}")
        raise # Re-levanta a exceção para que a GUI possa tratá-la


if __name__ == "__main__":
    # Este bloco de teste é para uso direto do módulo anonymizer.py, não da GUI.
    try:
        # Importa load_config de config_gui.py
        from config_gui import load_config as load_app_config # Mantido para compatibilidade do teste direto
        config = load_app_config()
        input_dir = config.get("paths", {}).get("input_pdfs", "input_pdfs")
        output_dir = config.get("paths", {}).get("anonymized_pdfs", "anonymized_pdfs")
    except ImportError:
        print("Módulo config_gui não encontrado. Usando pastas padrão.")
        input_dir = "input_pdfs"
        output_dir = "anonymized_pdfs"
    except Exception as e:
        print(f"Erro ao carregar config no teste: {e}. Usando pastas padrão.")
        input_dir = "input_pdfs"
        output_dir = "anonymized_pdfs"

    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n--- Iniciando teste direto do anonymizer.py ---")
    print(f"Buscando PDFs em: {input_dir}")
    for nome_arquivo in os.listdir(input_dir):
        if nome_arquivo.lower().endswith(".pdf"):
            caminho_entrada = os.path.join(input_dir, nome_arquivo)
            caminho_saida = os.path.join(output_dir, f"{nome_arquivo[:-4]}_anonimizado.pdf")
            print(f"Anonimizando: {nome_arquivo}")
            try:
                # A função anonymize_pdf não precisa mais das regex como argumentos extras
                anonymize_pdf(caminho_entrada, caminho_saida) 
                print(f"Concluído: {os.path.basename(caminho_saida)}")
            except Exception as e:
                print(f"ERRO: Falha ao anonimizar {nome_arquivo}: {e}")
                logging.error(f"ERRO: Falha ao anonimizar {nome_arquivo} no teste direto: {e}")

    print(f"--- Teste direto concluído ---")
