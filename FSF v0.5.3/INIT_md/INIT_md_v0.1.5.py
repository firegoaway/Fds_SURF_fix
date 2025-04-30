import os
import re
import io
import csv
import sys
import glob
import json
import time
import configparser
from collections import defaultdict
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QScrollArea, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np

class MainWindow(QMainWindow):
    def __init__(self, process_id=None):
        super().__init__()
        self.unique_id = str(process_id) if process_id is not None else str(os.getpid())
        self.setWindowTitle(f"(\u03b2) Расчет СПДЗ v0.1.5 ID: {self.unique_id}")
        self.setGeometry(100, 100, 620, 640)
        self.inis_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "inis"))
        self.fds_file_ini_path = os.path.join(self.inis_folder, f"filePath_{self.unique_id}.ini")
        self.inideltaZ_ini_path = os.path.join(self.inis_folder, "InideltaZ.ini")
        self.plots = []
        self.init_ui()
        self.load_config()
        self.check_devc()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        controls_layout = QHBoxLayout()
        self.deltaZ_field = QLineEdit()
        self.apply_button = QPushButton("Применить")
        self.track_button = QPushButton("Рассчитать")
        self.save_plots_button = QPushButton("Сохранить графики")
        self.status_text = QLabel()
        controls_layout.addWidget(QLabel("Размер ячейки (Cs):"))
        controls_layout.addWidget(self.deltaZ_field)
        controls_layout.addWidget(self.apply_button)
        controls_layout.addWidget(self.track_button)
        controls_layout.addWidget(self.save_plots_button)
        layout.addLayout(controls_layout)
        layout.addWidget(self.status_text)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.plot_container = QWidget()
        self.plot_layout = QVBoxLayout()
        self.plot_container.setLayout(self.plot_layout)
        scroll_area.setWidget(self.plot_container)
        layout.addWidget(scroll_area)
        main_widget.setLayout(layout)
        self.apply_button.clicked.connect(self.apply_modifications)
        self.track_button.clicked.connect(self.track_values)
        self.save_plots_button.clicked.connect(self.save_plots)
        self.non_koridor_plots = []
        self.koridor_plots = []
        self.save_plots_button.setEnabled(False)

    def load_config(self):
        if not os.path.isfile(self.fds_file_ini_path):
            QMessageBox.critical(self, "Error", f"{self.fds_file_ini_path} not found")
            return
        if not os.path.isfile(self.inideltaZ_ini_path):
            QMessageBox.critical(self, "Error", f"{self.inideltaZ_ini_path} not found")
            return
        config = configparser.ConfigParser()
        with io.open(self.inideltaZ_ini_path, 'r', encoding='utf-16') as f:
            config.read_file(f)
        self.deltaZ_field.setText(config.get("InideltaZ", "deltaZ", fallback="0.5"))
        cfg_fds = configparser.ConfigParser()
        with io.open(self.fds_file_ini_path, 'r', encoding='utf-16') as f:
            cfg_fds.read_file(f)
        self.path_to_fds = None
        for section in cfg_fds.sections():
            if cfg_fds.has_option(section, "filePath"):
                self.path_to_fds = cfg_fds.get(section, "filePath")
                break
        if not self.path_to_fds:
            with io.open(self.fds_file_ini_path, 'r', encoding='utf-16') as f:
                self.path_to_fds = f.read().splitlines()[-1].strip()
        if not os.path.isfile(self.path_to_fds):
            QMessageBox.critical(self, "Error", f"FDS file '{self.path_to_fds}' not found")
            return
        self.chid = self.extract_chid_from_fds()
        print(f"CHID: {self.chid}")

    def extract_chid_from_fds(self):
        try:
            with open(self.path_to_fds, 'r', encoding='utf-8') as file:
                for line in file:
                    if line.strip().startswith("&HEAD") and "CHID=" in line:
                        match = re.search(r"CHID\s*=\s*['\"]?([^'\"]+)['\"]?", line)
                        if match:
                            return match.group(1).strip()
            raise ValueError("CHID not found")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error extracting CHID: {str(e)}")

    def apply_modifications(self):
        try:
            user_delta_z = float(self.deltaZ_field.text().strip())
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid deltaZ value!")
            return
        try:
            with io.open(self.path_to_fds, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read .fds file: {str(e)}")
            return
        updated_lines = []
        init_line_pattern = re.compile(r"^\s*&INIT.*TEMPERATURE\s*=\s*(\d+\.\d+)", re.IGNORECASE)
        xb_pattern = re.compile(r"XB\s*=\s*([-\d\.]+)\s*,\s*([-\d\.]+)\s*,\s*([-\d\.]+)\s*,\s*([-\d\.]+)\s*,\s*([-\d\.]+)\s*,\s*([-\d\.]+)", re.IGNORECASE)
        counters = defaultdict(int)
        mass_flow_created = set()
        for line in lines:
            updated_lines.append(line)
            match_init = init_line_pattern.search(line)
            if match_init:
                temperature_value_str = match_init.group(1)
                match_xb = xb_pattern.search(line)
                if not match_xb:
                    continue
                x1, x2, y1, y2, z1, z2 = map(float, match_xb.groups())
                z2_adjusted = z2 - user_delta_z
                suffix_match = re.search(r'\.(\d+)$', temperature_value_str)
                if not suffix_match:
                    continue
                group_key = suffix_match.group(1)
                counters[group_key] += 1
                devc_id_suffix = f"_{group_key}_{counters[group_key]}"
                devc_ids = [
                    f"h{devc_id_suffix}",
                    f"Density_VM{devc_id_suffix}",
                    f"Tg 3D{devc_id_suffix}"
                ]
                devc_lines = [
                    f"&DEVC ID='{devc_ids[0]}', QUANTITY='LAYER HEIGHT', XB={x1},{x2},{y1},{y2},{z1},{z2_adjusted}/\n",
                    f"&DEVC ID='{devc_ids[1]}', QUANTITY='DENSITY', STATISTICS='VOLUME MEAN', XB={x1},{x2},{y1},{y2},{z1},{z2_adjusted}/\n",
                    f"&DEVC ID='{devc_ids[2]}', QUANTITY='GAS TEMPERATURE', STATISTICS='MEAN', XB={x1},{x2},{y1},{y2},{z1},{z2_adjusted}/\n",
                ]
                if group_key not in mass_flow_created:
                    devc_ids_mass_flow = f"MFLOW+{devc_id_suffix}"
                    devc_lines.append(f"&DEVC ID='{devc_ids_mass_flow}', QUANTITY='MASS FLOW +', XB={x1},{x2},{y1},{y2},{z2_adjusted},{z2_adjusted}/\n")
                    mass_flow_created.add(group_key)
                updated_lines.extend(devc_lines)
        try:
            with io.open(self.path_to_fds, 'w', encoding='utf-8') as f:
                f.writelines(updated_lines)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not write to .fds file: {str(e)}")
            return
        self.status_text.setText("Файл .fds успешно изменён!")
        time.sleep(1.5)
        self.deltaZ_field.setEnabled(False)
        self.apply_button.setEnabled(False)
        self.track_button.setEnabled(True)
        time.sleep(1.5)
        sys.exit(app.exec_())

    def track_values(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            config_path = os.path.join(parent_dir, 'inis', f'filePath_{self.unique_id}.ini')
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"INI file not found at: {config_path}")
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-16')
            if not config.has_option('filePath', 'filePath'):
                raise ValueError("Missing [filePath] section or filePath key")
            fds_path = config.get('filePath', 'filePath')
            if not os.path.exists(fds_path):
                raise FileNotFoundError(f"FDS file not found at: {fds_path}")
            groups = self.parse_fds(fds_path)
            csv_dir = os.path.dirname(fds_path)
            csv_pattern = os.path.join(csv_dir, f'{self.chid}*_devc.csv')
            csv_files = glob.glob(csv_pattern)
            if not csv_files:
                raise FileNotFoundError(f"No CSV files found matching: {csv_pattern}")
            all_data = self.track_values_from_csv(csv_files, groups)
            self.calculate_and_plot(all_data, groups)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

    def parse_fds(self, fds_path):
        groups = defaultdict(list)
        current_group = None
        head_pattern = re.compile(r"&HEAD\s+CHID=['\"]([^'\"]+)['\"]", re.IGNORECASE)
        devc_pattern = re.compile(r"ID=['\"](h_\d{4}_\d+|Density_VM_\d{4}_\d+|Tg 3D_\d{4}_\d+|MFLOW\+_\d{4}_\d+)['\"]", re.IGNORECASE)
        with open(fds_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.upper().startswith('&HEAD'):
                    head_match = head_pattern.search(line)
                    if head_match:
                        self.chid = re.sub(r'(_nfs|_tout)+$', '', head_match.group(1))
                if line.upper().startswith('&INIT'):
                    temp_match = re.search(r'TEMPERATURE=(\d+\.\d{4})', line, re.IGNORECASE)
                    if temp_match:
                        current_group = temp_match.group(1).split('.')[-1][:4]
                elif line.upper().startswith('&DEVC'):
                    devc_match = devc_pattern.search(line)
                    if devc_match and current_group:
                        devc_id = devc_match.group(1)
                        groups[current_group].append(devc_id)
        return groups

    def track_values_from_csv(self, csv_files, groups):
        all_data = defaultdict(lambda: defaultdict(list))
        expected_columns = set()
        for group_ids in groups.values():
            expected_columns.update(group_ids)
        for csv_file in csv_files:
            with open(csv_file, 'r') as f:
                header_line = f.readline().strip()
                units_line = f.readline().strip()
                f.seek(0)
                reader = csv.DictReader(f)
                if any('/' in name for name in reader.fieldnames):
                    f.seek(0)
                    next(f)
                    reader = csv.DictReader(f)
                    reader.fieldnames = [name.strip('"').strip() for name in next(f).strip().split(',')]
                    reader = csv.DictReader(f, fieldnames=reader.fieldnames)
                reader.fieldnames = [name.strip('"').strip() for name in reader.fieldnames]
                csv_columns = set(reader.fieldnames)
                valid_columns = expected_columns & csv_columns
                for row_num, row in enumerate(reader, 1):
                    try:
                        time = float(row.get('Time', 0)) if 'Time' in row else float(row.get('FDS Time', 0))
                    except:
                        continue
                    for group, dev_ids in groups.items():
                        for dev_id in dev_ids:
                            if dev_id not in valid_columns:
                                continue
                            val = row.get(dev_id, '0')
                            try:
                                num_val = float(val)
                                num_val = 0.0 if np.isnan(num_val) else num_val
                            except:
                                num_val = 0.0
                            all_data[group][dev_id].append((time, num_val))
        return all_data

    def calculate_and_plot(self, all_data, groups):
        self.clear_layout(self.plot_layout)
        for group, dev_ids in groups.items():
            density_mins = []
            mflow_maxes = []
            categorized_data = {
                'h': {},
                'Density_VM': {},
                'Tg 3D': {},
                'MFLOW+': {}
            }
            for dev_id in dev_ids:
                dev_type = None
                if dev_id.startswith('h_'):
                    dev_type = 'h'
                elif dev_id.startswith('Density_VM'):
                    dev_type = 'Density_VM'
                elif dev_id.startswith('Tg 3D'):
                    dev_type = 'Tg 3D'
                elif dev_id.startswith('MFLOW+'):
                    dev_type = 'MFLOW+'
                if dev_type and dev_id in all_data[group]:
                    categorized_data[dev_type][dev_id] = all_data[group][dev_id]
                    if dev_type == 'Density_VM':
                        device_values = [v[1] for v in all_data[group][dev_id]]
                        if device_values:
                            density_mins.append(np.min(device_values))
                    elif dev_type == 'MFLOW+':
                        device_values = [v[1] for v in all_data[group][dev_id]]
                        if device_values:
                            mflow_maxes.append(np.max(device_values))
            density_avg_min = ((np.min(density_mins) + np.mean(density_mins)) / 2) + ((np.min(density_mins) - np.mean(density_mins)) / 10) if density_mins else 0
            mflow_avg_max = ((np.max(mflow_maxes) + np.mean(mflow_maxes)) / 2) + ((np.max(mflow_maxes) - np.mean(mflow_maxes)) / 10) if mflow_maxes else 0
            gsm = mflow_avg_max / density_avg_min if density_avg_min !=  0 else 0
            gp = gsm * 0.7
            Gsmf = gsm * 3600
            Gpf = gp * 3600
            self.create_group_block(group, categorized_data, Gsmf, Gpf, gsm, gp)
        self.save_plots_button.setEnabled(True)

    def create_group_block(self, group, categorized_data, Gsmf, Gpf, gsm, gp):
        container = QWidget()
        layout = QVBoxLayout(container)
        title = QLabel(f"Группа {group} | gsm: {gsm:.4f} | gp: {gp:.4f}\nРезультаты: | Gsmf: {Gsmf:.0f} | Gpf: {Gpf:.0f}")
        title.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title)
        plot_layout = QHBoxLayout()
        layout.addLayout(plot_layout)
        
        for dev_type, data in categorized_data.items():
            if data:
                fig = go.Figure()
                for dev_id, points in data.items():
                    times = [p[0] for p in points]
                    values = [p[1] for p in points]
                    fig.add_trace(go.Scatter(x=times, y=values, name=dev_id))
                fig.update_layout(title=f"Группа {group} - {dev_type}", height=400, showlegend=True, margin=dict(l=20, r=20, t=40, b=20))
                self.plots.append(fig)
                html = pio.to_html(fig, include_plotlyjs='cdn', full_html=False)
                web_view = QWebEngineView()
                web_view.setHtml(html)
                plot_layout.addWidget(web_view)
        
        self.plot_layout.addWidget(container)

    def save_plots(self):
        output_dir = os.path.dirname(self.path_to_fds)
        for i, fig in enumerate(self.plots, start=1):
            title = fig.layout.title.text
            group_id = title.split(' - ')[0].split('Группа ')[1]
            filename = f"{self.chid}_{group_id}_plot_{i}.png"
            pio.write_image(fig, os.path.join(output_dir, filename))
        QMessageBox.information(self, "Сохранение", "Графики успешно сохранены!")

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout:
                    self.clear_layout(sub_layout)

    def check_devc(self):
        try:
            with open(self.path_to_fds, 'r', encoding='utf-8') as file:
                for line in file:
                    if line.strip().startswith("&DEVC") and ("h_" in line or "Density_VM_" in line or "Tg 3D_" in line or "MFLOW+_" in line):
                        self.apply_button.setEnabled(False)
                        self.track_button.setEnabled(True)
                        return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error checking DEVC: {str(e)}")
        self.apply_button.setEnabled(True)
        self.track_button.setEnabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    process_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
    window = MainWindow(process_id)
    window.show()
    sys.exit(app.exec_())