import os
import threading
import time
import tkinter.filedialog as fd
import customtkinter as ctk
from tkinter import messagebox
import fitz  # PyMuPDF
import shutil
import subprocess
import logging
from PIL import Image
import io

# --- Importações dos seus módulos ---
# Certifique-se de que esses arquivos .py estão na mesma pasta
from anonymizer import anonymize_pdf, cpf_regex_linha_unica, cpf_regex_quebra_linha
from manual_anonymizer import anonymize_manual
from compressor import compress_pdf  # Assumindo que compressor.py tem uma função compress_pdf
from config_gui import load_config  # Usar o load_config de config_gui.py

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

try:
    config = load_config()
    # Tenta usar o caminho de "anonymized_pdfs" do config.json, se existir.
    # Caso contrário, usa o Desktop como padrão.
    initial_path = config.get("paths", {}).get("anonymized_pdfs", os.path.expanduser("~/Desktop"))
except (FileNotFoundError, KeyError):
    initial_path = os.path.expanduser("~/Desktop")

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='app_process.log',
                    filemode='w')

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistema Portátil de Anonimização")
        self.geometry("820x640")
        self.resizable(True, True)
        self.cancel_event = threading.Event()
        self.pdf_paths = []
        self.pasta_saida = initial_path
        self.progress_window = None
        self.current_file_index = 0  # Adicionado para rastrear o índice do arquivo atual
        self.total_files = 0  # Adicionado para rastrear o total de arquivos
        self.start_time = None  # Inicializa o tempo de início aqui

        # --- A interface gráfica continua exatamente a mesma ---
        self.sidebar = ctk.CTkFrame(self, width=150)
        self.sidebar.pack(side="left", fill="y")
        self.checkbox_ocr = ctk.CTkCheckBox(self.sidebar, text="OCR Padrão (Grayscale)")
        self.checkbox_mono = ctk.CTkCheckBox(self.sidebar, text="OCR Mono (Alta Compressão)")
        self.checkbox_auto = ctk.CTkCheckBox(self.sidebar, text="Auto (CPF)")
        self.checkbox_manual = ctk.CTkCheckBox(self.sidebar, text="Manual (Termos)")
        self.checkbox_comp = ctk.CTkCheckBox(self.sidebar, text="Comprimir")
        self.checkbox_ocr.pack(pady=10, anchor="w", padx=15)
        self.checkbox_mono.pack(pady=10, anchor="w", padx=15)
        self.checkbox_auto.pack(pady=10, anchor="w", padx=15)
        self.checkbox_manual.pack(pady=10, anchor="w", padx=15)
        self.checkbox_comp.pack(pady=10, anchor="w", padx=15)
        self.btn_cancelar = ctk.CTkButton(self.sidebar, text="Cancelar Processo", command=self._confirmar_cancelamento)
        self.btn_cancelar.pack(pady=30, padx=10)
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
        if self.progress_window is None or not self.progress_window.winfo_exists():
            self.progress_window = ctk.CTkToplevel(self)
            self.progress_window.title("Progresso")
            self.progress_window.geometry("500x200")
            self.progress_window.transient(self) # Faz a janela de progresso ficar sempre sobre a principal
            self.progress_window.grab_set() # Bloqueia interação com a janela principal (opcional, dependendo da UX)
            self.progress_window.protocol("WM_DELETE_WINDOW", lambda: None) # Impede fechar pelo 'X'
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
        if self.progress_window and self.progress_window.winfo_exists():
            self.pw_status_label.configure(text=status_msg)
            self.pw_progress_bar.set(progress_val)
            percentage = int(progress_val * 100)
            self.pw_percentage_label.configure(text=f"{percentage}%")
            
            if progress_val > 0.001: 
                total_time_estimated = elapsed_time / progress_val
                remaining_time = total_time_estimated - elapsed_time
                self.pw_time_label.configure(text=f"Tempo decorrido: {int(elapsed_time)}s | Tempo restante: {int(remaining_time)}s")
            else:
                self.pw_time_label.configure(text=f"Tempo decorrido: {int(elapsed_time)}s | Tempo restante: Calculando...")
            
            self.progress_window.update_idletasks() 

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
            if messagebox.askyesno("Cancelar?", "Tem certeza?"): self.cancel_event.set()
        else:
            messagebox.showinfo("Info", "O processo não está em execução.")

    def _executar(self):
        if not self.pdf_paths:
            messagebox.showerror("Erro", "Nenhum PDF selecionado.")
            return
        
        self.cancel_event.clear()
        self.btn_executar.configure(state="disabled")
        self._create_progress_window()
        self.start_time = time.time() # Inicia o timer aqui
        threading.Thread(target=self.executar_pipeline, daemon=True).start()
    
    def _binarize_pdf(self, input_path: str, temp_output_path: str, dpi: int = 300):
        logging.info(f"Iniciando binarização para: {os.path.basename(input_path)}")
        source_doc = fitz.open(input_path)
        output_doc = fitz.open()
        num_pages = len(source_doc)
        
        # A binarização pode ser ~30% do processo de um arquivo com OCR Mono
        progress_weight_for_binarization = 0.3 

        for i, page in enumerate(source_doc):
            if self.cancel_event.is_set():
                break 
            
            # Calcula o progresso dentro da binarização para o arquivo atual
            progress_in_current_stage = ((i + 1) / num_pages) * progress_weight_for_binarization
            
            # Soma ao progresso total do pipeline
            overall_progress = (self.current_file_index / self.total_files) + \
                               (progress_in_current_stage / self.total_files)
            
            # Captura as variáveis 'msg', 'prog', 'elapsed' explicitamente no lambda
            msg = f"Arquivo {self.current_file_index+1}/{self.total_files}: Binarizando {os.path.basename(input_path)} (Pág. {i+1}/{num_pages})"
            prog = overall_progress
            elapsed = time.time() - self.start_time
            self.after(0, lambda m=msg, p=prog, e_time=elapsed: self._update_progress(m, p, e_time))

            pix = page.get_pixmap(dpi=dpi)
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert('1', dither=Image.Dither.FLOYDSTEINBERG)
            img_buffer = io.BytesIO()
            img.save(img_buffer, format="PNG")
            new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(page.rect, stream=img_buffer.getvalue())
        
        output_doc.save(temp_output_path)
        output_doc.close()
        source_doc.close()
        logging.info(f"Binarização concluída: {os.path.basename(temp_output_path)}")


    def _run_ocr(self, input_file: str, output_file: str):
        logging.info(f"Iniciando OCR em: {os.path.basename(input_file)}")
        
        env = os.environ.copy()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # --- Lógica de resolução do caminho do Ghostscript ---
        ghostscript_exec_path = None
        try:
            cfg = load_config() 
            configured_gs_path = cfg.get("paths", {}).get("ghostscript_path")
            if configured_gs_path and os.path.isfile(configured_gs_path):
                ghostscript_exec_path = configured_gs_path
            else:
                portable_gs_path = os.path.join(script_dir, "ghostscript", "bin", "gswin64c.exe")
                if os.path.isfile(portable_gs_path):
                    ghostscript_exec_path = portable_gs_path
                else:
                    self.after(0, lambda: messagebox.showwarning("Aviso", "Ghostscript não encontrado no caminho configurado nem no caminho portátil padrão. OCR pode falhar. Verifique 'config.json' ou a pasta 'ghostscript/bin'."))
                    logging.warning(f"Ghostscript not found at configured path {configured_gs_path} or default portable path {portable_gs_path}. Relying on system PATH.")
                    # Última tentativa: confia no PATH do sistema, mas avisa o usuário.
                    ghostscript_exec_path = "gswin64c.exe" 
        except Exception as caught_e_gs: # Captura a exceção com um nome diferente
            logging.error(f"Erro ao carregar caminho do Ghostscript do config: {caught_e_gs}")
            portable_gs_path = os.path.join(script_dir, "ghostscript", "bin", "gswin64c.exe")
            if os.path.isfile(portable_gs_path):
                ghostscript_exec_path = portable_gs_path
            else:
                self.after(0, lambda msg_box_text=f"Erro ao verificar Ghostscript: {caught_e_gs}. OCR pode falhar. Tente configurar manualmente.": messagebox.showwarning("Aviso", msg_box_text))
                logging.warning(f"Ghostscript not found after config error. Relying on system PATH. Error: {caught_e_gs}")
                ghostscript_exec_path = "gswin64c.exe"
        
        # Adiciona o diretório do Ghostscript ao PATH se o caminho resolved for um diretório válido
        if os.path.dirname(ghostscript_exec_path) and os.path.isdir(os.path.dirname(ghostscript_exec_path)):
            env["PATH"] = os.path.dirname(ghostscript_exec_path) + os.pathsep + env["PATH"]
        logging.info(f"Usando Ghostscript de: {ghostscript_exec_path}")

        # --- Resolve o caminho para o ocrmypdf.exe dentro do venv ---
        # O diretório do script atual (gui_anonymizer.py) é 'scripts'
        # O venv está um nível acima de 'scripts'
        venv_root_dir = os.path.dirname(script_dir) 
        venv_scripts_dir = os.path.join(venv_root_dir, "venv", "Scripts")
        ocrmypdf_executable = os.path.join(venv_scripts_dir, "ocrmypdf.exe")
        
        # Se ocrmypdf.exe não for encontrado no venv, então confia no PATH.
        if not os.path.isfile(ocrmypdf_executable):
            logging.warning(f"ocrmypdf.exe não encontrado nos scripts do venv: {ocrmypdf_executable}. Tentando usar do PATH do sistema.")
            ocrmypdf_executable = "ocrmypdf" # O nome do comando, que será resolvido via PATH
        else:
            logging.info(f"Usando ocrmypdf do venv: {ocrmypdf_executable}")
            # Garante que o diretório do ocrmypdf do venv esteja no PATH para subprocessos
            env["PATH"] = venv_scripts_dir + os.pathsep + env["PATH"]

        command = [
            ocrmypdf_executable, # Usa o caminho resolvido para o executável
            "-l", "por", "--output-type", "pdfa",
            "-O", "1", "--force-ocr", input_file, output_file,
        ]
        
        # --- Lógica de resolução do caminho do Tesseract ---
        try:
            cfg = load_config()
            configured_tesseract_path = cfg.get("paths", {}).get("tesseract_path")
            if configured_tesseract_path and os.path.isfile(configured_tesseract_path):
                command.extend(["--tesseract-executable", configured_tesseract_path])
            else:
                portable_tesseract_path = os.path.join(script_dir, "tesseract", "tesseract.exe")
                if os.path.isfile(portable_tesseract_path):
                    command.extend(["--tesseract-executable", portable_tesseract_path])
                else:
                    self.after(0, lambda: messagebox.showwarning("Aviso", "Tesseract não encontrado no caminho configurado nem no caminho portátil padrão. OCR pode falhar. Verifique 'config.json' ou a pasta 'tesseract'."))
                    logging.warning(f"Tesseract not found at configured path {configured_tesseract_path} or default portable path {portable_tesseract_path}. Relying on system PATH for Tesseract.")

        except Exception as caught_e_tess: # Captura a exceção com um nome diferente
            logging.error(f"Erro ao carregar caminho do Tesseract do config: {caught_e_tess}")
            self.after(0, lambda msg_box_text=f"Erro ao verificar Tesseract: {caught_e_tess}. OCR pode falhar. Tente configurar manualmente.": messagebox.showwarning("Aviso", msg_box_text))
            logging.warning(f"Tesseract not found after config error. Relying on system PATH for Tesseract. Error: {caught_e_tess}")

        logging.info(f"Executando comando OCR: {' '.join(command)}")
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW 
        subprocess.run(command, check=True, startupinfo=si, env=env)
        logging.info(f"OCR concluído: {os.path.basename(output_file)}")

    def run_full_ocr_pipeline(self, input_path: str, final_output_path: str, mode: str):
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        
        # Peso total para a etapa de OCR (incluindo binarização se for mono) dentro de um único arquivo
        # Exemplo: OCR (binarização+OCR) representa 60% do processamento de um arquivo.
        # Ajuste este peso se o OCR for mais ou menos demorado em relação às outras etapas.
        ocr_total_weight_for_file = 0.6 
        
        if mode == 'mono':
            # Usa pasta de saída para arquivos temporários também para garantir permissões/espaço
            temp_binarized_path = os.path.join(self.pasta_saida, f"{base_name}_temp_binarized.pdf")
            try:
                # _binarize_pdf já atualiza o progresso internamente
                self._binarize_pdf(input_path, temp_binarized_path)
                if self.cancel_event.is_set(): return # Verifica cancelamento após binarização
                
                # Atualiza o progresso para o início do OCR real
                # Progresso já inclui o peso da binarização (0.3).
                # O restante do peso do OCR (0.6 - 0.3 = 0.3) é para a etapa de ocrmypdf
                current_overall_progress = (self.current_file_index / self.total_files) + \
                                           (0.3 / self.total_files) # Início da fase de OCR após binarização
                
                msg = f"Arquivo {self.current_file_index+1}/{self.total_files}: Aplicando OCR - {base_name}"
                prog = current_overall_progress
                elapsed = time.time() - self.start_time
                self.after(0, lambda m=msg, p=prog, e_time=elapsed: self._update_progress(m, p, e_time))
                
                self._run_ocr(temp_binarized_path, final_output_path)
            finally:
                if os.path.exists(temp_binarized_path):
                    os.remove(temp_binarized_path)
        elif mode == 'grayscale':
            # Para grayscale, não há binarização. O OCR leva todo o peso de 0.6.
            current_overall_progress = (self.current_file_index / self.total_files) # Começa do 0 para este arquivo
            
            msg = f"Arquivo {self.current_file_index+1}/{self.total_files}: Executando OCR em Tons de Cinza - {base_name}"
            prog = current_overall_progress
            elapsed = time.time() - self.start_time
            self.after(0, lambda m=msg, p=prog, e_time=elapsed: self._update_progress(m, p, e_time))
            
            self._run_ocr(input_path, final_output_path)
        else:
            raise ValueError(f"Modo OCR desconhecido: {mode}")

    def executar_pipeline(self):
        termos = [t.strip() for t in self.caixa_termos.get("0.0", ctk.END).splitlines() if t.strip()]
        self.total_files = len(self.pdf_paths) 
        
        for i, pdf_original in enumerate(self.pdf_paths):
            self.current_file_index = i 
            
            if self.cancel_event.is_set():
                # Calcula o progresso final mesmo com cancelamento para um feedback visual mais preciso
                # O progresso deve refletir o que foi concluído até o momento do cancelamento.
                final_progress_on_cancel = (i / self.total_files) 
                
                msg = "Processo cancelado pelo utilizador!"
                prog = final_progress_on_cancel
                elapsed = time.time() - self.start_time
                self.after(0, lambda m=msg, p=prog, e_time=elapsed: self._update_progress(m, p, e_time))
                break

            nome_base = os.path.splitext(os.path.basename(pdf_original))[0]
            caminho_atual = pdf_original
            arquivos_temporarios = []
            
            try:
                # Pesos para cada etapa do pipeline dentro de um único arquivo (soma 1.0)
                # Esses pesos podem precisar ser ajustados com base no tempo real de cada operação
                WEIGHT_OCR = 0.6  # OCR pode ser a etapa mais demorada
                WEIGHT_AUTO_ANONYMIZE = 0.15
                WEIGHT_MANUAL_ANONYMIZE = 0.15
                WEIGHT_COMPRESS = 0.1

                current_file_base_progress = self.current_file_index / self.total_files
                
                # Para calcular o progresso no final de cada etapa, somamos os pesos das etapas já concluídas.
                completed_weights_sum = 0.0

                # --- 1. Etapa de OCR ---
                if self.checkbox_mono.get() or self.checkbox_ocr.get():
                    modo_ocr = 'mono' if self.checkbox_mono.get() else 'grayscale'
                    saida_ocr = os.path.join(self.pasta_saida, f"{nome_base}_temp_ocr.pdf")
                    arquivos_temporarios.append(saida_ocr)
                    self.run_full_ocr_pipeline(caminho_atual, saida_ocr, modo_ocr, progress_callback, cancel_event, file_info, show_warning_callback, show_error_callback)
                    caminho_atual = saida_ocr
                    if self.cancel_event.is_set(): break
                    
                    completed_weights_sum += WEIGHT_OCR
                    current_overall_progress = current_file_base_progress + (completed_weights_sum / self.total_files)
                    
                    msg = f"Arquivo {i+1}/{self.total_files}: OCR Concluído."
                    prog = current_overall_progress
                    elapsed = time.time() - self.start_time
                    self.after(0, lambda m=msg, p=prog, e_time=elapsed: self._update_progress(m, p, e_time))

                # --- 2. Etapa de Anonimização Automática (CPF) ---
                if self.checkbox_auto.get():
                    saida_auto = os.path.join(self.pasta_saida, f"{nome_base}_temp_auto.pdf")
                    arquivos_temporarios.append(saida_auto)
                    
                    # Calcula o progresso de início para esta etapa
                    start_progress_current_stage = current_file_base_progress + \
                                                   (completed_weights_sum / self.total_files)
                    
                    msg = f"Arquivo {i+1}/{self.total_files}: Anonimizando CPFs..."
                    prog = start_progress_current_stage
                    elapsed = time.time() - self.start_time
                    self.after(0, lambda m=msg, p=prog, e_time=elapsed: self._update_progress(m, p, e_time))
                    
                    # CORREÇÃO AQUI: Chamar anonymize_pdf apenas com 2 argumentos
                    anonymize_pdf(caminho_atual, saida_auto) 
                    caminho_atual = saida_auto
                    if self.cancel_event.is_set(): break
                    
                    completed_weights_sum += WEIGHT_AUTO_ANONYMIZE
                    current_overall_progress = current_file_base_progress + (completed_weights_sum / self.total_files)
                    
                    msg = f"Arquivo {i+1}/{self.total_files}: CPFs Anonimizados."
                    prog = current_overall_progress
                    elapsed = time.time() - self.start_time
                    self.after(0, lambda m=msg, p=prog, e_time=elapsed: self._update_progress(m, p, e_time))


                # --- 3. Etapa de Anonimização Manual (Termos) ---
                if self.checkbox_manual.get() and termos:
                    saida_manual = os.path.join(self.pasta_saida, f"{nome_base}_temp_manual.pdf")
                    arquivos_temporarios.append(saida_manual)
                    
                    # Calcula o progresso de início para esta etapa
                    start_progress_current_stage = current_file_base_progress + \
                                                   (completed_weights_sum / self.total_files)
                    
                    msg = f"Arquivo {i+1}/{self.total_files}: Anonimizando termos manuais..."
                    prog = start_progress_current_stage
                    elapsed = time.time() - self.start_time
                    self.after(0, lambda m=msg, p=prog, e_time=elapsed: self._update_progress(m, p, e_time))
                    
                    anonymize_manual(caminho_atual, saida_manual, termos)
                    caminho_atual = saida_atual
                    if self.cancel_event.is_set(): break

                    completed_weights_sum += WEIGHT_MANUAL_ANONYMIZE
                    current_overall_progress = current_file_base_progress + (completed_weights_sum / self.total_files)
                    
                    msg = f"Arquivo {i+1}/{self.total_files}: Termos Manuais Anonimizados."
                    prog = current_overall_progress
                    elapsed = time.time() - self.start_time
                    self.after(0, lambda m=msg, p=prog, e_time=elapsed: self._update_progress(m, p, e_time))
                
                # --- 4. Etapa de Compressão ---
                if self.checkbox_comp.get():
                    saida_comp = os.path.join(self.pasta_saida, f"{nome_base}_temp_comp.pdf")
                    arquivos_temporarios.append(saida_comp)
                    
                    # Calcula o progresso de início para esta etapa
                    start_progress_current_stage = current_file_base_progress + \
                                                   (completed_weights_sum / self.total_files)
                    
                    msg = f"Arquivo {i+1}/{self.total_files}: Finalizando e comprimindo..."
                    prog = start_progress_current_stage
                    elapsed = time.time() - self.start_time
                    self.after(0, lambda m=msg, p=prog, e_time=elapsed: self._update_progress(m, p, e_time))
                    
                    # Tenta obter o caminho do Ghostscript para compressão
                    ghostscript_path = None
                    try:
                        cfg = load_config()
                        configured_gs_path = cfg.get("paths", {}).get("ghostscript_path")
                        if configured_gs_path and os.path.isfile(configured_gs_path):
                            ghostscript_path = configured_gs_path
                        else:
                            script_dir = os.path.dirname(os.path.abspath(__file__))
                            portable_gs_path = os.path.join(script_dir, "ghostscript", "bin", "gswin64c.exe")
                            if os.path.isfile(portable_gs_path):
                                ghostscript_path = portable_gs_path
                    except Exception as caught_e_gs_comp: # Captura a exceção aqui
                        logging.error(f"Erro ao obter caminho do Ghostscript para compressão: {caught_e_gs_comp}")
                        
                    if ghostscript_path and os.path.isfile(ghostscript_path):
                        compress_pdf(caminho_atual, saida_comp, gs_path=ghostscript_path)
                    else:
                        self.after(0, lambda: messagebox.showwarning("Aviso", "Compressão não executada: Ghostscript não encontrado ou caminho inválido. Verifique o config.json ou a pasta 'ghostscript/bin'."))
                        logging.error("Compression skipped: Ghostscript not found or invalid path.")

                    caminho_atual = saida_comp
                    if self.cancel_event.is_set(): break

                # Mover o arquivo final para o destino
                nome_final = os.path.join(self.pasta_saida, f"{nome_base}_PROCESSADO.pdf")
                # Se nenhuma operação foi marcada, o arquivo temporário 'caminho_atual'
                # ainda é o 'pdf_original', então precisamos copiar, não mover.
                # Se alguma operação foi feita, 'caminho_atual' é um temp_file, e precisa ser movido.
                if not (self.checkbox_ocr.get() or self.checkbox_mono.get() or \
                        self.checkbox_auto.get() or (self.checkbox_manual.get() and termos) or \
                        self.checkbox_comp.get()):
                    shutil.copy(pdf_original, nome_final) 
                else:
                    shutil.move(caminho_atual, nome_final)
                
            except Exception as caught_e: # Captura a exceção com um nome diferente
                logging.error(f"Falha ao processar {nome_base}: {caught_e}")
                error_msg_box_text = f"Falha ao processar {nome_base}:\n{caught_e}"
                self.after(0, lambda msg=error_msg_box_text: messagebox.showerror("Erro", msg))
            finally:
                # Limpa arquivos temporários
                for temp_file in arquivos_temporarios:
                    if os.path.exists(temp_file) and temp_file != caminho_atual: # Evita remover o arquivo final se ele for temporário
                        try: os.remove(temp_file)
                        except OSError as e_remove: print(f"Erro ao remover temp: {e_remove}")
            
            # Atualiza o progresso para o próximo arquivo (ou final, se for o último)
            msg = f"Ficheiro {i+1}/{self.total_files} concluído."
            prog = (i + 1) / self.total_files
            elapsed = time.time() - self.start_time
            self.after(0, lambda m=msg, p=prog, e_time=elapsed: self._update_progress(m, p, e_time))
            
        if not self.cancel_event.is_set():
            msg = "Todos os ficheiros foram processados!"
            prog = 1
            elapsed = time.time() - self.start_time
            self.after(0, lambda m=msg, p=prog, e_time=elapsed: self._update_progress(m, p, e_time))
            self.after(2000, lambda: self._close_progress_window()) 
        else:
            self.after(0, lambda: self._close_progress_window()) 
        
        self.after(0, lambda: self.btn_executar.configure(state="normal")) 
        self.after(0, lambda: self.btn_cancelar.configure(state="normal")) # Reabilita o botão Cancelar também


    def _close_progress_window(self):
        if self.progress_window and self.progress_window.winfo_exists():
            self.progress_window.grab_release() # Libera o grab_set
            self.progress_window.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
