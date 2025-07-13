import subprocess
import logging

# Configuração do logging para registrar informações em um arquivo.
# O modo 'w' (write) limpa o log a cada nova execução.
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='processamento.log',
                    filemode='w')

def processar_ocr_para_arquivamento(input_path: str, output_path: str) -> tuple[bool, str]:
    """
    Executa o OCR em um PDF usando ocrmypdf com configurações modernas e
    otimizadas para atender às especificações de arquivamento digital (AFD).

    Args:
        input_path (str): Caminho para o PDF de entrada (digitalizado sem OCR).
        output_path (str): Caminho para salvar o PDF final processado.

    Returns:
        tuple[bool, str]: Uma tupla contendo (True/False para sucesso, mensagem de status).
    """
    logging.info(f"Iniciando processo de OCR para o arquivo: {input_path}")
    
    command = [
        "ocrmypdf",
        
        # Arquivos de entrada e saída
        input_path,
        output_path,
        
        # --- Configurações de Conformidade e Qualidade ---
        "-l", "por",                          # Define o idioma para o Tesseract
        "--output-type", "pdfa",              # Garante a saída no formato PDF/A (padrão recomendado)
        
        # --- Configurações de Otimização e Compressão ---
        # -O é o atalho para --optimize. Nível 3 é o máximo.
        # Para PDF/A, o ocrmypdf já seleciona a melhor compressão SEM PERDAS
        # (lossless) por padrão, como JBIG2 para P&B e ZIP/Flate para outros.
        "-O", "3",       
        
        # --- Configurações de Imagem ---
        "--image-dpi", "300",                 # Força a resolução da imagem, caso o PDF não informe
        "--clean",                            # Usa o 'unpaper' para limpar a imagem antes do OCR
        
        # --- Configurações de Execução ---
        "--force-ocr",                        # Força o OCR mesmo que o arquivo já tenha algum texto
        # A flag '--skip-text' foi removida para resolver o conflito com '--force-ocr'
        "--tesseract-timeout", "600",         # Aumenta o tempo limite para páginas complexas
    ]

    try:
        logging.info(f"Executando comando: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        logging.info("Processo de OCR concluído com sucesso.")
        logging.info(f"Saída do ocrmypdf:\n{result.stdout}")
        return True, f"OCR e otimização concluídos com sucesso. Salvo em: {output_path}"

    except FileNotFoundError:
        error_message = "Erro: 'ocrmypdf' não encontrado. Verifique se ele está instalado e no PATH do sistema."
        logging.error(error_message)
        return False, error_message
        
    except subprocess.CalledProcessError as e:
        error_message = f"Erro durante a execução do ocrmypdf: {e.stderr}"
        logging.error(error_message)
        return False, error_message

    except Exception as e:
        error_message = f"Um erro inesperado ocorreu: {str(e)}"
        logging.error(error_message)
        return False, error_message

# Bloco para testes rápidos e diretos do script
if __name__ == '__main__':
    print("Testando a função de OCR (versão final corrigida)...")
    # Para testar, descomente as linhas abaixo e substitua com caminhos reais
    # input_pdf = "caminho/para/seu/pdf_sem_ocr.pdf"
    # output_pdf = "caminho/para/seu/pdf_com_ocr.pdf"
    # success, message = processar_ocr_para_arquivamento(input_pdf, output_pdf)
    # print(f"Resultado: {success}\nMensagem: {message}")