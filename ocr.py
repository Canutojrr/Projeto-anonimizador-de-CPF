import os
import io
import fitz  # PyMuPDF
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
import pytesseract
from PIL import Image
import cv2
import numpy as np


import multiprocessing
import time
from exceptions import CancelledOperationError

# Define o caminho para o executável Tesseract de forma dinâmica
script_dir = os.path.dirname(os.path.abspath(__file__))
tesseract_exe_path = os.path.join(script_dir, "tesseract", "tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = tesseract_exe_path

# ──────────────────────────────────────────────────────────────
# Função auxiliar para processamento de página única em paralelo
# ──────────────────────────────────────────────────────────────

def _processar_pagina_ocr(args):
    page_image_bytes, ocr_mode = args
    start_time_page = time.time()
    try:
        img_pil = Image.open(io.BytesIO(page_image_bytes))

        if ocr_mode == "grayscale":
            img_pil = img_pil.convert("L")  # 8-bit gray
        elif ocr_mode == "monochromatic":
            img_cv = np.array(img_pil.convert("L"))
            # Adiciona um filtro de ruído para remover "manchas"
            img_cv = cv2.medianBlur(img_cv, 3)
            img_bin = cv2.adaptiveThreshold(img_cv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                             cv2.THRESH_BINARY, 31, 10)
            img_pil = Image.fromarray(img_bin).convert("1")  # force 1-bit

        # Gera um PDF com camada de texto pesquisável usando o Tesseract com configuração PSM 6 (para teste)
        config_tesseract = r'--psm 6 --user-words C:\Users\canut\OneDrive\Documentos\novo_projeto\scripts\tesseract\tessdata\configs\custom_words.txt'
        pdf_bytes = pytesseract.image_to_pdf_or_hocr(img_pil, extension="pdf", lang="por", config=config_tesseract)
        end_time_page = time.time()
        return pdf_bytes, (end_time_page - start_time_page)
    except Exception as e:
        logging.error(f"Erro ao processar página OCR: {e}")
        return None, None # Retorna None em caso de erro


# ──────────────────────────────────────────────────────────────
# Função auxiliar comum para OCR
# ──────────────────────────────────────────────────────────────

def _aplicar_ocr_comum(input_pdf: str, output_pdf: str, ocr_type: str, progress_callback=None, cancel_callback=None):
    """Aplica OCR (tons de cinza ou monocromático) e salva o PDF resultante."""
    display_name = "Tons de Cinza" if ocr_type == "grayscale" else "Preto e Branco"
    try:
        doc = fitz.open(input_pdf)
        out_doc = fitz.open()
        total_pages = len(doc)

        if progress_callback:
            progress_callback.update_message(f"Iniciando OCR ({display_name}) em {total_pages} páginas...")

        page_images_data = []
        for page in doc:
            if cancel_callback:
                cancel_callback()
            pix = page.get_pixmap(colorspace=fitz.csGRAY, dpi=300)
            logging.info(f"DPI da página {page.number + 1}: X={pix.xres}, Y={pix.yres})")
            page_images_data.append((pix.tobytes("png"), ocr_type))

        if progress_callback:
            progress_callback.update_message("Iniciando processamento OCR paralelo...")

        with multiprocessing.Pool() as pool:
            results = []
            page_processing_times = []
            for i, (pdf_bytes, page_time) in enumerate(pool.imap(_processar_pagina_ocr, page_images_data)):
                if pdf_bytes is not None: # Ignora páginas que falharam no OCR
                    results.append(pdf_bytes)
                    page_processing_times.append(page_time)
                else:
                    logging.warning(f"Página {i+1} falhou no OCR e será ignorada.")
                if progress_callback:
                    progress = int(((i + 1) / total_pages) * 100)
                    progress_callback.update_progress(progress)
                    progress_callback.update_message(f"OCR concluído para {i + 1}/{total_pages} páginas ({display_name})...")

        for pdf_bytes in results:
            page_doc = fitz.open("pdf", pdf_bytes)
            out_doc.insert_pdf(page_doc)
            page_doc.close()

        out_doc.save(output_pdf, garbage=4, deflate=True, clean=True)
        out_doc.close()

        total_ocr_time = sum(page_processing_times)
        avg_page_time = total_ocr_time / len(page_processing_times) if page_processing_times else 0
        logging.info(f"OCR {display_name}: Tempo total de processamento: {total_ocr_time:.2f}s, Tempo médio por página: {avg_page_time:.2f}s")

        if progress_callback:
            progress_callback.update_message(f"OCR ({display_name}) concluído!")
        return True, f"OCR {display_name} concluído com sucesso.", output_pdf

    except Exception as e:
        msg = f"Erro no OCR ({display_name}): {e}"
        if progress_callback:
            progress_callback.update_message(msg)
        return False, msg, None

# ──────────────────────────────────────────────────────────────
# OCR tons de cinza
# ──────────────────────────────────────────────────────────────

def aplicar_ocr_grayscale(input_pdf: str, output_pdf: str, progress_callback=None, cancel_callback=None):
    """Aplica OCR em tons de cinza e salva o PDF resultante."""
    return _aplicar_ocr_comum(input_pdf, output_pdf, "grayscale", progress_callback, cancel_callback)

# ──────────────────────────────────────────────────────────────
# OCR monocromático 1‑bit
# ──────────────────────────────────────────────────────────────

def aplicar_ocr_monocromatico(input_pdf: str, output_pdf: str, progress_callback=None, cancel_callback=None):
    """Aplica OCR monocromático e salva o PDF resultante."""
    return _aplicar_ocr_comum(input_pdf, output_pdf, "monochromatic", progress_callback, cancel_callback)
