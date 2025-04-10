import os
import time
import hashlib
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
import csv
from datetime import datetime

GB = 1024 * 1024 * 1024

class SSDTesterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SSD Endurance Tester")

        # Данные для логирования и графика
        self.total_written_gb = 0
        self.cycles = []
        self.speeds = []
        self.cycle_times = []
        self.total_time = 0  # Общее время работы программы
        self.log_file_path = os.path.join(os.path.expanduser("~"), "Desktop", "ssd_test_log.txt")
        self.csv_file_path = os.path.join(os.path.expanduser("~"), "Desktop", "ssd_test_report.csv")
        self.start_time = None  # Для общего времени работы программы

        tk.Label(root, text="Путь к SSD-папке:").grid(row=0, column=0, sticky='w')
        self.path_entry = tk.Entry(root, width=50)
        self.path_entry.grid(row=0, column=1)
        tk.Button(root, text="Обзор...", command=self.browse_folder).grid(row=0, column=2)

        self.use_all_space = tk.BooleanVar()
        self.use_all_space.set(True)
        tk.Checkbutton(root, text="Использовать весь доступный объём", variable=self.use_all_space, command=self.toggle_entry).grid(row=1, column=0, columnspan=2, sticky='w')

        tk.Label(root, text="Или указать объём (ГБ):").grid(row=2, column=0, sticky='w')
        self.size_entry = tk.Entry(root, width=10)
        self.size_entry.grid(row=2, column=1, sticky='w')
        self.size_entry.insert(0, "10")

        tk.Label(root, text="Количество циклов:").grid(row=3, column=0, sticky='w')
        self.cycles_entry = tk.Entry(root, width=10)
        self.cycles_entry.grid(row=3, column=1, sticky='w')
        self.cycles_entry.insert(0, "1")

        self.start_button = tk.Button(root, text="▶ Начать тест", command=self.start_test)
        self.start_button.grid(row=4, column=0, pady=10)

        self.stop_button = tk.Button(root, text="■ Остановить", command=self.stop_test, state=tk.DISABLED)
        self.stop_button.grid(row=4, column=1, pady=10)

        self.log_text = tk.Text(root, height=20, width=80)
        self.log_text.grid(row=5, column=0, columnspan=3)

        self.stop_flag = False
        self.cycle = 0

        # Инициализация лог-файла
        self.create_logfile()

    def toggle_entry(self):
        self.size_entry.config(state='disabled' if self.use_all_space.get() else 'normal')

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder)

    def start_test(self):
        self.stop_flag = False
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.start_time = time.time()  # Начало общего времени работы
        threading.Thread(target=self.run_test).start()

    def stop_test(self):
        self.stop_flag = True
        self.log("🛑 Остановка запрошена.")

    def run_test(self):
        path = self.path_entry.get()
        if not os.path.exists(path):
            self.log("❌ Указанный путь не существует.")
            return

        try:
            if self.use_all_space.get():
                total, used, free = shutil.disk_usage(path)
                size_to_write_gb = (free - 2 * GB) // GB
            else:
                size_to_write_gb = int(self.size_entry.get())

            if size_to_write_gb <= 0:
                self.log("❌ Объём должен быть больше 0.")
                return

            num_cycles = int(self.cycles_entry.get())
            if num_cycles <= 0:
                self.log("❌ Количество циклов должно быть больше 0.")
                return
        except Exception as e:
            self.log(f"Ошибка в настройках: {e}")
            return

        test_dir = os.path.join(path, "ssd_test_temp")
        os.makedirs(test_dir, exist_ok=True)

        # Создание или очистка CSV-отчёта
        self.init_csv_report()

        try:
            # Запуск циклов
            for cycle in range(1, num_cycles + 1):
                if self.stop_flag:
                    break

                self.cycle = cycle
                self.log(f"\n🔁 Цикл {self.cycle} — Запись {size_to_write_gb} ГБ")
                cycle_time = self.test_cycle(test_dir, size_to_write_gb)

                # Удаление файлов после каждого цикла
                self.log("🧹 Очистка файлов после цикла...")
                for filename in os.listdir(test_dir):
                    file_path = os.path.join(test_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)

                self.cycle_times.append(cycle_time)
                self.total_time += cycle_time  # Обновляем общее время работы программы
                self.log(f"✅ Цикл {self.cycle} завершён.")
                self.log(f"⏱ Время цикла {self.cycle}: {cycle_time:.2f} сек")
                self.log(f"⏳ Общее время работы: {self.total_time:.2f} сек")

            self.plot_tbw_graph()

        except Exception as e:
            self.log(f"❗ Тест остановлен из-за ошибки: {str(e)}")
        finally:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def test_cycle(self, test_dir, size_to_write_gb):
        file_paths = []
        start_time = time.time()

        for i in range(size_to_write_gb):
            if self.stop_flag:
                break

            filename = os.path.join(test_dir, f"file_{i}.bin")
            data = os.urandom(GB)
            with open(filename, "wb") as f:
                f.write(data)

            file_paths.append(filename)

        write_time = time.time() - start_time
        speed = size_to_write_gb / write_time
        self.total_written_gb += size_to_write_gb

        self.log(f"📈 Скорость записи: {speed:.2f} ГБ/с")
        self.log(f"🧮 Всего записано: {self.total_written_gb} ГБ")

        # Логирование данных в CSV
        self.log_to_csv(self.cycle, speed, self.total_written_gb)

        # Записываем данные для графика
        self.cycles.append(self.cycle)
        self.speeds.append(speed)

        # Возвращаем время выполнения цикла
        return write_time

    def log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        print(message)
        self.write_to_logfile(message)

    def write_to_logfile(self, message):
        # Запись в лог-файл
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")

    def create_logfile(self):
        # Если лог-файл не существует, создаём его с заголовком
        if not os.path.exists(self.log_file_path):
            with open(self.log_file_path, "w", encoding="utf-8") as f:
                f.write(f"Тестирование SSD начато: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 40 + "\n")

    def init_csv_report(self):
        # Инициализация CSV файла с заголовками
        if not os.path.exists(self.csv_file_path):
            with open(self.csv_file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Цикл", "Скорость записи (ГБ/с)", "Общий объём записанных данных (ГБ)", "Дата"])

    def log_to_csv(self, cycle, speed, total_written_gb):
        with open(self.csv_file_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([cycle, speed, total_written_gb, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

    def plot_tbw_graph(self):
        # Создание графика TBW
        if self.cycles and self.speeds:
            print("📊 График будет строиться...")
            try:
                plt.figure(figsize=(10, 6))
                plt.plot(self.cycles, self.speeds, marker="o")
                plt.xlabel("Циклы теста")
                plt.ylabel("Скорость записи (ГБ/с)")
                plt.title("График TBW (Total Bytes Written)")
                plt.grid(True)

                # Путь для сохранения графика
                graph_path = os.path.join(os.path.expanduser("~"), "Desktop", "tbw_graph.png")
                plt.savefig(graph_path)
                plt.close()  # Закрываем, чтобы не оставить открытое окно

                print(f"✅ График сохранён: {graph_path}")
            except Exception as e:
                print(f"❌ Ошибка при сохранении графика: {e}")
        else:
            print("❌ Нет данных для графика.")

# Запуск GUI
if __name__ == "__main__":
    root = tk.Tk()
    app = SSDTesterGUI(root)
    root.mainloop()
