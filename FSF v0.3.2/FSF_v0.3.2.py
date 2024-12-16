import configparser
import os
import re
import tkinter as tk
from tkinter import messagebox
from math import sqrt, pi

class Tooltip:
    """Создаёт всплывающие подсказки."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)  # Убираем косметику
        self.tooltip_window.geometry(f"+{x}+{y}")  # Размещаем тултип

        label = tk.Label(self.tooltip_window, text=self.text, background="lightyellow", borderwidth=1, relief="solid")
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class FDSProcessorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        current_directory = os.path.dirname(__file__)
        parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
        icon_path = os.path.join(parent_directory, '.gitpics', 'fsf.ico')
        
        self.title("FDS SURF FIX v0.3.2")
        self.iconbitmap(icon_path)
        self.wm_iconbitmap(icon_path)
        
        # Завезли тултипсы
        tk.Label(self, text="k:").grid(row=0, column=0, padx=10, pady=5)
        self.k_entry = tk.Entry(self)
        self.k_entry.grid(row=0, column=1, padx=10, pady=5)
        Tooltip(self.k_entry, "Коэффициент, учитывающий отличие фактической площади горючей нагрузки в помещении и площади помещения. Для помещений классов функциональной пожарной опасности Ф1 - Ф4 следует принимать равным 2")

        tk.Label(self, text="Fпом:").grid(row=1, column=0, padx=10, pady=5)
        self.fpom_entry = tk.Entry(self)
        self.fpom_entry.grid(row=1, column=1, padx=10, pady=5)
        Tooltip(self.fpom_entry, "Площадь помещения с очагом пожара, м2")

        self.v = None
        tk.Label(self, text="v:").grid(row=2, column=0, padx=10, pady=5)
        self.v_entry = tk.Entry(self)
        self.v_entry.grid(row=2, column=1, padx=10, pady=5)
        Tooltip(self.v_entry, "Линейная скорость растространения пламени, м/с")

        tk.Label(self, text="psi_уд:").grid(row=3, column=0, padx=10, pady=5)
        self.psyd_entry = tk.Entry(self)
        self.psyd_entry.grid(row=3, column=1, padx=10, pady=5)
        Tooltip(self.psyd_entry, "Удельная массовая скорость выгорания (для жидкостей установившаяся), кг/(с*м2)")

        #tk.Label(self, text="Sof:").grid(row=4, column=0, padx=10, pady=5)
        #self.sof_entry = tk.Entry(self)
        #self.sof_entry.grid(row=4, column=1, padx=10, pady=5)
        #Tooltip(self.sof_entry, "Фактическая площадь поверхности очага пожара на твёрдом теле, м2")

        # Поля рассчитываемых значений (нередактируемые)
        tk.Label(self, text="tmax:").grid(row=5, column=0, padx=10, pady=5)
        self.tmax_entry = tk.Entry(self, state='readonly')
        self.tmax_entry.grid(row=5, column=1, padx=10, pady=5)
        Tooltip(self.tmax_entry, "Время охвата пожаром всей поверхности горючей нагрузки в помещении, сек")

        tk.Label(self, text="Psi:").grid(row=6, column=0, padx=10, pady=5)
        self.psy_entry = tk.Entry(self, state='readonly')
        self.psy_entry.grid(row=6, column=1, padx=10, pady=5)
        Tooltip(self.psy_entry, "Зависимость скорости выгорания (кг/с) от времени")

        tk.Label(self, text="Stt:").grid(row=7, column=0, padx=10, pady=5)
        self.stt_entry = tk.Entry(self, state='readonly')
        self.stt_entry.grid(row=7, column=1, padx=10, pady=5)
        Tooltip(self.stt_entry, "Площадь поверхности горючей нагрузки в помещении, м2")

        #tk.Label(self, text="AREA_MULTIPLIER:").grid(row=8, column=0, padx=10, pady=5)
        #self.area_multiplier_entry = tk.Entry(self, state='readonly')
        #self.area_multiplier_entry.grid(row=8, column=1, padx=10, pady=5)
        #Tooltip(self.area_multiplier_entry, "Мультипликатор площади поверхности очага пожара. Переводит фактическую площадь поверхности очага пожара на твёрдом теле в требуемую согласно Приложению 1 Методики 1140")

        self.calculate_button = tk.Button(self, text="Рассчитать", command=self.calculate)
        self.calculate_button.grid(row=9, columnspan=2, pady=10)

        self.process_button = tk.Button(self, text="Сохранить", command=self.process_files)
        self.process_button.grid(row=10, columnspan=2, pady=10)
        
        self.load_from_ini()  # Загружаем данные из INI

    def load_from_ini(self):
        current_directory = os.path.dirname(__file__)
        parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
        inis_path = os.path.join(parent_directory, 'inis')
        
        ini_file = os.path.join(inis_path, 'IniApendix1.ini')
        
        if os.path.exists(ini_file):
            config = configparser.ConfigParser()
            config.read(ini_file)
            try:
                # Считываем редактируемые данные
                self.k_entry.insert(0, config['Calculations']['k'])
                self.fpom_entry.insert(0, config['Calculations']['Fpom'])
                self.v_entry.insert(0, config['Calculations']['v'])
                self.psyd_entry.insert(0, config['Calculations']['psi_ud'])
                #self.sof_entry.insert(0, config['Calculations']['Sof'])
                # Считываем нередактируемые данные
                self.tmax_entry.insert(0, config['Calculations']['tmax'])
                self.psy_entry.insert(0, config['Calculations']['Psi'])
                self.stt_entry.insert(0, config['Calculations']['Stt'])
                #self.area_multiplier_entry.insert(0, config['Calculations']['AREA_MULTIPLIER'])
            except KeyError as e:
                messagebox.showwarning("Предупреждение", f"Значения не найдены: {e}")

    def calculate(self):
        try:
            k = float(self.k_entry.get())
            Fpom = float(self.fpom_entry.get())
            v = float(self.v_entry.get())
            psi_ud = float(self.psyd_entry.get())
            #Sof = float(self.sof_entry.get())

            # Вычисляем tmax, Psi, Stt, AREA_MULTIPLIER
            tmax = sqrt((k * Fpom) / (pi * v**2))
            Psi = psi_ud * pi * v**2 * tmax**2
            Stt = pi * (v * tmax)**2
            #AREA_MULTIPLIER = Stt / Sof

            # Обновляем нередактируемые поля
            self.tmax_entry.config(state='normal')
            self.tmax_entry.delete(0, tk.END)
            self.tmax_entry.insert(0, f"{tmax:.4f}")
            self.tmax_entry.config(state='readonly')

            self.psy_entry.config(state='normal')
            self.psy_entry.delete(0, tk.END)
            self.psy_entry.insert(0, f"{Psi:.4f}")
            self.psy_entry.config(state='readonly')

            self.stt_entry.config(state='normal')
            self.stt_entry.delete(0, tk.END)
            self.stt_entry.insert(0, f"{Stt:.4f}")
            self.stt_entry.config(state='readonly')

            #self.area_multiplier_entry.config(state='normal')
            #self.area_multiplier_entry.delete(0, tk.END)
            #self.area_multiplier_entry.insert(0, f"{AREA_MULTIPLIER:.4f}")
            #self.area_multiplier_entry.config(state='readonly')

            self.save_to_ini(k, Fpom, v, psi_ud, tmax, Psi, Stt)

        except ValueError:
            messagebox.showerror("Ошибка", "Пожалуйста, введите допустимые положительные числа в поля ввода.")

    def save_to_ini(self, k, Fpom, v, psi_ud, tmax, Psi, Stt):
        config = configparser.ConfigParser()
        config['Calculations'] = {
            'k': k,
            'Fpom': Fpom,
            'v': v,
            'psi_ud': psi_ud,
            #'Sof': Sof,
            'tmax': tmax,
            'Psi': Psi,
            'Stt': Stt
            #'AREA_MULTIPLIER': AREA_MULTIPLIER
        }
        
        current_directory = os.path.dirname(__file__)
        parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
        inis_path = os.path.join(parent_directory, 'inis')
        
        ini_file = os.path.join(inis_path, 'IniApendix1.ini')

        with open(ini_file, 'w') as configfile:
            config.write(configfile)

    def read_ini_file(self, ini_file):
        config = configparser.ConfigParser()
        with open(ini_file, 'r', encoding='utf-16') as f:
            config.read_file(f)
        return config['filePath']['filePath']

    def process_fds_file(self, fds_path, MLRPUA, TAU_Q):
        modified_lines = []
        inside_surf_block = False
        vent_seen = False
        surf_id = None
        hrrpua_found = False 
        remove_ctrl_ramp = False

        with open(fds_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            for line in lines:
                if line.startswith('&SURF'):
                    match = re.search(r"ID='([^']*)'", line)
                    if match:
                        surf_id = match.group(1)

                    inside_surf_block = True
                    vent_seen = False
                    v = self.v_entry.get()
                    
                    if 'HRRPUA' in line:
                        hrrpua_found = True
                        inside_surf_block = True
                        modified_lines.append(f"&SURF ID='{surf_id}', ")
                        modified_lines.append(f"MLRPUA={MLRPUA}, ")
                        modified_lines.append(f"COLOR='RED', ")
                        modified_lines.append(f"TAU_Q={TAU_Q}/\n")
                    else:
                        hrrpua_found = False
                        modified_lines.append(line)
                    continue

                if inside_surf_block and hrrpua_found:
                    if line.startswith('&VENT'):
                        line = re.sub(r"CTRL_ID='[^']*'\s*", '', line)
                        if 'SPREAD_RATE' not in line:
                            line = line.rstrip('\n') + f" SPREAD_RATE={v}\n"
                        modified_lines.append(line)
                        vent_seen = True
                        continue

                    if '(end)' in line:
                        inside_surf_block = False
                        modified_lines.append(line)
                        continue

                    continue

                if line.startswith('&OBST'):
                    if 'CTRL_ID' in line:
                        line = re.sub(r"CTRL_ID='[^']*'\s*", '', line)
                        remove_ctrl_ramp = True

                    modified_lines.append(line)
                    continue

                if remove_ctrl_ramp and (line.startswith('&CTRL') or line.startswith('&RAMP')):
                    continue
                else:
                    remove_ctrl_ramp = False

                modified_lines.append(line)

        with open(fds_path.replace('.fds', '.fds'), 'w', encoding='utf-8') as file:
            file.writelines(modified_lines)

    def process_files(self):
        current_directory = os.path.dirname(__file__)
        parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
        inis_path = os.path.join(parent_directory, 'inis')
        
        ini_path = os.path.join(inis_path, 'filePath.ini')
        
        try:
            fds_path = self.read_ini_file(ini_path)
            MLRPUA = self.psy_entry.get()
            TAU_Q = -float(self.tmax_entry.get()) # Значение tmax в GUI отображается положительным, а когда оно идёт в TAU_Q, то становится отрицательным, чтобы удовлетворить условия назначения переменной TAU_Q в FDS
            #AREA_MULTIPLIER = self.area_multiplier_entry.get()
            if not MLRPUA or not TAU_Q: #or not AREA_MULTIPLIER:
                raise ValueError("Поля не должны быть пустыми")
            self.process_fds_file(fds_path, MLRPUA, TAU_Q)
            messagebox.showinfo("Готово!", f"Модифицированный .fds файл сохранён:\n\n{fds_path.replace('.fds', '.fds')}")
            app.quit() # Закрыть окно GUI после сохранения
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

if __name__ == "__main__":
    app = FDSProcessorApp()    
    app.mainloop()