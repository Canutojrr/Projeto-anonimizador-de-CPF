import subprocess
import logging

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='processamento_mono.log',
                    filemode='w')

def processar_ocr_monocromatico(input_path: str, output_path: str) -> tuple[bool, str]:
    """
    Executa o OCR em um PDF, FORÇANDO a conversão para monocromático (1-bit)
    através de argumentos explícitos para o 'unpaper' para obter a máxima compressão.
    """
    logging.info(f"Iniciando processo de OCR (FORÇANDO MONO) para: {input_path}")
    
    # Argumentos explícitos para o unpaper.
    # O '--pre-rotate' tenta corrigir a rotação, e o '--black-threshold' 
    # é um valor entre 0 e 1 que define o quão escuro um pixel precisa ser para virar preto.
    # 0.3 é um bom ponto de partida.
    unpaper_arguments = "--pre-rotate 90 --black-threshold 0.3"

    command = [
        "ocrmypdf",
        input_path,
        output_path,
        "-l", "por",
        "--output-type", "pdfa",
        "-O", "3",
        "--force-ocr",
        
        # Ativamos a limpeza para que o unpaper seja chamado
        "--clean",
        
        # =============================================================================
        # MUDANÇA CRUCIAL: Passamos os argumentos diretamente para o unpaper
        # =============================================================================
        "--unpaper-args", unpaper_arguments,
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
        
        logging.info("Processo de OCR monocromático concluído com sucesso.")
        logging.info(f"Saída do ocrmypdf:\n{result.stdout}")
        return True, f"OCR Monocromático concluído com sucesso. Salvo em: {output_path}"

    except FileNotFoundError:
        # ... (código de erro continua o mesmo) ...
        error_message = "Erro: 'ocrmypdf' ou uma de suas dependências não foi encontrado."
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

# Bloco para testes rápidos
if __name__ == '__main__':
    print("Testando a função de OCR (forçando monocromático)...")