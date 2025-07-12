import json
import os
from tkinter import Tk, Label, Entry, Button, filedialog, messagebox

CONFIG_FILE = 'config.json'

def load_config():
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_config(path_tesseract, path_ghostscript):
    config = {
        'tesseract_path': path_tesseract,
        'ghostscript_path': path_ghostscript
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    messagebox.showinfo("Configurações", "config.json salvo com sucesso.")

def select_tesseract():
    path = filedialog.askopenfilename(title="Selecione tesseract.exe",
                                      filetypes=[("Executável Tesseract", "tesseract.exe")])
    if path:
        entry_tesseract.delete(0, 'end')
        entry_tesseract.insert(0, path)

def select_ghostscript():
    path = filedialog.askopenfilename(title="Selecione o executável do Ghostscript",
                                      filetypes=[("Executável Ghostscript", "*.exe")])
    if path:
        entry_ghostscript.delete(0, 'end')
        entry_ghostscript.insert(0, path)

root = Tk()
root.title("Configurações do Anonimizador")
root.geometry("500x150")

Label(root, text="Caminho do Tesseract (tesseract.exe):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
entry_tesseract = Entry(root, width=50)
entry_tesseract.grid(row=0, column=1, padx=5, pady=5)
Button(root, text="Selecionar...", command=select_tesseract).grid(row=0, column=2, padx=5, pady=5)

Label(root, text="Caminho do Ghostscript (gswin*.exe):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
entry_ghostscript = Entry(root, width=50)
entry_ghostscript.grid(row=1, column=1, padx=5, pady=5)
Button(root, text="Selecionar...", command=select_ghostscript).grid(row=1, column=2, padx=5, pady=5)

cfg = load_config()
if 'tesseract_path' in cfg:
    entry_tesseract.insert(0, cfg['tesseract_path'])
if 'ghostscript_path' in cfg:
    entry_ghostscript.insert(0, cfg['ghostscript_path'])

Button(root, text="Salvar", command=lambda: save_config(entry_tesseract.get(), entry_ghostscript.get())).grid(row=2, column=1, pady=10)

root.mainloop()
