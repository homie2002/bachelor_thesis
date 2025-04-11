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
from ttkbootstrap import Style

class SSDTester:
    def __init__(self, root):
        self.root = root
        self.root.title("Тест витривалості SSD")
        self.root.geometry("750x700")
        self.style = Style("darkly")

        self.font_family = ("Segoe UI", 10)

        self.test_folder = StringVar()
        self.log_folder = StringVar()
        self.gb_to_write = IntVar(value=1)
        self.cycles = IntVar(value=1)
        self.stop_test = False

        self.progress = None
        self.report_data = []

        self.build_gui()

    def build_gui(self):
        frame = ttk.Frame(self.root)
        frame.pack(pady=20, padx=20)

        ttk.Label(frame, text="Папка для запису на SSD:").grid(row=0, column=0, sticky=W, padx=5, pady=5)
        ttk.Button(frame, text="Обрати", command=self.select_test_folder).grid(row=0, column=1, padx=5)
        self.test_folder_label = ttk.Label(frame, text="")
        self.test_folder_label.grid(row=0, column=2, sticky=W, padx=5)

        ttk.Label(frame, text="Папка для логів та графіків:").grid(row=1, column=0, sticky=W, padx=5, pady=5)
        ttk.Button(frame, text="Обрати", command=self.select_log_folder).grid(row=1, column=1, padx=5)
        self.log_folder_label = ttk.Label(frame, text="")
        self.log_folder_label.grid(row=1, column=2, sticky=W, padx=5)

        ttk.Label(frame, text="Обсяг запису (ГБ):").grid(row=2, column=0, sticky=W, padx=5, pady=5)
        Spinbox(frame, from_=1, to=1000, textvariable=self.gb_to_write, width=10, font=self.font_family).grid(row=2, column=1, padx=5)

        ttk.Label(frame, text="Кількість циклів:").grid(row=3, column=0, sticky=W, padx=5, pady=5)
        Spinbox(frame, from_=1, to=1000, textvariable=self.cycles, width=10, font=self.font_family).grid(row=3, column=1, padx=5)

        self.progress = ttk.Progressbar(self.root, orient=HORIZONTAL, length=500, mode='determinate')
        self.progress.pack(pady=15)

        button_frame = Frame(self.root)
        button_frame.pack(pady=5)

        ttk.Button(button_frame, text="Почати тест", command=self.start_test_thread).grid(row=0, column=0, padx=10, pady=5)
        ttk.Button(button_frame, text="Експортувати у JSON", command=self.export_json_report).grid(row=0, column=1, padx=10, pady=5)
        ttk.Button(button_frame, text="Експорт у CSV (Excel)", command=self.export_csv_report).grid(row=0, column=2, padx=10, pady=5)
        ttk.Button(button_frame, text="Тест всього SSD", command=self.start_full_test_thread).grid(row=1, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Зупинити тест", command=self.stop_test_run).grid(row=1, column=2, pady=10)

    def select_test_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.test_folder.set(folder)
            self.test_folder_label.config(text=folder)

    def select_log_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.log_folder.set(folder)
            self.log_folder_label.config(text=folder)

    def start_test_thread(self):
        self.stop_test = False
        thread = threading.Thread(target=self.run_test)
        thread.start()

    def start_full_test_thread(self):
        self.stop_test = False
        thread = threading.Thread(target=self.run_full_capacity_test)
        thread.start()

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
            messagebox.showerror("Помилка", "Оберіть папку для тесту та логів")
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
                        f.write(f"❌ ПОМИЛКА: Контрольна сума не співпала у {path}\n")
                        f.write(f"Очікувана: {original_hash}\nОтримана: {read_hash}\n")
                    user_choice = messagebox.askyesno("Помилка", f"Контрольна сума не співпала у {path}.\nПродовжити тест?")
                    if not user_choice:
                        return

            for path in file_checksums:
                if os.path.exists(path):
                    os.remove(path)

            end_time = time.time()
            cycle_duration = end_time - start_time
            total_duration = end_time - total_start_time

            log_entry = {
                "цикл": cycle,
                "швидкість_запису_ГБ_с": round((gb / cycle_duration), 2),
                "тривалість_циклу_сек": round(cycle_duration, 2),
                "загальний_час_роботи_сек": round(total_duration, 2)
            }
            self.report_data.append(log_entry)

            with open(log_file_path, "a", encoding="utf-8") as f:
                f.write(f"Цикл #{cycle}\n")
                f.write(f"Швидкість запису: {log_entry['швидкість_запису_ГБ_с']} ГБ/с\n")
                f.write(f"Тривалість циклу: {log_entry['тривалість_циклу_сек']} сек.\n")
                f.write(f"Загальний час роботи: {log_entry['загальний_час_роботи_сек']} сек.\n")
                f.write("="*40 + "\n")

            self.plot_graph(log_folder)

        messagebox.showinfo("Готово", f"Тест завершено. Лог збережено: {log_file_path}")

    def run_full_capacity_test(self):
        folder = self.test_folder.get()
        log_folder = self.log_folder.get()

        if not folder or not log_folder:
            messagebox.showerror("Помилка", "Оберіть папку для тесту та логів")
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
                        f.write(f"❌ ПОМИЛКА: Контрольна сума не співпала у файлі {path} після {cycle} циклів, {gb_written} ГБ\n")
                        f.write(f"Очікувана: {original_hash}\nОтримана: {read_hash}\n")
                    user_choice = messagebox.askyesno("Помилка", f"Контрольна сума не співпала у {path}.\nПродовжити тест?")
                    if not user_choice:
                        return

            for path in file_checksums:
                if os.path.exists(path):
                    os.remove(path)

            with open(log_file_path, "a", encoding="utf-8") as f:
                f.write(f"✅ Цикл {cycle} завершено успішно. Записано {i} ГБ\n")

    def export_json_report(self):
        if not self.report_data:
            messagebox.showwarning("Увага", "Немає даних для експорту")
            return

        export_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON файли", "*.json")])
        if export_path:
            with open(export_path, "w") as f:
                json.dump(self.report_data, f, indent=4)
            messagebox.showinfo("Успіх", f"Звіт збережено у {export_path}")

    def export_csv_report(self):
        if not self.report_data:
            messagebox.showwarning("Увага", "Немає даних для експорту")
            return

        export_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV файли", "*.csv")])
        if export_path:
            with open(export_path, "w", encoding="utf-8") as f:
                f.write("Цикл,Швидкість запису (ГБ/с),Тривалість циклу (сек),Загальний час (сек)\n")
                for entry in self.report_data:
                    f.write(f"{entry['цикл']},{entry['швидкість_запису_ГБ_с']},{entry['тривалість_циклу_сек']},{entry['загальний_час_роботи_сек']}\n")
            messagebox.showinfo("Успіх", f"CSV експорт завершено: {export_path}")

    def plot_graph(self, folder):
        if not self.report_data:
            return

        cycles = [entry['цикл'] for entry in self.report_data]
        speeds = [entry['швидкість_запису_ГБ_с'] for entry in self.report_data]

        plt.figure()
        plt.plot(cycles, speeds, marker='o')
        plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True))
        plt.xlabel("Цикл")
        plt.ylabel("Швидкість запису (ГБ/с)")
        plt.title("TBW - Швидкість запису за циклами")
        plt.grid(True)
        graph_path = os.path.join(folder, "tbw_plot.png")
        plt.savefig(graph_path)
        plt.close()

if __name__ == "__main__":
    root = Tk()
    app = SSDTester(root)
    root.mainloop()
