import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
from config_gui import load_config

def aplicar_ocr_em_pdf(input_path, output_path=None):
    """
    Aplica OCR em um PDF digitalizado (baseado em imagens) e salva em PDF/A-1b com compressão leve.
    """
    config = load_config()
    tesseract_path = config["paths"].get("tesseract_path", "tesseract/tesseract.exe")
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

    if not os.path.isfile(input_path):
        print(f"Arquivo não encontrado: {input_path}")
        return

    doc = fitz.open(input_path)
    pdf_ocr = fitz.open()  # Novo PDF com OCR

    for page in doc:
        pix = page.get_pixmap(dpi=300, colorspace=fitz.csGRAY)  # Imagem em tons de cinza
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes))

        # Aplicando OCR com pytesseract
        texto_ocr = pytesseract.image_to_pdf_or_hocr(img, extension='pdf')

        # Inserir a página OCR como imagem com texto reconhecido
        ocr_page = fitz.open("pdf", texto_ocr)
        pdf_ocr.insert_pdf(ocr_page)

    # Definindo nome de saída
    if not output_path:
        base, ext = os.path.splitext(input_path)
        output_path = base + "_ocr.pdf"

    # Salvar com compactação e compatibilidade PDF/A-1b
    pdf_ocr.save(output_path, garbage=4, deflate=True, clean=True, incremental=False, encryption=0)
    pdf_ocr.close()
    print(f"OCR aplicado e salvo em: {output_path}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Aplicar OCR em PDFs digitalizados")
    parser.add_argument("input_pdf", help="Caminho para o PDF digitalizado")
    parser.add_argument("-o", "--output", help="Caminho do PDF OCR de saída (opcional)")
    args = parser.parse_args()

    aplicar_ocr_em_pdf(args.input_pdf, args.output)
