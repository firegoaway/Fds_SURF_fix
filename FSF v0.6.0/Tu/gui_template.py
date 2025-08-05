import numpy as np
import re
import math
import configparser
import os
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QTabWidget, QStatusBar, QLineEdit, QPushButton, QCheckBox, QMessageBox, QListWidget, QGroupBox, QFileDialog)
from PyQt6.QtGui import QPalette, QColor, QIcon, QIntValidator, QDoubleValidator, QFont
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QLocale

# Глобальная переменная для ProcessID, используемая для путей к ini-файлам.
# Инициализируется из аргументов командной строки при запуске.
ProcessID = None
if len(sys.argv) > 1:
    try:
        ProcessID = int(sys.argv[1])
        print(f"Process ID received from AHK: {ProcessID}")
    except ValueError:
        print(f"Invalid Process ID received: {sys.argv[1]}. Using None.")
        pass
else:
    print("No Process ID received.")
    pass



def find_best_factors(n):
    """
    Находит факторы числа n, которые обеспечивают сбалансированное деление по двум осям.
    Вспомогательная функция для split_mesh.
    """
    best_factors = (1, n)
    min_difference = float('inf')

    for i in range(1, int(n**0.5) + 1):
        if n % i == 0:
            factor_x = i
            factor_y = n // i
            difference = abs(factor_x - factor_y)

            if difference < min_difference:
                min_difference = difference
                best_factors = (factor_x, factor_y)

    return best_factors

