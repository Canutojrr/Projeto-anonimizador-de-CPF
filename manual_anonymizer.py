# manual_anonymizer.py
# ------------------------------------------------------------------
# Oculta termos arbitrários em um PDF com tarjas pretas, mantendo
# o arquivo enxuto (deflate, limpeza de objetos) e pronto para,
# depois, ser convertido para PDF/A‑1b em tons de cinza.
# ------------------------------------------------------------------

import fitz  # PyMuPDF
import re
import os

# Pré‑compila regex opcional para caso deseje busca sem exata maiúsc‑minúsc.
# (Se não precisar, remova e use termos literais diretamente.)
def _make_regex(term):
    # Escapa metacaracteres e ignora maiúsc/minúsc.
    return re.compile(re.escape(term), flags=re.IGNORECASE)

def anonymize_manual(input_pdf_path: str,
                     output_pdf_path: str,
                     termos: list[str],
                     usar_regex: bool = False) -> None:
    """
    Aplica tarja preta sobre cada termo informado.
    • termos ........ lista de strings
    • usar_regex .... se True, converte cada termo em regex IGNORECASE
    """
    if not os.path.exists(input_pdf_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {input_pdf_path}")

    if not termos:
        raise ValueError("Lista de termos vazia.")

    # Converte termos em padrões de busca
    padroes = [_make_regex(t) for t in termos] if usar_regex else termos

    doc = fitz.open(input_pdf_path)

    for page in doc:
        texto_pagina = page.get_text()

        for idx, pad in enumerate(padroes):
            if usar_regex:
                for m in pad.finditer(texto_pagina):
                    trecho = m.group()
                    for rect in page.search_for(trecho):
                        page.add_redact_annot(rect, fill=(0, 0, 0))
            else:
                # termo literal
                encontrados = page.search_for(pad)
                for rect in encontrados:
                    page.add_redact_annot(rect, fill=(0, 0, 0))

        page.apply_redactions()

    # Salva com mesmas flags que usamos no anonymizer.py
    doc.save(
        output_pdf_path,
        garbage=4,       # remove objetos soltos
        deflate=True,    # compacta sem perdas (Flate)
        clean=True,
        incremental=False
    )
    doc.close()


# --------------------------- teste rápido --------------------------
if __name__ == "__main__":
    IN_PDF  = "exemplo.pdf"
    OUT_PDF = "exemplo_manual.pdf"
    TERMOS  = ["João da Silva", "12345678900"]

    anonymize_manual(IN_PDF, OUT_PDF, TERMOS)
    print("Anonimização manual concluída.")
