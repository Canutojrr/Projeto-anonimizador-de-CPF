import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from anonymizer import anonymize_pdf, cpf_regex_linha_unica, cpf_regex_quebra_linha
from manual_anonymizer import anonymize_by_text
from compressor import compress_pdf_to_pdfa

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def carregar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config
    else:
        return {
            "paths": {
                "input_pdfs": "../input_pdfs",
                "anonymized_pdfs": "../anonymized_pdfs",
                "compressed_pdfs": "../compressed_pdfs",
                "manual_targets": "../manual_targets"
            }
        }

def salvar_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def selecionar_arquivos(diretorio_padrao):
    arquivos = filedialog.askopenfilenames(
        initialdir=diretorio_padrao,
        title="Selecione arquivos PDF",
        filetypes=[("PDF Files", "*.pdf")]
    )
    return list(arquivos)

def executar_anonymizacao_automatica(config, arquivos):
    for arquivo in arquivos:
        nome_arquivo = os.path.basename(arquivo)
        destino = os.path.join(config["paths"]["anonymized_pdfs"], nome_arquivo.replace(".pdf", "_anonimizado.pdf"))
        anonymize_pdf(arquivo, destino, cpf_regex_linha_unica, cpf_regex_quebra_linha)
    messagebox.showinfo("Concluído", f"Anonimização automática concluída para {len(arquivos)} arquivo(s).")

def executar_anonymizacao_manual(config, arquivos, textos):
    for arquivo in arquivos:
        nome_arquivo = os.path.basename(arquivo)
        destino = os.path.join(config["paths"]["anonymized_pdfs"], nome_arquivo.replace(".pdf", "_manual_anonimizado.pdf"))
        anonymize_by_text(arquivo, destino, textos)
    messagebox.showinfo("Concluído", f"Anonimização manual concluída para {len(arquivos)} arquivo(s).")

def executar_compressao(config, arquivos):
    for arquivo in arquivos:
        nome_arquivo = os.path.basename(arquivo)
        destino = os.path.join(config["paths"]["compressed_pdfs"], nome_arquivo.replace(".pdf", "_comprimido.pdf"))
        compress_pdf_to_pdfa(arquivo, destino)
    messagebox.showinfo("Concluído", f"Compressão concluída para {len(arquivos)} arquivo(s).")

def run_gui():
    config = carregar_config()

    # Tema customizado: "dark-blue"
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    root.title("Sistema de Anonimização de PDFs")
    root.geometry("700x500")

    frame = ctk.CTkFrame(root, corner_radius=10)
    frame.pack(padx=20, pady=20, fill="both", expand=True)

    ctk.CTkLabel(frame, text="Caminhos configurados:", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0,10))
    for key, path in config["paths"].items():
        ctk.CTkLabel(frame, text=f"{key.replace('_', ' ').title()}: {path}").pack(anchor="w")

    arquivos_selecionados = []

    def btn_selecionar_pdfs():
        nonlocal arquivos_selecionados
        arquivos_selecionados = selecionar_arquivos(config["paths"]["input_pdfs"])
        if arquivos_selecionados:
            lbl_arquivos.config(text=f"{len(arquivos_selecionados)} arquivo(s) selecionado(s)")
        else:
            lbl_arquivos.config(text="Nenhum arquivo selecionado")

    lbl_arquivos = ctk.CTkLabel(frame, text="Nenhum arquivo selecionado")
    lbl_arquivos.pack(pady=10)

    ctk.CTkButton(frame, text="Selecionar arquivos PDF", command=btn_selecionar_pdfs).pack(pady=5)

    lbl_manual = ctk.CTkLabel(frame, text="Textos para anonimização manual (separados por vírgula):")
    lbl_manual.pack(pady=(20, 5))
    entry_manual = ctk.CTkEntry(frame, width=500)
    entry_manual.pack()

    def executar_processo():
        if not arquivos_selecionados:
            messagebox.showwarning("Aviso", "Selecione pelo menos um arquivo PDF.")
            return

        textos_para_anonimizar = [t.strip() for t in entry_manual.get().split(",") if t.strip()]

        if textos_para_anonimizar:
            executar_anonymizacao_manual(config, arquivos_selecionados, textos_para_anonimizar)
        else:
            executar_anonymizacao_automatica(config, arquivos_selecionados)

    ctk.CTkButton(frame, text="Executar Anonimização", command=executar_processo).pack(pady=15)

    def btn_comprimir():
        if not arquivos_selecionados:
            messagebox.showwarning("Aviso", "Selecione pelo menos um arquivo PDF.")
            return
        executar_compressao(config, arquivos_selecionados)

    ctk.CTkButton(frame, text="Comprimir PDFs", command=btn_comprimir).pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    run_gui()