def split_mesh(original_mesh, num_splits):
    """
    Разбивает одну расчетную область (mesh) на num_splits частей в плоскости XY.
    
    :param original_mesh: Словарь с данными оригинальной сетки (IJK, XB).
    :param num_splits: Желаемое количество разбиений.
    :return: Список словарей с данными новых сеток.
    """
    ijk = original_mesh['IJK']
    xb = original_mesh['XB']
    x1, x2, y1, y2, z1, z2 = xb

    def divide_into_parts(length, parts):
        part_length = length / parts
        offsets = [i * part_length for i in range(parts)]
        return offsets, [part_length] * parts

    num_splits_x, num_splits_y = find_best_factors(num_splits)

    x_offsets, dx_sizes = divide_into_parts(x2 - x1, num_splits_x)
    y_offsets, dy_sizes = divide_into_parts(y2 - y1, num_splits_y)
    
    ni = max(1, ijk[0] // num_splits_x)
    nj = max(1, ijk[1] // num_splits_y)

    split_meshes = []
    mesh_id = 1
    for ix in range(num_splits_x):
        for iy in range(num_splits_y):
            xb_new = [
                x1 + x_offsets[ix], x1 + x_offsets[ix] + dx_sizes[ix],
                y1 + y_offsets[iy], y1 + y_offsets[iy] + dy_sizes[iy],
                z1, z2
            ]
            ijk_new = [ni, nj, ijk[2]]
            mesh = {
                'ID': f'Mesh{mesh_id:02d}',
                'IJK': ijk_new,
                'XB': xb_new
            }
            split_meshes.append(mesh)
            mesh_id += 1

    return split_meshes

def split_mesh_homo(original_mesh, num_splits):
    """
    Разбивает одну расчетную область (mesh) на num_splits частей,
    стараясь сохранить гомоморфизм (пропорциональность) ячеек.
    
    :param original_mesh: Словарь с данными оригинальной сетки (IJK, XB).
    :param num_splits: Желаемое количество разбиений.
    :return: Список словарей с данными новых сеток.
    :raises ValueError: Если num_splits <= 0.
    """
    ijk = original_mesh['IJK']
    xb = original_mesh['XB']
    x1, x2, y1, y2, z1, z2 = xb

    if num_splits <= 0:
        raise ValueError("num_splits must be greater than 0")

    num_splits_z = 1 if ijk[2] < 4 else max(1, min(num_splits, 2))
    remaining_splits = num_splits // num_splits_z

    num_splits_x = max(1, int(math.sqrt(remaining_splits)))
    num_splits_y = max(1, remaining_splits // num_splits_x)

    # Корректировка факторов для достижения точного num_splits
    while num_splits_x * num_splits_y * num_splits_z < num_splits:
        if num_splits_y < num_splits_x:
            num_splits_y += 1
        else:
            num_splits_x += 1

    while num_splits_x * num_splits_y * num_splits_z > num_splits:
        if num_splits_y > num_splits_x:
            num_splits_y -= 1
        else:
            num_splits_x -= 1
    
    dx = (x2 - x1) / num_splits_x
    dy = (y2 - y1) / num_splits_y
    dz = (z2 - z1) / num_splits_z
    
    ni = ijk[0] // num_splits_x
    nj = ijk[1] // num_splits_y
    nk = ijk[2] // num_splits_z

    split_meshes = []
    mesh_id = 1

    for ix in range(num_splits_x):
        for iy in range(num_splits_y):
            for iz in range(num_splits_z):
                xb_new = [
                    x1 + ix * dx,
                    x1 + (ix + 1) * dx,
                    y1 + iy * dy,
                    y1 + (iy + 1) * dy,
                    z1 + iz * dz,
                    z1 + (iz + 1) * dz
                ]
                ijk_new = [ni, nj, nk]
                mesh = {
                    'ID': f'Mesh{mesh_id:02d}',
                    'IJK': ijk_new,
                    'XB': xb_new
                }
                split_meshes.append(mesh)
                mesh_id += 1

    return split_meshes

def partition_fds_content(lines, partition_value, homogeneous=False):
    """
    Разбивает одну расчетную область FDS файла на несколько.
    
    :param lines: Список строк FDS файла.
    :param partition_value: Желаемое количество разбиений.
    :param homogeneous: Если True, используется гомоморфное разбиение.
    :return: Модифицированное содержимое файла в виде списка строк.
    :raises ValueError: Если в файле нет MESH или он поврежден, или partition_value некорректно.
    """
    mesh_line_indices = [i for i, line in enumerate(lines) if line.startswith('&MESH')]
    if len(mesh_line_indices) != 1:
        raise ValueError("Файл сценария .fds должен иметь только одну расчетную область")

    original_mesh_line_index = mesh_line_indices[0]
    original_mesh_line = lines[original_mesh_line_index]
    
    ijk_match = re.search(r'IJK=\s*(\d+),(\d+),(\d+)', original_mesh_line)
    xb_match = re.search(r'XB=\s*([-+]?\d*\.?\d+),([-+]?\d*\.?\d+),([-+]?\d*\.?\d+),([-+]?\d*\.?\d+),([-+]?\d*\.?\d+),([-+]?\d*\.?\d+)', original_mesh_line)
    
    if not ijk_match or not xb_match:
        raise ValueError("Не удалось найти значения IJK or XB. Убедитесь, что .fds файл не поврежден.")

    ijk = list(map(int, ijk_match.groups()))
    xb = list(map(float, xb_match.groups()))

    original_mesh = {'IJK': ijk, 'XB': xb}
    num_splits = partition_value

    if num_splits <= 1:
        raise ValueError("Число разбиений должно быть целым положительным и больше 1")

    if homogeneous:
        split_meshes = split_mesh_homo(original_mesh, num_splits)
    else:
        split_meshes = split_mesh(original_mesh, num_splits)
        
    mesh_lines = []
    for mesh in split_meshes:
        xb_new = mesh['XB']
        ijk_new = mesh['IJK']
        mesh_line = f"&MESH ID='{mesh['ID']}', IJK={ijk_new[0]},{ijk_new[1]},{ijk_new[2]}, XB={xb_new[0]},{xb_new[1]},{xb_new[2]},{xb_new[3]},{xb_new[4]},{xb_new[5]} /\n"
        mesh_lines.append(mesh_line)
    
    # Replace the original MESH line with the new split meshes
    modified_lines = lines[:original_mesh_line_index] + mesh_lines + lines[original_mesh_line_index + 1:]
    return modified_lines

def calculate_cs(xmin, xmax, imin):
    """
    Вычисляет размер ячейки (cell size) по одному направлению.
    
    :param xmin: Минимальная координата.
    :param xmax: Максимальная координата.
    :param imin: Количество ячеек в этом направлении.
    :return: Размер ячейки.
    """
    if imin == 0:
        return float('inf') # Avoid division by zero, indicates an invalid mesh
    return (xmax - xmin) / imin

def parse_fds_file_for_meshes_refine(contents):
    """
    Парсит FDS файл и извлекает информацию о сетках для инструмента Refine/Coarsen.
    Возвращает список кортежей (I, J, K, Xmin, Xmax, Ymin, Ymax, Zmin, Zmax, line_index),
    общее количество ячеек и минимальное значение Cs.
    
    :param contents: Список строк FDS файла.
    :return: Кортеж: (список данных сеток, общее количество ячеек, минимальный Cs, исходные строки файла).
    """
    meshes_data = []
    total_cells = 0
    min_cs_value = float('inf')

    for i, line in enumerate(contents):
        match = re.search(r'&MESH\s.*?\bIJK=(\d+,\d+,\d+)\b.*?\bXB=([-\d\.]+,[-\d\.]+,[-\d\.]+,[-\d\.]+,[-\d\.]+,[-\d\.]+)\b', line)
        if match:
            IJK = match.group(1).split(',')
            XB = match.group(2).split(',')
            I, J, K = map(int, IJK)
            Xmin, Xmax, Ymin, Ymax, Zmin, Zmax = map(float, XB)
            
            cs_x = calculate_cs(Xmin, Xmax, I)
            cs_y = calculate_cs(Ymin, Ymax, J)
            cs_z = calculate_cs(Zmin, Zmax, K)
            Cs = min(cs_x, cs_y, cs_z)
            
            meshes_data.append((I, J, K, Xmin, Xmax, Ymin, Ymax, Zmin, Zmax, i)) 
            total_cells += I * J * K
            if Cs < min_cs_value:
                min_cs_value = Cs
    
    if min_cs_value == float('inf'):
        min_cs_value = 0.0 # Default if no meshes found or invalid Cs

    return meshes_data, total_cells, min_cs_value, contents

def refine_fds_meshes(contents, meshes_data, selected_mesh_indices, Csw):
    """
    Пересчитывает IJK для выбранных сеток на основе Csw и возвращает модифицированное содержимое FDS файла.
    Также обновляет файл IniDeltaZ.ini.
    
    :param contents: Список строк FDS файла.
    :param meshes_data: Список кортежей с данными сеток (I, J, K, Xmin, ..., line_index).
    :param selected_mesh_indices: Список индексов выбранных сеток из meshes_data.
    :param Csw: Желаемое значение Cs.
    :return: Модифицированное содержимое файла в виде списка строк.
    :raises ValueError: Если Csw некорректно или нет выбранных сеток.
    """
    if Csw <= 0:
        raise ValueError("Значение Csw должно быть положительным!")
    if not selected_mesh_indices:
        raise ValueError("Выберите хотя бы одну расчётную область из списка.")

    modified_contents = list(contents)

    for index in selected_mesh_indices:
        if index >= len(meshes_data):
            continue 

        I, J, K, Xmin, Xmax, Ymin, Ymax, Zmin, Zmax, line_index = meshes_data[index]
        
        Cs = min(calculate_cs(Xmin, Xmax, I), calculate_cs(Ymin, Ymax, J), calculate_cs(Zmin, Zmax, K))
        
        # Пересчитываем IJK, округляя до целого и обеспечивая минимум 1
        new_I = max(1, int(round(I * (Cs / Csw))))
        new_J = max(1, int(round(J * (Cs / Csw))))
        new_K = max(1, int(round(K * (Cs / Csw))))
        
        original_mesh_line = contents[line_index].strip()
        new_line = re.sub(r'IJK=\d+,\d+,\d+', f'IJK={new_I},{new_J},{new_K}', original_mesh_line)
        modified_contents[line_index] = new_line + "\n"

    # Обновление IniDeltaZ.ini
    try:
        current_directory = os.path.dirname(__file__)
        parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
        inis_path = os.path.join(parent_directory, 'inis')
        ini_delta_z_path = os.path.join(inis_path, 'IniDeltaZ.ini')
        
        config = configparser.ConfigParser()
        if os.path.exists(ini_delta_z_path):
            config.read(ini_delta_z_path, encoding='utf-16')
        
        if not config.has_section('deltaZ'):
            config.add_section('deltaZ')
            
        config.set('deltaZ', 'deltaZ', str(Csw))
        
        os.makedirs(inis_path, exist_ok=True)
        
        with open(ini_delta_z_path, 'w', encoding='utf-16') as configfile:
            config.write(configfile)

    except Exception as e:
        print(f"Ошибка при обновлении IniDeltaZ.ini: {e}")
        
    return modified_contents

def merge_fds_meshes(contents, Csw=None):
    """
    Объединяет все MESH области в FDS файле в одну большую область
    и пересчитывает IJK на основе заданного Csw.
    Также обрабатывает VENT-параметры.
    
    :param contents: Список строк FDS файла.
    :param Csw: Желаемое значение Cs. Если None, будет вычислено из существующих сеток.
    :return: Модифицированное содержимое файла в виде списка строк.
    :raises ValueError: Если не найдены MESH записи.
    """
    meshes_xb_only = []
    all_mesh_lines_ijk_xb = []

    lines = contents # Use the passed contents directly

    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith('&MESH'):
            params = dict(re.findall(r'(\w+)=([^=\s/]+)', stripped_line))
            if 'XB' in params:
                try:
                    xb = [float(val.strip()) for val in params['XB'].split(',')]
                    meshes_xb_only.append(xb)
                    if 'IJK' in params:
                        ijk = [int(val.strip()) for val in params['IJK'].split(',')]
                        all_mesh_lines_ijk_xb.append({'IJK': ijk, 'XB': xb})
                except ValueError:
                    pass
    
    if not meshes_xb_only:
        raise ValueError("В файле не найдено записей &MESH для объединения!")

    x_min = min(m[0] for m in meshes_xb_only)
    x_max = max(m[1] for m in meshes_xb_only)
    y_min = min(m[2] for m in meshes_xb_only)
    y_max = max(m[3] for m in meshes_xb_only)
    z_min = min(m[4] for m in meshes_xb_only)
    z_max = max(m[5] for m in meshes_xb_only)

    effective_csw = Csw
    if effective_csw is None:
        min_cs = []
        for mesh_data in all_mesh_lines_ijk_xb:
            ijk = mesh_data['IJK']
            xb = mesh_data['XB']
            # Ensure no division by zero if IJK is 0 for some reason
            cs_x = (xb[1] - xb[0]) / ijk[0] if ijk[0] != 0 else float('inf')
            cs_y = (xb[3] - xb[2]) / ijk[1] if ijk[1] != 0 else float('inf')
            cs_z = (xb[5] - xb[4]) / ijk[2] if ijk[2] != 0 else float('inf')
            
            current_min_cs = min(cs_x, cs_y, cs_z)
            if current_min_cs != float('inf'): # Only add valid Cs values
                min_cs.append(current_min_cs)
        effective_csw = min(min_cs) if min_cs else 0.1

    if effective_csw <= 0:
        raise ValueError("Вычисленное или заданное значение Csw должно быть положительным.")

    i = max(1, int(round((x_max - x_min) / effective_csw)))
    j = max(1, int(round((y_max - y_min) / effective_csw)))
    k = max(1, int(round((z_max - z_min) / effective_csw)))

    new_mesh_line = (
        f"&MESH IJK={i},{j},{k}, XB={x_min:.4f},{x_max:.4f},"
        f"{y_min:.4f},{y_max:.4f},{z_min:.4f},{z_max:.4f}/\n"
    )

    vent_faces_to_open = {
        'xmin': False, 'xmax': False,
        'ymin': False, 'ymax': False,
        'zmin': False, 'zmax': False
    }

    new_fds_lines = []
    mesh_line_inserted = False

    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith('&MESH'):
            if not mesh_line_inserted:
                new_fds_lines.append(new_mesh_line)
                mesh_line_inserted = True
            continue
        elif stripped_line.startswith('&VENT'):
            if "SURF_ID='OPEN'" in stripped_line or 'SURF_ID="OPEN"' in stripped_line:
                params = dict(re.findall(r'(\w+)=([^=\s/]+)', stripped_line))
                if 'XB' in params:
                    try:
                        xb_vent = [float(val.strip()) for val in params['XB'].split(',')]
                        tol = 1e-6
                        if abs(xb_vent[0] - xb_vent[1]) < tol:
                            if abs(xb_vent[0] - x_min) < tol: vent_faces_to_open['xmin'] = True
                            elif abs(xb_vent[0] - x_max) < tol: vent_faces_to_open['xmax'] = True
                        elif abs(xb_vent[2] - xb_vent[3]) < tol:
                            if abs(xb_vent[2] - y_min) < tol: vent_faces_to_open['ymin'] = True
                            elif abs(xb_vent[2] - y_max) < tol: vent_faces_to_open['ymax'] = True
                        elif abs(xb_vent[4] - xb_vent[5]) < tol:
                            if abs(xb_vent[4] - z_min) < tol: vent_faces_to_open['zmin'] = True
                            elif abs(xb_vent[4] - z_max) < tol: vent_faces_to_open['zmax'] = True
                    except ValueError:
                        pass
            continue
        new_fds_lines.append(line)

    new_vent_lines = []
    if vent_faces_to_open['xmin']: new_vent_lines.append(f"&VENT XB={x_min:.4f},{x_min:.4f},{y_min:.4f},{y_max:.4f},{z_min:.4f},{z_max:.4f} SURF_ID='OPEN'/\n")
    if vent_faces_to_open['xmax']: new_vent_lines.append(f"&VENT XB={x_max:.4f},{x_max:.4f},{y_min:.4f},{y_max:.4f},{z_min:.4f},{z_max:.4f} SURF_ID='OPEN'/\n")
    if vent_faces_to_open['ymin']: new_vent_lines.append(f"&VENT XB={x_min:.4f},{x_max:.4f},{y_min:.4f},{y_min:.4f},{z_min:.4f},{z_max:.4f} SURF_ID='OPEN'/\n")
    if vent_faces_to_open['ymax']: new_vent_lines.append(f"&VENT XB={x_min:.4f},{x_max:.4f},{y_max:.4f},{y_max:.4f},{z_min:.4f},{z_max:.4f} SURF_ID='OPEN'/\n")
    if vent_faces_to_open['zmin']: new_vent_lines.append(f"&VENT XB={x_min:.4f},{x_max:.4f},{y_min:.4f},{y_max:.4f},{z_min:.4f},{z_min:.4f} SURF_ID='OPEN'/\n")
    if vent_faces_to_open['zmax']: new_vent_lines.append(f"&VENT XB={x_min:.4f},{x_max:.4f},{y_min:.4f},{y_max:.4f},{z_max:.4f},{z_max:.4f} SURF_ID='OPEN'/\n")

    try:
        insert_index = new_fds_lines.index(new_mesh_line) + 1
        new_fds_lines[insert_index:insert_index] = new_vent_lines
    except ValueError:
        new_fds_lines.extend(new_vent_lines)
            
    return new_fds_lines

from PyQt6.QtCore import Qt, QSize, pyqtSignal

class FDSFileSelectionWidget(QWidget):
    file_selected = pyqtSignal(str, list)
    status_message_signal = pyqtSignal(str) # Новый сигнал для статус-бара

    def __init__(self, process_id=None):
        super().__init__()
        self.process_id = process_id
        self.file_path_label = None # Инициализация здесь для _open_file_dialog
        self.select_button = None # Инициализация здесь для _open_file_dialog
        self._setup_ui()

    def _get_button_style(self):
        """Возвращает стиль для кнопок."""
        return """
            QPushButton {
                background-color: #bae6fd;
                color: #0369a1;
                border: none;
                border-radius: 5px;
                padding: 10px 15px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #7dd3fc;
            }
            QPushButton:pressed {
                background-color: #0284c7;
                color: white;
            }
            QPushButton:disabled {
                background-color: #e2e8f0;
                color: #94a3b8;
            }
        """

    def _setup_ui(self):
        """
        Настраивает пользовательский интерфейс для виджета выбора файла FDS.
        """
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # Инструкция
        instruction_label = QLabel("Выберите файл FDS:")
        instruction_label.setStyleSheet("font-weight: bold; color: #0284c7;")
        main_layout.addWidget(instruction_label)

        # Кнопка выбора файла
        self.select_button = QPushButton("Выбрать .fds")
        self.select_button.setStyleSheet(self._get_button_style())
        self.select_button.clicked.connect(self._open_file_dialog)
        main_layout.addWidget(self.select_button)

        # Лейбл для отображения пути к файлу
        self.file_path_label = QLabel("Файл не выбран")
        self.file_path_label.setStyleSheet("font-style: italic; color: #64748b;")
        main_layout.addWidget(self.file_path_label)

        main_layout.addStretch(1) # Добавляем растяжку для выравнивания влево

    def _read_ini_file(self, ini_file_path):
        """
        Чтение пути к файлу из INI-файла.
        
        :param ini_file_path: Путь к INI-файлу.
        :return: Путь к файлу FDS.
        :raises FileNotFoundError: Если INI-файл не найден.
        :raises configparser.Error: Если INI-файл поврежден.
        """
        config = configparser.ConfigParser()
        if not os.path.exists(ini_file_path):
            raise FileNotFoundError(f"INI-файл не найден: {ini_file_path}")
        
        with open(ini_file_path, 'r', encoding='utf-16') as f:
            config.read_file(f)
        
        if 'filePath' not in config or 'filePath' not in config['filePath']:
            raise configparser.Error("INI-файл не содержит секцию 'filePath' или ключ 'filePath'.")
            
        return config['filePath']['filePath']

    def _read_fds_file(self, file_path):
        """
        Чтение содержимого FDS файла.
        
        :param file_path: Путь к FDS файлу.
        :return: Список строк файла.
        :raises FileNotFoundError: Если FDS файл не найден.
        """
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        return lines

    def _open_file_dialog(self):
        """
        Открывает диалог выбора файла или читает путь из INI-файла,
        затем считывает FDS файл и эмитирует сигнал.
        Возвращает True, если файл успешно загружен, иначе False.
        """
        fds_file_path = None
        fds_lines = []
        
        loaded_successfully = False # Flag to track if file was loaded
        
        try:
            if self.process_id is None:
                # Если ProcessID не был предоставлен, открываем QFileDialog для выбора файла
                fds_file_path, _ = QFileDialog.getOpenFileName(self, "Открыть FDS файл", "", "FDS Files (*.fds);;All Files (*)")
                if fds_file_path and os.path.exists(fds_file_path):
                    fds_lines = self._read_fds_file(fds_file_path)
                    self.file_path_label.setText(os.path.basename(fds_file_path))
                    self.file_selected.emit(fds_file_path, fds_lines)
                    self.status_message_signal.emit(f"Файл загружен: {os.path.basename(fds_file_path)}")
                    loaded_successfully = True
                    self.select_button.setEnabled(False) # Отключение кнопки после успешной загрузки вручную
                else:
                    if fds_file_path: # User selected a path that doesn't exist
                        QMessageBox.warning(self, "Ошибка", f"Файл не найден: {fds_file_path}")
                    self.file_path_label.setText("Файл не выбран")
                    self.status_message_signal.emit("Выбор файла отменен или файл не найден.")
                    self.select_button.setEnabled(True) # Re-enable if it was disabled
            else:
                # Если ProcessID предоставлен, пытаемся найти ini-файл
                current_directory = os.path.dirname(__file__)
                parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
                inis_path = os.path.join(parent_directory, 'inis')
                ini_path = os.path.join(inis_path, f'filePath_{self.process_id}.ini')

                try:
                    fds_file_path = self._read_ini_file(ini_path)
                    if fds_file_path and os.path.exists(fds_file_path):
                        fds_lines = self._read_fds_file(fds_file_path)
                        self.file_path_label.setText(os.path.basename(fds_file_path))
                        self.file_selected.emit(fds_file_path, fds_lines)
                        self.select_button.setEnabled(False) # Disable button if file loaded via INI
                        self.status_message_signal.emit(f"Файл загружен: {os.path.basename(fds_file_path)}")
                        loaded_successfully = True
                    else:
                        QMessageBox.warning(self, "Файл конфигурации отсутствует",
                                            "Не найден файл конфигурации (INI). Пожалуйста, укажите путь к файлу FDS вручную или убедитесь, что файл filePath_<ProcessID>.ini существует.")
                        self.select_button.setEnabled(True) # Re-enable if it was disabled
                        self.file_path_label.setText("Файл не выбран")
                        self.status_message_signal.emit("Ошибка: INI-файл не найден.")
                except FileNotFoundError:
                    QMessageBox.warning(self, "Файл конфигурации отсутствует",
                                        "Не найден файл конфигурации (INI). Пожалуйста, укажите путь к файлу FDS вручную или убедитесь, что файл filePath_<ProcessID>.ini существует.")
                    self.select_button.setEnabled(True) # Re-enable if it was disabled
                    self.file_path_label.setText("Файл не выбран")
                    self.status_message_signal.emit("Ошибка: INI-файл не найден.")
                except configparser.Error:
                    QMessageBox.warning(self, "Ошибка INI файла", "INI файл не содержит путь к файлу FDS или поврежден.")
                    self.select_button.setEnabled(True) # Re-enable if it was disabled
                    self.file_path_label.setText("Файл не выбран")
                    self.status_message_signal.emit("Ошибка: INI-файл поврежден.")
            
        except Exception as e:
            QMessageBox.warning(self, "Ошибка загрузки файла", str(e))
            self.file_path_label.setText("Файл не выбран")
            self.select_button.setEnabled(True) # Re-enable if it was disabled
            self.status_message_signal.emit(f"Ошибка загрузки файла: {str(e)}")
            
        return loaded_successfully

class FDSMeshToolsApp(QMainWindow):
    def __init__(self, process_id=None):
        super().__init__()
        
        self.fds_file_path = None
        self.fds_lines = []
        self.partition_label = None
        self.partition_entry = None
        self.homomorph_var = None
        self.partition_button = None
        self.meshes = [] # Добавлено для Refine tab
        self.total_cells = 0 # Добавлено для Refine tab
        self.cs_entry = None
        self.csw_entry = None
        self.refine_list_widget = None
        self.total_cells_label = None

        # Определяем путь к иконке относительно текущего скрипта
        current_directory = os.path.dirname(__file__)
        self.parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
        icon_path = os.path.join(self.parent_directory, '.gitpics', 'FMT3.ico') # Updated icon for main window
        self.setWindowIcon(QIcon(icon_path))
        
        self.setWindowTitle("FDS Mesh Tools v0.3.0")
        self.setMinimumSize(800, 600) # Увеличим размер окна для удобства
        
        self.process_id = process_id
         
        self._setup_palette()
        self._setup_ui()
        
        # If process_id is provided, try to load the file automatically
        if self.process_id is not None:
            file_loaded = self.fds_file_selection_widget._open_file_dialog()
            if file_loaded:
                self.fds_file_selection_widget.hide() # Hide if file loaded successfully via process_id
            else:
                self.fds_file_selection_widget.show() # Show if auto-load failed, allowing manual selection
        else:
            # If no process_id, always show the widget for manual file selection
            self.fds_file_selection_widget.show()
        
    def _setup_palette(self):
        """Установка цветовой палитры для приложения."""
        palette = QPalette()
        # Определение современной, светлой цветовой схемы
        palette.setColor(QPalette.ColorRole.Window, QColor(248, 250, 252))  # Очень светло-синяя
        palette.setColor(QPalette.ColorRole.WindowText, QColor(30, 41, 59))  # Темно-синяя
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))  # Чистая белая
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(241, 245, 249))  # Светло-синяя
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))  # Чистая белая
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(30, 41, 59))  # Темно-синяя
        palette.setColor(QPalette.ColorRole.Text, QColor(30, 41, 59))  # Темно-синяя
        palette.setColor(QPalette.ColorRole.Button, QColor(186, 230, 253))  # Светло-синяя кнопки
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(3, 105, 161))  # Темно-синяя текст на кнопках
        palette.setColor(QPalette.ColorRole.Highlight, QColor(125, 211, 252))  # Светло-синяя выделение
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(30, 41, 59))  # Темно-синяя текст для контраста
        self.setPalette(palette)
        
    def _setup_ui(self):
        """Установка основных компонентов интерфейса."""
        # Установка шрифта приложения
        app_font = QFont("Segoe UI", 10)
        QApplication.setFont(app_font)

        self.statusBar = QStatusBar()
        self.statusBar.setStyleSheet("QStatusBar { background-color: rgb(241, 245, 249); color: rgb(30, 41, 59); }")
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Готово")
        
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20) # Apply margins
        main_layout.setSpacing(15) # Apply spacing
        self.setCentralWidget(central_widget)

        # Заголовок приложения
        header = QLabel("FDS Mesh Tools")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: rgb(3, 105, 161); padding: 10px;")
        main_layout.addWidget(header)
        
        # File Selection Widget (Moved here to be above tabs)
        self.fds_file_selection_widget = FDSFileSelectionWidget(self.process_id)
        main_layout.addWidget(self.fds_file_selection_widget)
        # Connect signals from the file selection widget
        self.fds_file_selection_widget.file_selected.connect(self._handle_file_selected)
        self.fds_file_selection_widget.status_message_signal.connect(self.statusBar.showMessage)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #bfdbfe;
                border-radius: 5px;
                background-color: white;
            }
            QTabBar {
                qproperty-drawBase: 0; /* Remove background of the tab bar itself */
            }
            QTabBar::tab {
                background-color: #e0f2fe;
                color: #0284c7;
                padding: 8px 16px;
                margin-right: 0px; /* Make tabs touch each other */
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 0; /* Allow shrinking */
            }
            QTabBar::tab:selected {
                background-color: #bae6fd;
                color: #0369a1;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #7dd3fc;
            }
        """)
        main_layout.addWidget(self.tab_widget)
        
        # Setup Partition Tab
        self._setup_partition_tab()
        
        # Add Refine Tab
        self._setup_refine_tab()

    
    def _get_group_box_style(self):
        """Возвращает стиль для групповых боксов."""
        return """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #bfdbfe;
                border-radius: 8px;
                margin-top: 1ex;
                background-color: rgba(255, 255, 255, 200);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """

    def _get_input_style(self):
        """Возвращает стиль для полей ввода."""
        return """
            QLineEdit {
                padding: 12px; /* Increased padding for larger input fields */
                border: 1px solid #cbd5e1;
                border-radius: 5px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #7dd3fc;
            }
        """

    def _get_button_style(self):
        """Возвращает стиль для кнопок."""
        return """
            QPushButton {
                background-color: #bae6fd;
                color: #0369a1;
                border: none;
                border-radius: 5px;
                padding: 10px 15px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #7dd3fc;
            }
            QPushButton:pressed {
                background-color: #0284c7;
                color: white;
            }
            QPushButton:disabled {
                background-color: #e2e8f0;
                color: #94a3b8;
            }
        """

    def _get_checkbox_style(self):
        """Возвращает стиль для флажков."""
        return """
            QCheckBox {
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #94a3b8;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #0284c7;
                border-radius: 4px;
                background-color: #0284c7;
            }
        """

    def _setup_refine_tab(self):
        """Sets up the UI for the Refine/Coarsen tab."""
        refine_tab = QWidget()
        refine_layout = QVBoxLayout(refine_tab)
        refine_layout.setContentsMargins(15, 15, 15, 15) # Adding margins for consistency
        refine_layout.setSpacing(15) # Adding spacing for consistency

        # Top section with buttons and entries
        top_layout = QHBoxLayout()


        top_layout.addWidget(QLabel("Cs:"))
        self.cs_entry = QLineEdit()
        self.cs_entry.setStyleSheet(self._get_input_style())
        self.cs_entry.setReadOnly(True)
        # self.cs_entry.setFixedSize(80, 25) # Removed fixed size to allow padding to take effect
        top_layout.addWidget(self.cs_entry)

        top_layout.addWidget(QLabel("Csw:"))
        self.csw_entry = QLineEdit()
        self.csw_entry.setStyleSheet(self._get_input_style())
        self.csw_entry.setPlaceholderText("Введите Cs")
        validator = QDoubleValidator(0.000001, 999999.999999, 6)
        validator.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.csw_entry.setValidator(validator)
        # self.csw_entry.setFixedSize(80, 25) # Removed fixed size to allow padding to take effect
        top_layout.addWidget(self.csw_entry)

        self.refine_button = QPushButton("Преобразовать")
        self.refine_button.setStyleSheet(self._get_button_style())
        self.refine_button.clicked.connect(self.refine_mesh)
        self.refine_button.setEnabled(False)
        top_layout.addWidget(self.refine_button)

        self.merge_button = QPushButton("Объединить")
        self.merge_button.setStyleSheet(self._get_button_style())
        self.merge_button.clicked.connect(self.merge_meshes)
        self.merge_button.setEnabled(False)
        top_layout.addWidget(self.merge_button)
        
        refine_layout.addLayout(top_layout)

        # List Widget for meshes
        self.refine_list_widget = QListWidget()
        self.refine_list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        refine_layout.addWidget(self.refine_list_widget)

        # Bottom section with select/unselect all and total cells label
        bottom_layout = QHBoxLayout()

        self.select_all_button = QPushButton("Выбрать все")
        self.select_all_button.setStyleSheet(self._get_button_style())
        self.select_all_button.clicked.connect(self.select_all_refine)
        self.select_all_button.setEnabled(False)
        bottom_layout.addWidget(self.select_all_button)

        self.unselect_all_button = QPushButton("Снять выбор")
        self.unselect_all_button.setStyleSheet(self._get_button_style())
        self.unselect_all_button.clicked.connect(self.unselect_all_refine)
        self.unselect_all_button.setEnabled(False)
        bottom_layout.addWidget(self.unselect_all_button)

        self.total_cells_label = QLabel("Всего ячеек: 0")
        bottom_layout.addWidget(self.total_cells_label)
        bottom_layout.addStretch(1) # Pushes other widgets to the left

        refine_layout.addLayout(bottom_layout)
        
        self.tab_widget.addTab(refine_tab, QIcon(os.path.join(self.parent_directory, '.gitpics', 'Refiner-Coarsener.ico')), "Refine/Coarsen")

    def _setup_partition_tab(self):
        """Sets up the UI for the Partition tab."""
        partition_tab = QWidget()
        partition_layout = QVBoxLayout(partition_tab)
        partition_layout.setContentsMargins(15, 15, 15, 15) # Adding margins for consistency with gui_template
        partition_layout.setSpacing(15) # Adding spacing for consistency with gui_template

        # Group box for Partition settings
        partition_group = QGroupBox("Параметры разбиения")
        partition_group.setStyleSheet(self._get_group_box_style()) # Using a common style for group boxes
        partition_layout_grouped = QVBoxLayout(partition_group)
        partition_layout_grouped.setSpacing(10)

        # Partition Label and Entry
        self.partition_label = QLabel("Число разбиений:")
        partition_layout_grouped.addWidget(self.partition_label)

        self.partition_entry = QLineEdit()
        self.partition_entry.setStyleSheet(self._get_input_style())
        self.partition_entry.setPlaceholderText("Введите целое положительное ненулевое значение.")
        self.partition_entry.setToolTip("Введите целое положительное ненулевое значение.")
        self.partition_entry.setValidator(QIntValidator(1, 999999)) # Restrict to positive integers
        self.partition_entry.setEnabled(False)  # Initially disabled
        partition_layout_grouped.addWidget(self.partition_entry) # Changed to partition_layout_grouped
 
        # Homomorph Checkbox
        self.homomorph_var = QCheckBox("Сохранять гомоморфизм разбиений")
        self.homomorph_var.setStyleSheet(self._get_checkbox_style())
        self.homomorph_var.setToolTip("Соблюсти пропорции размеров сетки.")
        partition_layout_grouped.addWidget(self.homomorph_var) # Changed to partition_layout_grouped
 
        # Partition Button
        self.partition_button = QPushButton("Разбить")
        self.partition_button.setStyleSheet(self._get_button_style())
        self.partition_button.setEnabled(False)  # Initially disabled
        self.partition_button.clicked.connect(self.on_partition_button)
        partition_layout_grouped.addWidget(self.partition_button) # Changed to partition_layout_grouped
 
        partition_layout.addWidget(partition_group) # Add the group box to the main partition layout
        # Add stretch to push widgets to the top
        partition_layout.addStretch(1)
 
        self.tab_widget.addTab(partition_tab, QIcon(os.path.join(self.parent_directory, '.gitpics', 'Partition.ico')), "Partition")


    def _handle_file_selected(self, file_path, fds_lines):
        """
        Обрабатывает сигнал file_selected от FDSFileSelectionWidget.
        Обновляет self.fds_file_path и self.fds_lines, а также
        включает/выключает соответствующие элементы управления.
        """
        self.fds_file_path = file_path
        self.fds_lines = fds_lines
        
        if file_path and fds_lines:
            if any(line.strip().startswith('&MESH') for line in fds_lines):
                self.partition_entry.setEnabled(True)
                self.partition_button.setEnabled(True)
                self.parse_file_refine(file_path, fds_lines) # Call to update Refine tab
            else:
                QMessageBox.warning(self, "Ошибка", "Расчетная область (&MESH) не найдена в файле.")
                self.partition_entry.setEnabled(False)
                self.partition_button.setEnabled(False)
                # Also update Refine tab if a file was previously loaded but is now invalid
                self.refine_button.setEnabled(False)
                self.merge_button.setEnabled(False)
                self.select_all_button.setEnabled(False)
                self.unselect_all_button.setEnabled(False)
                self.cs_entry.setText("")
                self.total_cells_label.setText("Всего ячеек: 0")
                self.refine_list_widget.clear()
        else:
            self.partition_entry.setEnabled(False)
            self.partition_button.setEnabled(False)
            # Also update Refine tab if a file was previously loaded but is now invalid/cleared
            self.refine_button.setEnabled(False)
            self.merge_button.setEnabled(False)
            self.select_all_button.setEnabled(False)
            self.unselect_all_button.setEnabled(False)
            self.cs_entry.setText("")
            self.total_cells_label.setText("Всего ячеек: 0")
            self.refine_list_widget.clear()

    def parse_file_refine(self, file_path, contents):
        """
        Парсит FDS файл и извлекает информацию о сетках для вкладки Refine/Coarsen.
        """
        try:
            meshes_data, total_cells, min_cs_value, _ = parse_fds_file_for_meshes_refine(contents)
            
            self.meshes = meshes_data
            self.total_cells = total_cells
            self.fds_lines = contents # Update self.fds_lines from passed contents
            
            # Очистить QListWidget
            self.refine_list_widget.clear()
            
            # Заполнить QListWidget
            for I, J, K, Xmin, Xmax, Ymin, Ymax, Zmin, Zmax, line_index in self.meshes:
                Cs_x = calculate_cs(Xmin, Xmax, I)
                Cs_y = calculate_cs(Ymin, Ymax, J)
                Cs_z = calculate_cs(Zmin, Zmax, K)
                Cs = min(Cs_x, Cs_y, Cs_z)
                line_content = self.fds_lines[line_index].strip()
                self.refine_list_widget.addItem(f"{line_content}    Cs={Cs:.4f}")
            
            # Обновить cs_entry с минимальным Cs
            self.cs_entry.setText(f"{min_cs_value:.4f}")
            
            # Обновить total_cells_label
            self.total_cells_label.setText(f"Всего ячеек: {self.total_cells}")
            
            # Включить кнопки
            self.refine_button.setEnabled(True)
            self.merge_button.setEnabled(True)
            self.select_all_button.setEnabled(True)
            self.unselect_all_button.setEnabled(True)
            
            self.statusBar.showMessage(f"Файл загружен: {os.path.basename(file_path)}")
            
        except Exception as e:
            QMessageBox.warning(self, "Ошибка парсинга файла", str(e))
            self.refine_button.setEnabled(False)
            self.merge_button.setEnabled(False)
            self.select_all_button.setEnabled(False)
            self.unselect_all_button.setEnabled(False)

    def on_partition_button(self):
        """
        Handles the partition button click event.
        Replaces the Tkinter on_partition_button logic.
        """
        try:
            partition_value_str = self.partition_entry.text()
            if not partition_value_str:
                QMessageBox.warning(self, "Ошибка ввода", "Пожалуйста, введите число разбиений.")
                return

            partition_value = int(partition_value_str)
            if partition_value <= 1:
                raise ValueError("Число разбиений должно быть целым положительным и больше 1")

            is_homogeneous = self.homomorph_var.isChecked()

            if not self.fds_lines or not self.fds_file_path:
                QMessageBox.warning(self, "Ошибка", "Файл FDS не загружен или некорректен.")
                return

            if is_homogeneous:
                modified_lines = partition_fds_content(self.fds_lines, partition_value, homogeneous=True)
            else:
                modified_lines = partition_fds_content(self.fds_lines, partition_value, homogeneous=False)

            if modified_lines is not None:
                write_fds_file(self.fds_file_path, modified_lines)
                QMessageBox.information(self, "Успех!", f"Расчетная область поделена на {partition_value} частей.")
                self.parse_file_refine(self.fds_file_path, modified_lines)
        except ValueError as ve:
            QMessageBox.warning(self, "Ошибка ввода", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Критическая ошибка", f"Произошла непредвиденная ошибка: {e}")

    def parse_file_refine(self, file_path, contents):
        """
        Парсит FDS файл и извлекает информацию о сетках для вкладки Refine/Coarsen.
        """
        try:
            meshes_data, total_cells, min_cs_value, _ = parse_fds_file_for_meshes_refine(contents)
            
            self.meshes = meshes_data
            self.total_cells = total_cells
            self.fds_lines = contents # Update self.fds_lines from passed contents
            
            # Очистить QListWidget
            self.refine_list_widget.clear()
            
            # Заполнить QListWidget
            for I, J, K, Xmin, Xmax, Ymin, Ymax, Zmin, Zmax, line_index in self.meshes:
                Cs_x = calculate_cs(Xmin, Xmax, I)
                Cs_y = calculate_cs(Ymin, Ymax, J)
                Cs_z = calculate_cs(Zmin, Zmax, K)
                Cs = min(Cs_x, Cs_y, Cs_z)
                line_content = self.fds_lines[line_index].strip()
                self.refine_list_widget.addItem(f"{line_content}    Cs={Cs:.4f}")
            
            # Обновить cs_entry с минимальным Cs
            self.cs_entry.setText(f"{min_cs_value:.4f}")
            
            # Обновить total_cells_label
            self.total_cells_label.setText(f"Всего ячеек: {self.total_cells}")
            
            # Включить кнопки
            self.refine_button.setEnabled(True)
            self.merge_button.setEnabled(True)
            self.select_all_button.setEnabled(True)
            self.unselect_all_button.setEnabled(True)
            
            self.statusBar.showMessage(f"Файл загружен: {os.path.basename(file_path)}")
            
        except Exception as e:
            QMessageBox.warning(self, "Ошибка парсинга файла", str(e))
            self.refine_button.setEnabled(False)
            self.merge_button.setEnabled(False)
            self.select_all_button.setEnabled(False)
            self.unselect_all_button.setEnabled(False)

    def refine_mesh(self):
        """
        Преобразует выбранные сетки на основе значения Csw.
        """
        try:
            Csw = float(self.csw_entry.text())
            selected_indices = [self.refine_list_widget.row(item) for item in self.refine_list_widget.selectedItems()]
            
            if not selected_indices:
                QMessageBox.warning(self, "Ошибка выбора", "Выберите хотя бы одну расчётную область из списка.")
                return
                
            if not self.fds_file_path:
                QMessageBox.warning(self, "Ошибка", "Файл FDS не загружен.")
                return
                
            modified_contents = refine_fds_meshes(self.fds_lines, self.meshes, selected_indices, Csw)
            
            if modified_contents is not None:
                write_fds_file(self.fds_file_path, modified_contents)
                QMessageBox.information(self, "Успех!", "Расчётные области преобразованы и сохранены.")
                # Перезагрузить файл, передавая текущие lines
                self.parse_file_refine(self.fds_file_path, modified_contents)
        except ValueError:
            QMessageBox.warning(self, "Ошибка ввода", "Значение Csw должно быть рациональным положительным.")
        except Exception as e:
            QMessageBox.critical(self, "Критическая ошибка", f"Произошла непредвиденная ошибка: {e}")

    def merge_meshes(self):
        """
        Объединяет все MESH области в FDS файле в одну большую область.
        """
        try:
            Csw = None
            if self.csw_entry.text():
                try:
                    Csw = float(self.csw_entry.text())
                except ValueError:
                    pass  # Если Csw не задан или некорректен, будет вычислен автоматически
            
            if not self.fds_file_path:
                QMessageBox.warning(self, "Ошибка", "Файл FDS не загружен.")
                return
                
            modified_contents = merge_fds_meshes(self.fds_lines, Csw)
            
            if modified_contents is not None:
                write_fds_file(self.fds_file_path, modified_contents)
                QMessageBox.information(self, "Успех!", "MESH и VENT объединены!")
                # Перезагрузить файл, передавая текущие lines
                self.parse_file_refine(self.fds_file_path, modified_contents)
        except Exception as e:
            QMessageBox.critical(self, "Критическая ошибка", f"Произошла непредвиденная ошибка: {e}")

    def select_all_refine(self):
        """
        Выбирает все элементы в списке.
        """
        self.refine_list_widget.selectAll()

    def unselect_all_refine(self):
        """
        Снимает выбор со всех элементов в списке.
        """
        self.refine_list_widget.clearSelection()

def write_fds_file(file_path: str, contents: list):
    """
    Записывает содержимое в указанный FDS-файл, создавая необходимые директории.
    
    :param file_path: Путь к файлу.
    :param contents: Список строк для записи.
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(contents)
    except Exception as e:
        QMessageBox.critical(None, "Ошибка записи файла", f"Не удалось записать файл: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = FDSMeshToolsApp(ProcessID)
    main_window.show()
    sys.exit(app.exec())