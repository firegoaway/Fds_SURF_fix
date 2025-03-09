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

class MainWindow(QMainWindow):
    def __init__(self, process_id=None):
        super().__init__()
        self.unique_id = str(process_id) if process_id is not None else str(os.getpid())
        self.setWindowTitle(f"(\u03b1) Расчет СПДЗ v0.1.3 ID: {self.unique_id}")
        self.setGeometry(100, 100, 620, 640)
        self.inis_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "inis"))
        self.fds_file_ini_path = os.path.join(self.inis_folder, f"filePath_{self.unique_id}.ini")
        self.inideltaZ_ini_path = os.path.join(self.inis_folder, "InideltaZ.ini")
        self.init_ui()
        self.load_config()

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
        self.deltaZ_field.setEnabled(False)
        self.apply_button.setEnabled(False)
        self.track_button.setEnabled(True)

    def track_values(self):
        self.clear_layout(self.plot_layout)
        fds_dir = os.path.dirname(self.path_to_fds)
        csv_files = glob.glob(os.path.join(fds_dir, f"{self.chid}*_devc.csv"))
        devc_data = {}
        pattern_dev_id = re.compile(r'^(?:(h?(?:_\d+)?)|(Density_VM?(?:_\d+)?)|(Tg(?: 3D)?(?:_\d+)?)|(MFLOW\+?(?:_\d+)?))$', re.IGNORECASE)
        for csv_file in csv_files:
            try:
                with io.open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    lines_read = 0
                    headers = []
                    time_column = None
                    time_idx = -1
                    relevant_indices = {}
                    for row in reader:
                        lines_read += 1
                        if lines_read == 2:
                            headers = [h.strip().strip('"') for h in row]
                            for col in ["FDS Time", "Time"]:
                                if col in headers:
                                    time_column = col
                                    time_idx = headers.index(col)
                                    break
                            if time_column is None:
                                break
                            for idx, col_name in enumerate(headers):
                                if idx == time_idx:
                                    relevant_indices[idx] = time_column
                                else:
                                    m = pattern_dev_id.match(col_name)
                                    if m:
                                        relevant_indices[idx] = col_name
                                        if col_name not in devc_data:
                                            devc_data[col_name] = {"time": [], "values": []}
                        elif lines_read > 2 and time_column:
                            t_val = None
                            for idx in relevant_indices:
                                col_name = relevant_indices[idx]
                                if idx < len(row):
                                    cell_value = row[idx].strip()
                                    if col_name == time_column:
                                        try:
                                            t_val = float(cell_value)
                                        except:
                                            t_val = None
                                    else:
                                        if t_val is not None:
                                            try:
                                                val = float(cell_value)
                                            except:
                                                val = float('nan')
                                            devc_data[col_name]["time"].append(t_val)
                                            devc_data[col_name]["values"].append(val)
            except:
                pass
        devc_groups = {}
        for col_name, content in devc_data.items():
            m = pattern_dev_id.match(col_name)
            if m:
                quantity_raw = col_name
                g1, g2, g3, g4 = m.groups()
                group_id = ""
                if g1:
                    group_id = g1.split('_', 1)[-1] if '_' in g1 else "0"
                elif g2:
                    group_id = g2.split('_', 1)[-1] if '_' in g2 else "0"
                elif g3:
                    group_id = g3.split('_', 1)[-1] if '_' in g3 else "0"
                elif g4:
                    group_id = g4.split('_', 1)[-1] if '_' in g4 else "0"
                quantity = quantity_raw.split('_', 1)[0] if '_' in quantity_raw else quantity_raw
                quantity = quantity.replace("Tg 3D", "Tg").replace("Density_VM", "Density_VM").replace("MFLOW+", "MFLOW+").replace("h_", "h").replace("h", "h")
                if group_id not in devc_groups:
                    devc_groups[group_id] = {
                        "h": {"time":[], "values":[]},
                        "Density_VM": {"time":[], "values":[]},
                        "Tg": {"time":[], "values":[]},
                        "MFLOW+": {"time":[], "values":[]}
                    }
                devc_groups[group_id][quantity]["time"].extend(content["time"])
                devc_groups[group_id][quantity]["values"].extend(content["values"])
        results = []
        for group_id, data in devc_groups.items():
            valid_density = [v for v in data["Density_VM"]["values"] if not math.isnan(v)]
            valid_mflow = [v for v in data["MFLOW+"]["values"] if not math.isnan(v)]
            if valid_density and valid_mflow:
                density_min = min(valid_density)
                mflow_max = max(valid_mflow)
                gsm = mflow_max / density_min if density_min else 0
                gp = gsm * 0.7
                results.append({"group": group_id, "density_min": density_min, "mflow_max": mflow_max, "gsm": gsm, "gp": gp})
                group_layout = QVBoxLayout()
                group_title = QLabel(f"Группа {group_id}")
                group_title.setStyleSheet("font-weight: bold;")
                group_layout.addWidget(group_title)
                for quantity in ["h", "Density_VM", "Tg", "MFLOW+"]:
                    qdata = data[quantity]
                    if not qdata["values"]:
                        continue
                    valid_times = []
                    valid_values = []
                    for t, v in zip(qdata["time"], qdata["values"]):
                        if not math.isnan(v):
                            valid_times.append(t)
                            valid_values.append(v)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=valid_times, y=valid_values, mode='lines'))
                    yaxis_title = {
                        "h": "Высота дымового слоя (м)",
                        "Density_VM": "Среднеобъемная плотность газов (кг/м³)",
                        "Tg": "Среднеобъемная температура газов (°C)",
                        "MFLOW+": "Массовый расход газов (кг/с)"
                    }.get(quantity, "Значение")
                    fig.update_layout(
                        title=f"{quantity} (Группа {group_id})",
                        xaxis_title="Время (сек)",
                        yaxis_title=yaxis_title,
                        height=300
                    )
                    html = pio.to_html(fig, include_plotlyjs='cdn', full_html=False)
                    view = QWebEngineView()
                    view.setHtml(html)
                    group_layout.addWidget(view)
                results_text = f"GSM_{group_id} = {gsm:.4f}\nGP_{group_id} = {gp:.4f}\nGSMf_{group_id} = {gsm*3600:.4f}\nGPF_{group_id} = {gp*3600:.4f}"
                results_label = QLabel(results_text)
                results_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                group_layout.addWidget(results_label)
                self.plot_layout.addLayout(group_layout)
            else:
                error_label = QLabel(f"Недостаточно данных для расчета для группы {group_id}!")
                error_label.setStyleSheet("color: red;")
                self.plot_layout.addWidget(error_label)
        if not results:
            error_label = QLabel("Нет групп с достаточными данными для расчета!")
            error_label.setStyleSheet("color: red;")
            self.plot_layout.addWidget(error_label)
        self.save_plots_button.setEnabled(bool(results))

    def add_plots_to_layout(self, plots, title):
        self.plot_layout.addWidget(QLabel(title))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QHBoxLayout()
        container.setLayout(layout)
        for fig in plots:
            html = pio.to_html(fig, include_plotlyjs='cdn', full_html=False)
            view = QWebEngineView()
            view.setHtml(html)
            layout.addWidget(view)
        scroll.setWidget(container)
        self.plot_layout.addWidget(scroll)

    def save_plots(self):
        output_dir = os.path.dirname(self.path_to_fds)
        all_plots = self.non_koridor_plots + self.koridor_plots
        for i, fig in enumerate(all_plots, start=1):
            title = fig.layout.title.text
            plot_type = "koridor" if re.search(r'koridor', title, re.IGNORECASE) else "non_koridor"
            filename = f"{self.chid}_{plot_type}_plot_{i}.png"
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    process_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
    window = MainWindow(process_id)
    window.show()
    sys.exit(app.exec_())