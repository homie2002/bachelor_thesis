import os
import time
import json
import hashlib
import threading
from datetime import datetime
from tkinter import *
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import ttkbootstrap as tb
from ttkbootstrap.constants import *

# Підключення теми та налаштування стилю
def set_custom_style(root):
    style = tb.Style()
    style.theme_use("flatly")
    style.configure("TLabel", font=("Segoe UI", 10))
    style.configure("TButton", font=("Segoe UI", 10), padding=6)
    style.configure("TNotebook", tabposition='n')
    style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"))
    style.configure("TFrame", background="white")
    style.configure("TLabelframe", background="#f9f9f9")
    style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))

class SSDTester:
    def __init__(self, root):
        self.root = root
        self.root.title("Тест витривалості SSD")
        self.root.geometry("900x600")
        set_custom_style(self.root)

        self.test_folder = StringVar()
        self.log_folder = StringVar()
        self.gb_to_write = IntVar(value=1)
        self.cycles = IntVar(value=1)
        self.stop_test = False

        self.progress = None
        self.report_data = []

        self.build_gui()

    def build_gui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill="both", padx=10, pady=10)

        main_frame = ttk.Frame(notebook)
        notebook.add(main_frame, text="Головна")

        header = Label(main_frame, text="Тест витривалості SSD", font=("Segoe UI", 16, "bold"))
        header.pack(pady=10)

        settings = ttk.Labelframe(main_frame, text="Налаштування тесту")
        settings.pack(fill="x", padx=10, pady=10)

        self.add_browse_row(settings, "Папка для запису на SSD:", self.select_test_folder, self.test_folder, 0)
        self.add_browse_row(settings, "Папка для логів і графіків:", self.select_log_folder, self.log_folder, 1)

        ttk.Label(settings, text="Розмір запису (ГБ):").grid(row=2, column=0, sticky=W, padx=5, pady=5)
        Spinbox(settings, from_=1, to=1000, textvariable=self.gb_to_write, width=10).grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(settings, text="Кількість циклів:").grid(row=3, column=0, sticky=W, padx=5, pady=5)
        Spinbox(settings, from_=1, to=1000, textvariable=self.cycles, width=10).grid(row=3, column=1, padx=5, pady=5)

        self.progress = ttk.Progressbar(main_frame, orient=HORIZONTAL, length=700, mode='determinate')
        self.progress.pack(pady=20)

        button_frame = ttk.Labelframe(main_frame, text="Керування")
        button_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(button_frame, text="Почати тест", command=self.start_test_thread).grid(row=0, column=0, padx=10, pady=5)
        ttk.Button(button_frame, text="Експорт у CSV", command=self.export_csv_report).grid(row=0, column=2, padx=10, pady=5)
        ttk.Button(button_frame, text="Тест всього SSD", command=self.start_full_test_thread).grid(row=1, column=0, padx=10, pady=5)
        ttk.Button(button_frame, text="Зупинити тест", command=self.stop_test_run).grid(row=1, column=1, padx=10, pady=5)

    def add_browse_row(self, parent, label_text, command, variable, row):
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=W, padx=5, pady=5)
        ttk.Button(parent, text="Вибрати", command=command).grid(row=row, column=1, padx=5)
        ttk.Label(parent, textvariable=variable, width=60).grid(row=row, column=2, sticky=W, padx=5)

    def select_test_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.test_folder.set(folder)

    def select_log_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.log_folder.set(folder)

    def start_test_thread(self):
        self.stop_test = False
        threading.Thread(target=self.run_test).start()

    def start_full_test_thread(self):
        self.stop_test = False
        threading.Thread(target=self.run_full_capacity_test).start()

    def stop_test_run(self):
        self.stop_test = True

    def compute_checksum(self, path):
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def run_test(self):
        folder = self.test_folder.get()
        log_folder = self.log_folder.get()
        gb = self.gb_to_write.get()
        cycles = self.cycles.get()

        if not folder or not log_folder:
            messagebox.showerror("Помилка", "Будь ласка, оберіть папку для тесту та логів")
            return

        total_start_time = time.time()
        log_file_path = os.path.join(log_folder, f"ssd_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

        for cycle in range(1, cycles + 1):
            if self.stop_test:
                break

            start_time = time.time()
            self.progress["value"] = 0
            self.progress["maximum"] = gb

            file_checksums = {}
            for i in range(gb):
                if self.stop_test:
                    break
                file_path = os.path.join(folder, f"testfile_{i}.bin")
                data = os.urandom(1024 * 1024 * 1024)
                with open(file_path, "wb") as f:
                    f.write(data)
                file_checksums[file_path] = hashlib.sha256(data).hexdigest()
                self.progress["value"] += 1
                self.root.update_idletasks()

            for path, original_hash in file_checksums.items():
                if self.stop_test:
                    break
                read_hash = self.compute_checksum(path)
                if read_hash != original_hash:
                    with open(log_file_path, "a", encoding="utf-8") as f:
                        f.write(f"Розбіжність контрольної суми у {path}\nОчікувалось: {original_hash}\nОтримано: {read_hash}\n")
                    user_choice = messagebox.askyesno("Помилка контрольної суми", f"Розбіжність у {path}.\nПродовжити?")
                    if not user_choice:
                        return

            for path in file_checksums:
                if os.path.exists(path):
                    os.remove(path)

            end_time = time.time()
            cycle_duration = end_time - start_time
            total_duration = end_time - total_start_time

            log_entry = {
                "cycle": cycle,
                "write_speed_GB_s": round((gb / cycle_duration), 2),
                "cycle_duration_sec": round(cycle_duration, 2),
                "total_runtime_sec": round(total_duration, 2)
            }
            self.report_data.append(log_entry)

            with open(log_file_path, "a", encoding="utf-8") as f:
                f.write(f"Цикл #{cycle}\n")
                f.write(f"Швидкість запису: {log_entry['write_speed_GB_s']} ГБ/с\n")
                f.write(f"Тривалість циклу: {log_entry['cycle_duration_sec']} сек\n")
                f.write(f"Загальний час роботи: {log_entry['total_runtime_sec']} сек\n")
                f.write("="*40 + "\n")

            self.plot_graph(log_folder)

        messagebox.showinfo("Готово", f"Тест завершено. Лог збережено у: {log_file_path}")

    def run_full_capacity_test(self):
        folder = self.test_folder.get()
        log_folder = self.log_folder.get()

        if not folder or not log_folder:
            messagebox.showerror("Помилка", "Будь ласка, оберіть папку для тесту та логів")
            return

        log_file_path = os.path.join(log_folder, f"ssd_full_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        cycle = 0
        gb_written = 0

        while not self.stop_test:
            cycle += 1
            file_checksums = {}
            i = 0
            try:
                while True:
                    if self.stop_test:
                        return
                    file_path = os.path.join(folder, f"fullfile_{i}.bin")
                    data = os.urandom(1024 * 1024 * 1024)
                    with open(file_path, "wb") as f:
                        f.write(data)
                    file_checksums[file_path] = hashlib.sha256(data).hexdigest()
                    self.progress["value"] = i
                    self.root.update_idletasks()
                    i += 1
            except Exception as e:
                print(f"Диск заповнено: {e}")

            gb_written += i
            self.progress["maximum"] = i

            for path, original_hash in file_checksums.items():
                read_hash = self.compute_checksum(path)
                if read_hash != original_hash:
                    with open(log_file_path, "a", encoding="utf-8") as f:
                        f.write(f"Розбіжність контрольної суми у {path} після {cycle} циклів, {gb_written} ГБ записано\n")
                        f.write(f"Очікувалось: {original_hash}\nОтримано: {read_hash}\n")
                    user_choice = messagebox.askyesno("Помилка контрольної суми", f"Розбіжність у {path}.\nПродовжити?")
                    if not user_choice:
                        return

            for path in file_checksums:
                if os.path.exists(path):
                    os.remove(path)

            with open(log_file_path, "a", encoding="utf-8") as f:
                f.write(f"Цикл {cycle} успішно завершено. {i} ГБ записано.\n")

    def export_csv_report(self):
        if not self.report_data:
            messagebox.showwarning("Попередження", "Немає даних для експорту")
            return

        export_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV файли", "*.csv")])
        if export_path:
            with open(export_path, "w", encoding="utf-8") as f:
                f.write("Цикл,Швидкість запису (ГБ/с),Тривалість циклу (сек),Загальний час (сек)\n")
                for entry in self.report_data:
                    f.write(f"{entry['cycle']},{entry['write_speed_GB_s']},{entry['cycle_duration_sec']},{entry['total_runtime_sec']}\n")
            messagebox.showinfo("Успішно", f"CSV експортовано у: {export_path}")

    def plot_graph(self, folder):
        if not self.report_data:
            return

        cycles = [entry['cycle'] for entry in self.report_data]
        speeds = [entry['write_speed_GB_s'] for entry in self.report_data]

        plt.figure()
        plt.plot(cycles, speeds, marker='o')
        plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True))
        plt.xlabel("Цикл")
        plt.ylabel("Швидкість запису (ГБ/с)")
        plt.title("TBW - Швидкість запису за цикл")
        plt.grid(True)
        graph_path = os.path.join(folder, "tbw_plot.png")
        plt.savefig(graph_path)
        plt.close()

if __name__ == "__main__":
    root = tb.Window(themename="flatly")
    app = SSDTester(root)
    root.mainloop()
