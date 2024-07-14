import configparser
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox

class FDSProcessorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fds SURF fix 0.1.0")
        
        tk.Label(self, text="MLRPUA:").grid(row=0, column=0, padx=10, pady=5)
        self.mlrpua_entry = tk.Entry(self)
        self.mlrpua_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(self, text="TAU_Q:").grid(row=1, column=0, padx=10, pady=5)
        self.tau_q_entry = tk.Entry(self)
        self.tau_q_entry.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(self, text="AREA_MULTIPLIER:").grid(row=2, column=0, padx=10, pady=5)
        self.area_multiplier_entry = tk.Entry(self)
        self.area_multiplier_entry.grid(row=2, column=1, padx=10, pady=5)

        self.process_button = tk.Button(self, text="Process", command=self.process_files)
        self.process_button.grid(row=3, columnspan=2, pady=10)

    def read_ini_file(self, ini_file):
        config = configparser.ConfigParser()
        with open(ini_file, 'r', encoding='utf-16') as f:
            config.read_file(f)
        return config['filePath']['filePath']

    def process_fds_file(self, fds_path, MLRPUA, TAU_Q, AREA_MULTIPLIER):
        modified_lines = []
        inside_ochag_block = False
        surf_seen = False
        vent_seen = False

        with open(fds_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            for line in lines:
                if 'Ochag pozhara 1 (begin)' in line:
                    inside_ochag_block = True
                    surf_seen = False
                    vent_seen = False
                    modified_lines.append(line)
                    continue

                if 'Ochag pozhara 1 (end)' in line:
                    inside_ochag_block = False
                    modified_lines.append(line)
                    continue

                if inside_ochag_block:
                    if line.startswith('&SURF') and not surf_seen:
                        modified_lines.append("&SURF ID='1',\n")
                        modified_lines.append(f"      FYI='Ochag pozhara 1',\n")
                        modified_lines.append("      COLOR='RED',\n")
                        modified_lines.append(f"      MLRPUA={MLRPUA},\n")
                        modified_lines.append(f"      TAU_Q={TAU_Q},\n")
                        modified_lines.append(f"      AREA_MULTIPLIER={AREA_MULTIPLIER}/\n")
                        surf_seen = True
                        continue
                    
                    if line.startswith('&VENT') and not vent_seen:
                        line = re.sub(r"CTRL_ID='[^']*'\s*", "", line)
                        modified_lines.append(line)
                        vent_seen = True
                        continue

                    if surf_seen and vent_seen:
                        continue
                else:
                    modified_lines.append(line)

        with open(fds_path.replace('.fds', '_surf_fixed.fds'), 'w', encoding='utf-8') as file:
            file.writelines(modified_lines)

    def process_files(self):
        ini_path = 'filePath.ini'
        try:
            fds_path = self.read_ini_file(ini_path)
            MLRPUA = self.mlrpua_entry.get()
            TAU_Q = self.tau_q_entry.get()
            AREA_MULTIPLIER = self.area_multiplier_entry.get()
            if not MLRPUA or not TAU_Q or not AREA_MULTIPLIER:
                raise ValueError("Поля не должны быть пустыми")
            self.process_fds_file(fds_path, MLRPUA, TAU_Q, AREA_MULTIPLIER)
            messagebox.showinfo("Готово!", f"Модифицированный .fds файл сохранён:\n\n{fds_path.replace('.fds', '_surf_fixed.fds')}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

if __name__ == "__main__":
    app = FDSProcessorApp()
    app.mainloop()
