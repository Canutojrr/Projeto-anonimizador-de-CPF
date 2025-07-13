# --- Início do teste_final.py (com caminhos corrigidos) ---

print("--- INICIANDO TESTE FINAL E DEFINITIVO ---")

import subprocess
import logging
import os
import fitz  # PyMuPDF
from PIL import Image
import io

# Configuração do logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='teste_final.log',
                    filemode='w')

def _binarize_pdf(input_path: str, temp_output_path: str, dpi: int = 300):
    """ETAPA 1: Converte um PDF para um novo PDF com imagens monocromáticas (1-bit)."""
    logging.info(f"[TESTE FINAL] Iniciando binarização para: {os.path.basename(input_path)}")
    source_doc = fitz.open(input_path)
    output_doc = fitz.open()
    for page in source_doc:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert('1', dither=Image.Dither.FLOYDSTEINBERG)
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(page.rect, stream=img_buffer.getvalue())
    output_doc.save(temp_output_path)
    output_doc.close()
    source_doc.close()
    logging.info(f"[TESTE FINAL] Binarização concluída: {os.path.basename(temp_output_path)}")

def _run_ocr(input_file: str, output_file: str):
    """ETAPA 2: Executa o ocrmypdf no arquivo de entrada, confiando no PATH do sistema."""
    logging.info(f"[TESTE FINAL] Iniciando OCR em: {os.path.basename(input_file)}")
    
    command = [
        "ocrmypdf", input_file, output_file,
        "-l", "por",
        "--output-type", "pdfa",
        "-O", "1", 
        "--force-ocr",
    ]
    try:
        logging.info(f"[TESTE FINAL] Executando comando: {' '.join(command)}")
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        logging.info("[TESTE FINAL] Processo de OCR concluído com sucesso.")
        logging.info(f"[TESTE FINAL] Saída do ocrmypdf:\n{result.stdout}")
    except Exception as e:
        logging.error(f"[TESTE FINAL] Falha na etapa de OCR do ocrmypdf: {e}")
        raise e

def run_full_ocr_pipeline(input_path: str, final_output_path: str, mode: str) -> tuple[bool, str]:
    """Orquestra a pipeline de OCR, escolhendo o modo 'mono' ou 'grayscale'."""
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    
    if mode == 'mono':
        temp_binarized_path = os.path.join(os.path.dirname(input_path), f"{base_name}_temp_binarized.pdf")
        try:
            print(f"Etapa 1/2: Convertendo para P&B - {base_name}")
            _binarize_pdf(input_path, temp_binarized_path)
            
            print(f"Etapa 2/2: Aplicando OCR - {base_name}")
            _run_ocr(temp_binarized_path, final_output_path)
            
            return True, f"Pipeline 'Mono' concluída! Salvo em: {final_output_path}"
        except Exception as e:
            return False, f"Erro na pipeline 'Mono': {e}"
        finally:
            if 'temp_binarized_path' in locals() and os.path.exists(temp_binarized_path):
                os.remove(temp_binarized_path)
    elif mode == 'grayscale':
        try:
            print(f"Executando OCR em Tons de Cinza - {base_name}")
            _run_ocr(input_path, final_output_path)
            return True, f"Pipeline 'Grayscale' concluída! Salvo em: {final_output_path}"
        except Exception as e:
            return False, f"Erro na pipeline 'Grayscale': {e}"
    else:
        return False, f"Modo '{mode}' desconhecido. Use 'mono' ou 'grayscale'."

# --- PONTO DE PARTIDA DO TESTE ---
if __name__ == '__main__':
    print("--- BLOCO DE EXECUÇÃO PRINCIPAL DO TESTE FINAL ---")
    
    # =============================================================================
    # CAMINHOS CORRIGIDOS PARA APONTAR PARA A PASTA CORRETA
    # =============================================================================
    caminho_do_seu_pdf = "D:/Documentos/maio/MAIO.pdf"
    caminho_saida_mono = "D:/Documentos/maio/saida_teste_mono.pdf"
    caminho_saida_gray = "D:/Documentos/maio/saida_teste_gray.pdf"
    
    if not os.path.exists(caminho_do_seu_pdf):
        print(f"ERRO: O ficheiro de entrada não foi encontrado em: {caminho_do_seu_pdf}")
        print("Por favor, certifique-se de que o caminho está correto e o ficheiro existe.")
    else:
        print("\n--- TESTANDO MODO MONOCROMÁTICO (ALTA COMPRESSÃO) ---")
        sucesso_mono, msg_mono = run_full_ocr_pipeline(caminho_do_seu_pdf, caminho_saida_mono, mode='mono')
        print(f"Resultado Mono: {sucesso_mono} - Mensagem: {msg_mono}")
        
        print("\n--- TESTANDO MODO GRAYSCALE (PADRÃO) ---")
        sucesso_gray, msg_gray = run_full_ocr_pipeline(caminho_do_seu_pdf, caminho_saida_gray, mode='grayscale')
        print(f"Resultado Grayscale: {sucesso_gray} - Mensagem: {msg_gray}")

    print("\n--- TESTE FINAL CONCLUÍDO ---")
