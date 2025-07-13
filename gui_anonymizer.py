import os
import threading
import time
import tkinter.filedialog as fd
import customtkinter as ctk
from tkinter import messagebox
import fitz
import shutil

# --- Importações dos seus módulos ---
from anonymizer import anonymize_pdf, cpf_regex_linha_unica, cpf_regex_quebra_linha
from manual_anonymizer import anonymize_manual
from compressor import compress_pdf
from config_gui import load_config
from ocr_pipeline import run_full_ocr_pipeline

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

try:
    config = load_config()
    initial_path = config["paths"]["anonymized_pdfs"]
except (FileNotFoundError, KeyError):
    initial_path = os.path.expanduser("~/Desktop")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistema Portátil de Anonimização")
        self.geometry("820x640")
        self.resizable(True, True)
        self.cancel_event = threading.Event()
        self.pdf_paths = []
        self.pasta_saida = initial_path
        self.progress_window = None # Para a nova janela de progresso

        self.sidebar = ctk.CTkFrame(self, width=150)
        self.sidebar.pack(side="left", fill="y")

        # =============================================================================
        # CHECKBOXES REORDENADAS SEGUINDO A LÓGICA DA PIPELINE
        # =============================================================================
        self.checkbox_ocr = ctk.CTkCheckBox(self.sidebar, text="OCR Padrão (Grayscale)")
        self.checkbox_mono = ctk.CTkCheckBox(self.sidebar, text="OCR Mono (Alta Compressão)")
        self.checkbox_auto = ctk.CTkCheckBox(self.sidebar, text="Auto (CPF)")
        self.checkbox_manual = ctk.CTkCheckBox(self.sidebar, text="Manual (Termos)")
        self.checkbox_comp = ctk.CTkCheckBox(self.sidebar, text="Comprimir")

        # Ordem de exibição na tela
        self.checkbox_ocr.pack(pady=10, anchor="w", padx=15)
        self.checkbox_mono.pack(pady=10, anchor="w", padx=15)
        self.checkbox_auto.pack(pady=10, anchor="w", padx=15)
        self.checkbox_manual.pack(pady=10, anchor="w", padx=15)
        self.checkbox_comp.pack(pady=10, anchor="w", padx=15)
        
        self.btn_cancelar = ctk.CTkButton(self.sidebar, text="Cancelar Processo", command=self._confirmar_cancelamento)
        self.btn_cancelar.pack(pady=30, padx=10)

        # --- Painel Principal (sem alterações de layout) ---
        self.main = ctk.CTkFrame(self)
        self.main.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.header = ctk.CTkLabel(self.main, text="Sistema Portátil de Anonimização", font=ctk.CTkFont(size=20, weight="bold"))
        self.header.pack(pady=10)
        self.btn_selecionar = ctk.CTkButton(self.main, text="Selecionar PDFs", command=self.selecionar_pdfs)
        self.btn_selecionar.pack(pady=5)
        self.lista_pdfs = ctk.CTkTextbox(self.main, height=120)
        self.lista_pdfs.pack(pady=5, fill="x")
        self.label_termos = ctk.CTkLabel(self.main, text="Termos para Anonimização Manual (1 por linha):")
        self.label_termos.pack(pady=(15, 5))
        self.caixa_termos = ctk.CTkTextbox(self.main, height=150)
        self.caixa_termos.pack(pady=5, fill="x")
        self.btn_saida = ctk.CTkButton(self.main, text="Selecionar pasta de saída", command=self.definir_saida)
        self.btn_saida.pack(pady=5)
        self.btn_executar = ctk.CTkButton(self.main, text="Executar", command=self._executar)
        self.btn_executar.pack(pady=10)
        
    def _create_progress_window(self):
        """Cria a nova janela pop-up de progresso."""
        self.progress_window = ctk.CTkToplevel(self)
        self.progress_window.title("Progresso")
        self.progress_window.geometry("500x200")
        self.progress_window.transient(self) # Mantém a janela na frente da principal
        self.progress_window.protocol("WM_DELETE_WINDOW", lambda: None) # Impede de fechar pelo "X"
        self.progress_window.grid_columnconfigure(0, weight=1)

        self.pw_status_label = ctk.CTkLabel(self.progress_window, text="Iniciando...", wraplength=450)
        self.pw_status_label.grid(row=0, column=0, padx=20, pady=10, sticky="ew")

        self.pw_progress_bar = ctk.CTkProgressBar(self.progress_window)
        self.pw_progress_bar.set(0)
        self.pw_progress_bar.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.pw_percentage_label = ctk.CTkLabel(self.progress_window, text="0%")
        self.pw_percentage_label.grid(row=2, column=0, padx=20, pady=5)
        
        self.pw_time_label = ctk.CTkLabel(self.progress_window, text="Tempo decorrido: 0s | Tempo restante: -")
        self.pw_time_label.grid(row=3, column=0, padx=20, pady=10)

    def _update_progress(self, status_msg, progress_val, elapsed_time):
        """Atualiza todos os widgets na janela de progresso."""
        self.pw_status_label.configure(text=status_msg)
        self.pw_progress_bar.set(progress_val)
        percentage = int(progress_val * 100)
        self.pw_percentage_label.configure(text=f"{percentage}%")
        
        if progress_val > 0:
            total_time_estimated = elapsed_time / progress_val
            remaining_time = total_time_estimated - elapsed_time
            self.pw_time_label.configure(text=f"Tempo decorrido: {int(elapsed_time)}s | Tempo restante: {int(remaining_time)}s")
        else:
            self.pw_time_label.configure(text=f"Tempo decorrido: {int(elapsed_time)}s | Tempo restante: Calculando...")

    def definir_saida(self):
        pasta = fd.askdirectory(title="Selecionar pasta de saída")
        if pasta: self.pasta_saida = pasta

    def selecionar_pdfs(self):
        arquivos = fd.askopenfilenames(title="Selecionar PDFs", filetypes=[("PDFs", "*.pdf")])
        if arquivos:
            self.pdf_paths = list(arquivos)
            self.lista_pdfs.delete("0.0", ctk.END)
            for p in self.pdf_paths: self.lista_pdfs.insert(ctk.END, os.path.basename(p) + "\n")

    def _confirmar_cancelamento(self):
        if self.progress_window and self.progress_window.winfo_exists():
            if messagebox.askyesno("Cancelar?", "Tem certeza?"):
                self.cancel_event.set()
        else:
            messagebox.showinfo("Info", "O processo não está em execução.")

    def _executar(self):
        if not self.pdf_paths:
            messagebox.showerror("Erro", "Nenhum PDF selecionado.")
            return
        
        self.cancel_event.clear()
        self.btn_executar.configure(state="disabled")
        self._create_progress_window()
        threading.Thread(target=self.executar_pipeline, daemon=True).start()

    def executar_pipeline(self):
        termos = [t.strip() for t in self.caixa_termos.get("0.0", ctk.END).splitlines() if t.strip()]
        total_de_arquivos = len(self.pdf_paths)
        start_time = time.time()
        
        for i, pdf_original in enumerate(self.pdf_paths):
            if self.cancel_event.is_set():
                self._update_progress("Processo cancelado pelo usuário!", (i + 1) / total_de_arquivos, time.time() - start_time)
                break

            nome_base = os.path.splitext(os.path.basename(pdf_original))[0]
            self._update_progress(f"Iniciando arquivo {i+1}/{total_de_arquivos}: {nome_base}.pdf", i / total_de_arquivos, time.time() - start_time)
            
            caminho_atual = pdf_original
            arquivos_temporarios = []
            
            try:
                # --- ETAPA 1: OCR ---
                if self.checkbox_mono.get() or self.checkbox_ocr.get():
                    modo_ocr = 'mono' if self.checkbox_mono.get() else 'grayscale'
                    saida_ocr = os.path.join(self.pasta_saida, f"{nome_base}_temp_ocr.pdf")
                    arquivos_temporarios.append(saida_ocr)
                    
                    def ocr_status_callback(msg):
                        self._update_progress(msg, (i + 0.2) / total_de_arquivos, time.time() - start_time)
                    
                    sucesso, msg_retorno = run_full_ocr_pipeline(caminho_atual, saida_ocr, mode=modo_ocr, status_callback=ocr_status_callback)
                    if not sucesso: raise Exception(msg_retorno)
                    caminho_atual = saida_ocr

                # --- ETAPA 2: ANONIMIZAÇÃO AUTOMÁTICA (CPF) ---
                if self.checkbox_auto.get():
                    saida_auto = os.path.join(self.pasta_saida, f"{nome_base}_temp_auto.pdf")
                    arquivos_temporarios.append(saida_auto)
                    self._update_progress(f"Anonimizando CPFs em {nome_base}...", (i + 0.6) / total_de_arquivos, time.time() - start_time)
                    anonymize_pdf(caminho_atual, saida_auto, cpf_regex_linha_unica, cpf_regex_quebra_linha)
                    caminho_atual = saida_auto

                # --- ETAPA 3: ANONIMIZAÇÃO MANUAL (TERMOS) ---
                if self.checkbox_manual.get() and termos:
                    saida_manual = os.path.join(self.pasta_saida, f"{nome_base}_temp_manual.pdf")
                    arquivos_temporarios.append(saida_manual)
                    self._update_progress(f"Anonimizando termos manuais...", (i + 0.8) / total_de_arquivos, time.time() - start_time)
                    anonymize_manual(caminho_atual, saida_manual, termos)
                    caminho_atual = saida_manual

                # --- ETAPA 4: COMPRESSÃO ---
                if self.checkbox_comp.get():
                    # A compressão final é inerente ao salvamento, mas podemos forçar uma re-escrita limpa
                    saida_comp = os.path.join(self.pasta_saida, f"{nome_base}_temp_comp.pdf")
                    arquivos_temporarios.append(saida_comp)
                    self._update_progress(f"Finalizando e comprimindo...", (i + 0.9) / total_de_arquivos, time.time() - start_time)
                    compress_pdf(caminho_atual, saida_comp)
                    caminho_atual = saida_comp

                # --- FINALIZAÇÃO ---
                nome_final = os.path.join(self.pasta_saida, f"{nome_base}_PROCESSADO.pdf")
                if not arquivos_temporarios:
                    shutil.copy(caminho_atual, nome_final)
                else:
                    shutil.move(caminho_atual, nome_final)
                
            except Exception as e:
                self._update_progress(f"Erro ao processar {nome_base}: {e}", i / total_de_arquivos, time.time() - start_time)
                messagebox.showerror("Erro", f"Falha ao processar {nome_base}:\n{e}")
            finally:
                for temp_file in arquivos_temporarios:
                    if os.path.exists(temp_file) and temp_file != caminho_atual:
                        try: os.remove(temp_file)
                        except OSError as e_remove: print(f"Erro ao remover temp: {e_remove}")
            
            self._update_progress(f"Arquivo {i+1}/{total_de_arquivos} concluído.", (i + 1) / total_de_arquivos, time.time() - start_time)
            time.sleep(1)

        if not self.cancel_event.is_set():
            self._update_progress("Todos os arquivos foram processados!", 1, time.time() - start_time)
        
        self.progress_window.destroy()
        self.btn_executar.configure(state="normal")

if __name__ == "__main__":
    app = App()
    app.mainloop()