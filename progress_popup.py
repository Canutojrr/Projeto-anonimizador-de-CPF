import time
import threading
import tkinter as tk
from tkinter import ttk

class ProgressBarPopup:
    def __init__(self, total_tasks):
        self.total_tasks = total_tasks
        self.completed_tasks = 0
        self.start_time = None

        self.window = tk.Tk()
        self.window.title("Progresso do Processamento")
        self.window.geometry("400x130")
        self.window.resizable(False, False)

        self.label = ttk.Label(self.window, text="Iniciando...")
        self.label.pack(pady=10)

        self.progress = ttk.Progressbar(self.window, length=350, mode='determinate')
        self.progress.pack(pady=5)

        self.time_label = ttk.Label(self.window, text="Tempo restante estimado: calculando...")
        self.time_label.pack(pady=5)

    def start(self):
        self.start_time = time.time()
        threading.Thread(target=self.window.mainloop, daemon=True).start()

    def update(self, completed_tasks):
        self.completed_tasks = completed_tasks
        percent = int((self.completed_tasks / self.total_tasks) * 100)
        self.progress['value'] = percent

        elapsed = time.time() - self.start_time
        if self.completed_tasks > 0:
            avg_time = elapsed / self.completed_tasks
            remaining_time = avg_time * (self.total_tasks - self.completed_tasks)
            mins, secs = divmod(int(remaining_time), 60)
            self.time_label.config(text=f"Tempo estimado restante: {mins}m {secs}s")
        else:
            self.time_label.config(text="Tempo estimado restante: calculando...")

        self.label.config(text=f"{self.completed_tasks} de {self.total_tasks} arquivos processados")
        self.window.update_idletasks()

    def close(self):
        self.window.destroy()
