import os
import re
import csv
import sys
import io
import glob
import json
import time
import configparser
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QScrollArea, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt
import plotly.graph_objects as go
import plotly.io as pio

class MainWindow(QMainWindow):
    def __init__(self, process_id=None):
        super().__init__()
        self.unique_id = str(process_id) if process_id is not None else str(os.getpid())
        self.setWindowTitle(f"(\u03b1) Расчет СПДЗ ID: {self.unique_id}")
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
        
        # Списки хранения
        self.non_koridor_plots = []
        self.koridor_plots = []
        
        # Кнопка сохранения графиков изначально выключена
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
        self.deltaZ_field.setText(config.get("InideltaZ", "deltaZ", fallback="0.75"))
        
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
        count_0001 = 0
        count_0002 = 0
        init_line_pattern = re.compile(r"^\s*&INIT.*TEMPERATURE\s*=\s*(\d+\.\d+)", re.IGNORECASE)
        xb_pattern = re.compile(r"XB\s*=\s*([-\d\.]+)\s*,\s*([-\d\.]+)\s*,\s*([-\d\.]+)\s*,\s*([-\d\.]+)\s*,\s*([-\d\.]+)\s*,\s*([-\d\.]+)", re.IGNORECASE)
        
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
                
                if temperature_value_str.endswith("0001"):
                    count_0001 += 1
                    devc_id_suffix = f"_{count_0001}"
                elif temperature_value_str.endswith("0002"):
                    count_0002 += 1
                    devc_id_suffix = f"_Koridor_{count_0002}"
                else:
                    continue
                    
                devc_ids = [
                    f"h{devc_id_suffix}",
                    f"Density_VM{devc_id_suffix}",
                    f"Tg 3D{devc_id_suffix}",
                    f"MFLOW+{devc_id_suffix}"
                ]
                
                devc_lines = [
                    f"&DEVC ID='{devc_ids[0]}', QUANTITY='LAYER HEIGHT', XB={x1},{x2},{y1},{y2},{z1},{z2_adjusted}/\n",
                    f"&DEVC ID='{devc_ids[1]}', QUANTITY='DENSITY', STATISTICS='VOLUME MEAN', XB={x1},{x2},{y1},{y2},{z1},{z2_adjusted}/\n",
                    f"&DEVC ID='{devc_ids[2]}', QUANTITY='GAS TEMPERATURE', STATISTICS='MEAN', XB={x1},{x2},{y1},{y2},{z1},{z2_adjusted}/\n",
                    f"&DEVC ID='{devc_ids[3]}', QUANTITY='MASS FLOW +', XB={x1},{x2},{y1},{y2},{z2_adjusted},{z2_adjusted}/\n",
                ]
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
    
    def track_values(self):
        self.clear_layout(self.plot_layout)
        fds_dir = os.path.dirname(self.path_to_fds)
        print(f"fds_dir: {fds_dir}")
        csv_files = glob.glob(os.path.join(fds_dir, f"{self.chid}*_devc.csv"))
        devc_data = {}
        pattern_dev_id = re.compile(r'^(h(_Koridor)?_\d+|Density_VM(_Koridor)?_\d+|Tg 3D(_Koridor)?_\d+|MFLOW\+(_Koridor)?_\d+)$', re.IGNORECASE)
        
        for csv_file in csv_files:
            try:
                with io.open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    lines_read = 0
                    headers = []
                    time_column = None
                    relevant_indices = {}
                    for row in reader:
                        lines_read += 1
                        if lines_read == 2:
                            headers = [h.strip().strip('"') for h in row]
                            possible_time_columns = ["FDS Time", "Time"]
                            for col in possible_time_columns:
                                if col in headers:
                                    time_column = col
                                    break
                            if not time_column:
                                print(f"Error: Time column not found in {csv_file}. Skipping.")
                                break
                            relevant_indices = {}
                            for idx, col_name in enumerate(headers):
                                if col_name == time_column:
                                    relevant_indices[idx] = time_column
                                elif pattern_dev_id.match(col_name):
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
                                                val = 0.0
                                            devc_data[col_name]["time"].append(t_val)
                                            devc_data[col_name]["values"].append(val)
            except Exception as e:
                print(f"Error processing {csv_file}: {str(e)}")
                continue
        
        density_vm_mins = []
        mflow_plus_values_for_avg = []
        non_koridor_plots = []
        koridor_plots = []
        
        self.non_koridor_plots = []
        self.koridor_plots = []
        
        for dev_id, data_dict in devc_data.items():
            t_arr = data_dict["time"]
            v_arr = data_dict["values"]
            if not t_arr or not v_arr:
                continue
            if dev_id.startswith("Density_VM"):
                local_min = min(v_arr)
                density_vm_mins.append(local_min)
            if dev_id.startswith("MFLOW+"):
                local_max = max(v_arr)
                mflow_plus_values_for_avg.append(local_max)
                
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=t_arr, y=v_arr, mode='lines', name=dev_id))
            yaxis_title = "Высота дымового слоя (м)" if dev_id.startswith("h") else \
                          "Среднеобъемная температура газов (°C)" if dev_id.startswith("Tg") else \
                          "Массовый расход газов (кг/с)" if dev_id.startswith("MFLOW+") else \
                          "Среднеобъемная плотность газов (кг/м³)" if dev_id.startswith("Density_VM") else "Value"
                          
            fig.update_layout(
                title=dev_id,
                xaxis_title="Время (сек)",
                yaxis_title=yaxis_title,
                height=400,
                width=450,
                margin=dict(l=50, r=50, t=50, b=50)
            )
            
            if "_Koridor_" in dev_id:
                self.koridor_plots.append(fig)
            else:
                self.non_koridor_plots.append(fig)
        
        self.add_plots_to_layout(self.non_koridor_plots, "Графики для помещения с очагом пожара:")
        self.add_plots_to_layout(self.koridor_plots, "Графики для остальных помещений:")
        
        density_vm_avg_min = None
        if density_vm_mins:
            density_vm_avg_min = sum(density_vm_mins) / len(density_vm_mins)
        
        if density_vm_avg_min is not None and mflow_plus_values_for_avg:
            avg_max_mflow_plus = sum(mflow_plus_values_for_avg) / len(mflow_plus_values_for_avg)
            gsm = avg_max_mflow_plus / density_vm_avg_min
            gp = gsm * 0.7
            results_text = f"Density_VM(AVG_MIN) = {density_vm_avg_min:.4f}\n" \
                           f"MFLOW+(AVG_MAX) = {avg_max_mflow_plus:.4f}\n" \
                           f"Gsm = {gsm:.4f}\n" \
                           f"Gp = {gp:.4f}\n" \
                           f"Gsmf = {gsm*3600:.4f}\n" \
                           f"Gpf = {gp*3600:.4f}"
            results_label = QLabel(results_text)
            results_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            results_label.setStyleSheet("font-size: 12px;")
            self.plot_layout.addWidget(results_label)
        else:
            error_label = QLabel("Недостаточно данных для расчета Gsm/Gp!")
            error_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            error_label.setStyleSheet("font-size: 10px; color: red;")
            self.plot_layout.addWidget(error_label)
            
        self.save_plots_button.setEnabled(True)
        
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
            plot_type = "koridor" if "_Koridor_" in title else "non_koridor"
            filename = f"{self.chid}_{plot_type}_plot_{i}.png"
            pio.write_image(fig, os.path.join(output_dir, filename))
        QMessageBox.information(self, "Сохранение", "Графики успешно сохранены!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    process_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
    window = MainWindow(process_id)
    window.show()
    sys.exit(app.exec_())