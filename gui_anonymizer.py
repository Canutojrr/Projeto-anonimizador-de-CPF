import os
import threading
import time
import tkinter.filedialog as fd
import customtkinter as ctk
from tkinter import messagebox

from anonymizer import anonymize_pdf, cpf_regex_linha_unica, cpf_regex_quebra_linha
from manual_anonymizer import anonymize_manual
from compressor import compress_pdf
from ocr import aplicar_ocr_em_pdf
from config_gui import load_config

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

config = load_config()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistema Portátil de Anonimização")
        self.geometry("820x640")
        self.resizable(True, True)
        self.cancel_event = threading.Event()

        self.pdf_paths = []
        self.termos_man = []

        self.sidebar = ctk.CTkFrame(self, width=150)
        self.sidebar.pack(side="left", fill="y")

        self.checkbox_auto = ctk.CTkCheckBox(self.sidebar, text="Auto")
        self.checkbox_manual = ctk.CTkCheckBox(self.sidebar, text="Manual")
        self.checkbox_comp = ctk.CTkCheckBox(self.sidebar, text="Comprimir")
        self.checkbox_ocr = ctk.CTkCheckBox(self.sidebar, text="OCR")

        self.checkbox_auto.pack(pady=10, anchor="w", padx=15)
        self.checkbox_manual.pack(pady=10, anchor="w", padx=15)
        self.checkbox_comp.pack(pady=10, anchor="w", padx=15)
        self.checkbox_ocr.pack(pady=10, anchor="w", padx=15)

        self.btn_cancelar = ctk.CTkButton(self.sidebar, text="Cancelar", command=self._confirmar_cancelamento)
        self.btn_cancelar.pack(pady=30, padx=10)

        self.main = ctk.CTkFrame(self)
        self.main.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.header = ctk.CTkLabel(self.main, text="Sistema Portátil de Anonimização", font=ctk.CTkFont(size=20, weight="bold"))
        self.header.pack(pady=10)

        self.btn_selecionar = ctk.CTkButton(self.main, text="Selecionar PDFs", command=self.selecionar_pdfs)
        self.btn_selecionar.pack(pady=5)

        self.lista_pdfs = ctk.CTkTextbox(self.main, height=80)
        self.lista_pdfs.pack(pady=5, fill="x")

        self.label_termos = ctk.CTkLabel(self.main, text="Termos para Anonimização Manual (1 por linha):")
        self.label_termos.pack(pady=(15, 5))

        self.caixa_termos = ctk.CTkTextbox(self.main, height=100)
        self.caixa_termos.pack(pady=5, fill="x")

        self.btn_saida = ctk.CTkButton(self.main, text="Selecionar pasta de saída", command=self.definir_saida)
        self.btn_saida.pack(pady=5)

        self.btn_executar = ctk.CTkButton(self.main, text="Executar", command=self._executar)
        self.btn_executar.pack(pady=10)

        self.barra = ctk.CTkProgressBar(self.main)
        self.barra.set(0)
        self.barra.pack(pady=5, fill="x")

        self.status = ctk.CTkLabel(self.main, text="")
        self.status.pack(pady=5)

        self.pasta_saida = config["paths"]["anonymized_pdfs"]

    def definir_saida(self):
        pasta = fd.askdirectory(title="Selecionar pasta de saída")
        if pasta:
            self.pasta_saida = pasta

    def selecionar_pdfs(self):
        arquivos = fd.askopenfilenames(title="Selecionar PDFs", filetypes=[("PDFs", "*.pdf")])
        if arquivos:
            self.pdf_paths = list(arquivos)
            self.lista_pdfs.delete("0.0", ctk.END)
            for p in self.pdf_paths:
                self.lista_pdfs.insert(ctk.END, p + "\n")

    def _confirmar_cancelamento(self):
        if messagebox.askyesno("Cancelar?", "Tem certeza que deseja cancelar o processamento?"):
            self.cancel_event.set()
            self.status.configure(text="Cancelado pelo usuário", text_color="red")

    def _executar(self):
        self.cancel_event.clear()
        threading.Thread(target=self.executar, daemon=True).start()

    def executar(self):
        if not self.pdf_paths:
            self.status.configure(text="Nenhum PDF selecionado.", text_color="red")
            return

        termos = [t.strip() for t in self.caixa_termos.get("0.0", ctk.END).splitlines() if t.strip()]

        total_paginas = self._contar_paginas_total(self.pdf_paths)
        progresso = 0
        inicio = time.time()

        for idx, pdf in enumerate(self.pdf_paths):
            if self.cancel_event.is_set(): break
            nome = os.path.splitext(os.path.basename(pdf))[0]

            auto_out = os.path.join(self.pasta_saida, nome + "_auto.pdf")
            man_out = os.path.join(self.pasta_saida, nome + "_manual.pdf")
            comp_out = os.path.join(self.pasta_saida, nome + "_comp.pdf")
            ocr_out = os.path.join(self.pasta_saida, nome + "_ocr.pdf")

            total = self._contar_paginas_total([pdf])
            progresso_local = 0

            for i in range(total):
                if self.cancel_event.is_set(): break
                time.sleep(0.01)
                progresso_local += 1
                progresso += 1
                percent = progresso / total_paginas
                self.barra.set(percent)
                elapsed = time.time() - inicio
                estimativa = (elapsed / progresso) * (total_paginas - progresso) if progresso else 0
                self.status.configure(text=f"{int(percent*100)}% - Tempo: {int(elapsed)}s - Restante: {int(estimativa)}s")

            if self.checkbox_auto.get(): anonymize_pdf(pdf, auto_out, cpf_regex_linha_unica, cpf_regex_quebra_linha)
            if self.checkbox_manual.get() and termos: anonymize_manual(pdf, man_out, termos)
            if self.checkbox_comp.get():
                base = auto_out if self.checkbox_auto.get() else pdf
                compress_pdf(base, comp_out)
            if self.checkbox_ocr.get(): aplicar_ocr_em_pdf(pdf, ocr_out)

        if not self.cancel_event.is_set():
            self.status.configure(text="Processamento finalizado!", text_color="green")

    def _contar_paginas_total(self, arquivos):
        import fitz
        total = 0
        for a in arquivos:
            with fitz.open(a) as doc:
                total += len(doc)
        return total

if __name__ == "__main__":
    app = App()
    app.mainloop()
