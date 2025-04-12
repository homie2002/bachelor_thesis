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

# Подключение темы Azure
def set_azure_theme(root):
    root.tk.call("source", "azure.tcl")
    root.tk.call("set_theme", "light")

class SSDTester:
    def __init__(self, root):
        self.root = root
        self.root.title("SSD Endurance Tester")
        self.root.geometry("900x600")
        set_azure_theme(self.root)

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
        notebook.add(main_frame, text="Main")

        # Settings frame
        settings = ttk.LabelFrame(main_frame, text="Test Settings")
        settings.pack(fill="x", padx=10, pady=10)

        self.add_browse_row(settings, "Folder to write to SSD:", self.select_test_folder, self.test_folder, 0)
        self.add_browse_row(settings, "Folder for logs and graphs:", self.select_log_folder, self.log_folder, 1)

        ttk.Label(settings, text="Write size (GB):").grid(row=2, column=0, sticky=W, padx=5, pady=5)
        Spinbox(settings, from_=1, to=1000, textvariable=self.gb_to_write, width=10).grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(settings, text="Number of cycles:").grid(row=3, column=0, sticky=W, padx=5, pady=5)
        Spinbox(settings, from_=1, to=1000, textvariable=self.cycles, width=10).grid(row=3, column=1, padx=5, pady=5)

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, orient=HORIZONTAL, length=700, mode='determinate')
        self.progress.pack(pady=20)

        # Buttons
        button_frame = ttk.LabelFrame(main_frame, text="Controls")
        button_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(button_frame, text="Start Test", command=self.start_test_thread).grid(row=0, column=0, padx=10, pady=5)
        ttk.Button(button_frame, text="Export to JSON", command=self.export_json_report).grid(row=0, column=1, padx=10, pady=5)
        ttk.Button(button_frame, text="Export to CSV (Excel)", command=self.export_csv_report).grid(row=0, column=2, padx=10, pady=5)
        ttk.Button(button_frame, text="Test Full SSD", command=self.start_full_test_thread).grid(row=1, column=0, padx=10, pady=5)
        ttk.Button(button_frame, text="Stop Test", command=self.stop_test_run).grid(row=1, column=1, padx=10, pady=5)

    def add_browse_row(self, parent, label_text, command, variable, row):
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky=W, padx=5, pady=5)
        ttk.Button(parent, text="Browse", command=command).grid(row=row, column=1, padx=5)
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
            messagebox.showerror("Error", "Please select test and log folders")
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
                        f.write(f"Checksum MISMATCH in {path}\nExpected: {original_hash}\nGot: {read_hash}\n")
                    user_choice = messagebox.askyesno("Checksum Error", f"Mismatch in {path}.\nContinue?")
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
                f.write(f"Cycle #{cycle}\n")
                f.write(f"Write Speed: {log_entry['write_speed_GB_s']} GB/s\n")
                f.write(f"Cycle Duration: {log_entry['cycle_duration_sec']} sec\n")
                f.write(f"Total Runtime: {log_entry['total_runtime_sec']} sec\n")
                f.write("="*40 + "\n")

            self.plot_graph(log_folder)

        messagebox.showinfo("Done", f"Test completed. Log saved to: {log_file_path}")

    def run_full_capacity_test(self):
        folder = self.test_folder.get()
        log_folder = self.log_folder.get()

        if not folder or not log_folder:
            messagebox.showerror("Error", "Please select test and log folders")
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
                print(f"Disk full: {e}")

            gb_written += i
            self.progress["maximum"] = i

            for path, original_hash in file_checksums.items():
                read_hash = self.compute_checksum(path)
                if read_hash != original_hash:
                    with open(log_file_path, "a", encoding="utf-8") as f:
                        f.write(f"Checksum MISMATCH in {path} after {cycle} cycles, {gb_written} GB written\n")
                        f.write(f"Expected: {original_hash}\nGot: {read_hash}\n")
                    user_choice = messagebox.askyesno("Checksum Error", f"Mismatch in {path}.\nContinue?")
                    if not user_choice:
                        return

            for path in file_checksums:
                if os.path.exists(path):
                    os.remove(path)

            with open(log_file_path, "a", encoding="utf-8") as f:
                f.write(f"Cycle {cycle} completed successfully. {i} GB written.\n")

    def export_json_report(self):
        if not self.report_data:
            messagebox.showwarning("Warning", "No data to export")
            return

        export_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if export_path:
            with open(export_path, "w") as f:
                json.dump(self.report_data, f, indent=4)
            messagebox.showinfo("Success", f"Report saved to {export_path}")

    def export_csv_report(self):
        if not self.report_data:
            messagebox.showwarning("Warning", "No data to export")
            return

        export_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if export_path:
            with open(export_path, "w", encoding="utf-8") as f:
                f.write("Cycle,Write Speed (GB/s),Cycle Duration (sec),Total Runtime (sec)\n")
                for entry in self.report_data:
                    f.write(f"{entry['cycle']},{entry['write_speed_GB_s']},{entry['cycle_duration_sec']},{entry['total_runtime_sec']}\n")
            messagebox.showinfo("Success", f"CSV exported to: {export_path}")

    def plot_graph(self, folder):
        if not self.report_data:
            return

        cycles = [entry['cycle'] for entry in self.report_data]
        speeds = [entry['write_speed_GB_s'] for entry in self.report_data]

        plt.figure()
        plt.plot(cycles, speeds, marker='o')
        plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True))
        plt.xlabel("Cycle")
        plt.ylabel("Write Speed (GB/s)")
        plt.title("TBW - Write Speed per Cycle")
        plt.grid(True)
        graph_path = os.path.join(folder, "tbw_plot.png")
        plt.savefig(graph_path)
        plt.close()

if __name__ == "__main__":
    root = Tk()
    app = SSDTester(root)
    root.mainloop()
