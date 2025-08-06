import os
import re
import configparser
from math import sqrt, pi

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel,
                             QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
                             QMessageBox, QGroupBox, QStatusBar, QSizePolicy)
from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtCore import Qt, QTimer

def setup_app_palette(app_instance: QMainWindow):
    """Установка цветовой палитры для приложения."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(248, 250, 252))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(30, 41, 59))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(241, 245, 249))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(30, 41, 59))
    palette.setColor(QPalette.ColorRole.Text, QColor(30, 41, 59))
    palette.setColor(QPalette.ColorRole.Button, QColor(186, 230, 253))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(3, 105, 161))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(125, 211, 252))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(30, 41, 59))
    app_instance.setPalette(palette)

def get_input_style_common():
    """Возвращает общий стиль для полей ввода."""
    return """
        QLineEdit {
            padding: 12px;
            border: 1px solid #cbd5e1;
            border-radius: 5px;
            background-color: white;
            font-size: 14px;
        }
        QLineEdit:focus {
            border: 2px solid #7dd3fc;
        }
    """

def get_input_style_fds5():
    """Возвращает стиль для полей ввода в FDS5."""
    return """
        QLineEdit {
            padding: 12px;
            border: 2px solid #cbd5e1;
            border-radius: 5px;
            background-color: white;
        }
        QLineEdit:focus {
            border: 2px solid #7dd3fc;
        }
        QLineEdit:read-only {
            background-color: #f1f5f9;
            border: 2px solid #cbd5e1;
        }
    """

def get_button_style_common():
    """Возвращает общий стиль для кнопок."""
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

def get_button_style_fds5(): 
    """Возвращает стиль для кнопок в FDS5."""
    return """
        QPushButton {
            background-color: #bae6fd;
            color: #0369a1;
            border: none;
            border-radius: 8px;
            padding: 20px 25px;
            font-size: 15px;
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

def get_group_box_style():
    """Возвращает стиль для QGroupBox."""
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

def get_label_style():
    """Возвращает стиль для QLabel."""
    return """
        QLabel {
            font-size: 14px;
            font-weight: 500;
            color: #607d8b; /* BLUE_GREY_700 */
        }
    """

def create_input_field_common(app_instance, label_text, hint_text, tooltip_text, read_only=False, prefix=""):
    """Вспомогательный метод для создания QLineEdit с меткой для common."""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(5)
    layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

    # Create prefix label with fixed width for consistent alignment
    if prefix:
        prefix_label = QLabel(prefix)
        prefix_label.setStyleSheet(get_label_style())
        prefix_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        # Removed fixed width for prefix to allow natural sizing
        layout.addWidget(prefix_label)

    # Create main label
    label = QLabel(label_text)
    label.setStyleSheet(get_label_style())
    label.setFont(QFont("Arial", 14))
    label.setFixedWidth(40)  # Fixed width for main label text to ensure alignment
    layout.addWidget(label)

    line_edit = QLineEdit()
    line_edit.setPlaceholderText(hint_text)
    line_edit.setToolTip(tooltip_text)
    line_edit.setReadOnly(read_only)
    line_edit.setStyleSheet(get_input_style_common())
    # Removed fixed width, allow line edit to expand
    line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    # Apply input validation and math operations only to editable fields
    if not read_only:
        # Connect to textChanged signal for input validation
        line_edit.textChanged.connect(lambda text: validate_and_calculate(line_edit, text))
    layout.addWidget(line_edit)

    # Removed addStretch to prevent empty space on the right

    return container, line_edit # Return both the container and the QLineEdit for access

def create_input_field_fds5(app_instance, label_text, hint_text, tooltip_text, read_only=False, prefix=""):
    """Вспомогательный метод для создания QLineEdit с меткой для FDS5."""
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(5)

    label = QLabel(prefix + label_text)
    label.setFont(QFont("Segoe UI", 24))
    layout.addWidget(label)

    line_edit = QLineEdit()
    line_edit.setPlaceholderText(hint_text)
    line_edit.setToolTip(tooltip_text)
    line_edit.setReadOnly(read_only)
    line_edit.setStyleSheet(get_input_style_fds5())
    layout.addWidget(line_edit)
    return container # Return the container widget containing the label and line edit

def load_from_ini_common(app_instance, k_entry, fpom_entry, psyd_entry, v_entry, m_entry):
    """Загрузка значений из INI файла для common."""
    current_directory = os.path.dirname(__file__)
    parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
    inis_path = os.path.join(parent_directory, 'inis') 
    ini_file = os.path.join(inis_path, 'IniApendix1.ini')

    if os.path.exists(ini_file):
        config = configparser.ConfigParser()
        config.read(ini_file)
        try:
            k_entry[1].setText(config['Calculations']['k'])
            fpom_entry[1].setText(config['Calculations']['Fpom'])
            v_entry[1].setText(config['Calculations']['v'])
            psyd_entry[1].setText(config['Calculations']['psi_ud'])
            m_entry[1].setText("0.0")
        except KeyError as e:
            QMessageBox.warning(app_instance, "Ошибка загрузки INI", f"Значения не найдены в INI файле: {e}")

def load_from_ini_fds5(app_instance, k_entry, fpom_entry, psyd_entry, v_entry, m_entry):
    """Загрузка значений из INI файла для FDS5."""
    current_directory = os.path.dirname(__file__)
    parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
    inis_path = os.path.join(parent_directory, 'inis')
    ini_file = os.path.join(inis_path, 'IniApendix1.ini')

    if os.path.exists(ini_file):
        config = configparser.ConfigParser()
        config.read(ini_file)
        try:
            # Accessing QLineEdit directly from the container
            k_entry.findChild(QLineEdit).setText(config['Calculations']['k'])
            fpom_entry.findChild(QLineEdit).setText(config['Calculations']['Fpom'])
            v_entry.findChild(QLineEdit).setText(config['Calculations']['v'])
            psyd_entry.findChild(QLineEdit).setText(config['Calculations']['psi_ud'])
            m_entry.findChild(QLineEdit).setText("0.0")  # Default value
        except KeyError as e:
            QMessageBox.warning(app_instance, "Ошибка загрузки INI", f"Значения не найдены: {e}")
        except Exception as e:
            QMessageBox.critical(app_instance, "Ошибка", f"Произошла непредвиденная ошибка при загрузке INI: {e}")
def calculate_common(app_instance, k_entry, fpom_entry, psyd_entry, v_entry, m_entry, tmax_entry, psy_entry, hrr_entry, stt_entry, bigM_entry, process_button, status_bar, process_id, read_ini_file_hoc_func):
    """Выполнение вычислений для common."""
    current_directory = os.path.dirname(__file__)
    parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
    inis_path = os.path.join(parent_directory, 'inis')
    ini_path_hoc = os.path.join(inis_path, f'HOC_{process_id}.ini') if process_id is not None else os.path.join(inis_path, 'HOC.ini')
    try:
        k = safe_eval(k_entry[1].text())
        Fpom = safe_eval(fpom_entry[1].text())
        v = safe_eval(v_entry[1].text())
        psi_ud = safe_eval(psyd_entry[1].text())
        m = safe_eval(m_entry[1].text())

        tmax = sqrt((k * Fpom) / (pi * v**2))
        Psi = psi_ud * pi * v**2 * tmax**2
        Stt = pi * (v * tmax)**2
        HEAT_OF_COMBUSTION = float(read_ini_file_hoc_func(ini_path_hoc))
        Hc = HEAT_OF_COMBUSTION / 1000

        if m > 0:
            bigM = Psi * tmax
            Psi = m / tmax
            bigM = m
            HRRPUA = Hc * Psi * 0.93 * 1000
        else:
            bigM = Psi * tmax
            HRRPUA = Hc * Psi * 0.93 * 1000
        tmax_entry[1].setText(f"{tmax:.4f}")
        psy_entry[1].setText(f"{Psi:.4f}")
        hrr_entry[1].setText(f"{HRRPUA:.4f}")
        stt_entry[1].setText(f"{Stt:.4f}")
        bigM_entry[1].setText(f"{bigM:.4f}")

        stt_entry[1].setToolTip(f"Площадь поверхности горючей нагрузки в помещении, охватываемая пожаром за время tmax = {tmax:.4f} м²")
        process_button.setEnabled(True)

    except ValueError as ve:
        QMessageBox.warning(app_instance, "Ошибка ввода", f"Ошибка ввода: {ve}")
    except Exception as ex:
        QMessageBox.critical(app_instance, "Ошибка", f"Произошла ошибка: {ex}")

def calculate_fds5(app_instance, k_entry, fpom_entry, psyd_entry, v_entry, m_entry, tmax_entry, psy_entry, hrr_entry, stt_entry, bigM_entry, process_button, status_bar, process_id, read_ini_file_hoc_func):
    """Выполнение вычислений для FDS5."""
    current_directory = os.path.dirname(__file__) 
    parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
    inis_path = os.path.join(parent_directory, 'inis')

    ini_path_hoc = os.path.join(inis_path, f'HOC_{process_id}.ini') if process_id is not None else os.path.join(inis_path, 'HOC.ini')
    try:
        k = safe_eval(k_entry.findChild(QLineEdit).text())
        Fpom = safe_eval(fpom_entry.findChild(QLineEdit).text())
        v = safe_eval(v_entry.findChild(QLineEdit).text())
        psi_ud = safe_eval(psyd_entry.findChild(QLineEdit).text())
        m = safe_eval(m_entry.findChild(QLineEdit).text())

        tmax = sqrt((k * Fpom) / (pi * v**2))
        Psi = psi_ud * pi * v**2 * tmax**2
        Stt = pi * (v * tmax)**2
        HEAT_OF_COMBUSTION = float(read_ini_file_hoc_func(ini_path_hoc))
        Hc = HEAT_OF_COMBUSTION / 1000

        if m > 0:
            bigM = Psi * tmax
            Psi = m / tmax
            bigM = m
            HRRPUA = Hc * Psi * 0.93 * 1000
        else:
            bigM = Psi * tmax
            Psi = 0.45 * (1 / k) * (bigM / tmax)
            HRRPUA = Hc * Psi * 0.93 * 1000

        tmax_entry.findChild(QLineEdit).setText(f"{tmax:.4f}")
        psy_entry.findChild(QLineEdit).setText(f"{Psi:.4f}")
        hrr_entry.findChild(QLineEdit).setText(f"{HRRPUA:.4f}")
        stt_entry.findChild(QLineEdit).setText(f"{Stt:.4f}")
        bigM_entry.findChild(QLineEdit).setText(f"{bigM:.4f}")

        stt_entry.findChild(QLineEdit).setToolTip(f"Площадь поверхности горючей нагрузки в помещении, охватываемая пожаром за время tₘₐₓ = {tmax:.4f} м²")

        process_button.setEnabled(True)
        status_bar.showMessage("Вычисления выполнены успешно.")

    except ValueError as ve:
        QMessageBox.warning(app_instance, "Ошибка ввода", f"Ошибка ввода: {ve}")
        status_bar.showMessage("Ошибка ввода: Проверьте введенные значения.")
    except Exception as ex:
        QMessageBox.critical(app_instance, "Ошибка", f"Произошла ошибка: {ex}")
        status_bar.showMessage("Произошла критическая ошибка.")

def save_to_ini_common(k, Fpom, v, psi_ud, m, tmax, Psi, Stt, bigM, HRRPUA):
    """Сохранение значений в INI файл для common."""
    config = configparser.ConfigParser()
    config['Calculations'] = {
        'k': k,
        'Fpom': Fpom,
        'v': v,
        'psi_ud': psi_ud,
        'm': m,
        'tmax': tmax,
        'Psi': Psi,
        'Stt': Stt,
        'bigM': bigM,
        'HRRPUA': HRRPUA,
    }

    current_directory = os.path.dirname(__file__)
    parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
    inis_path = os.path.join(parent_directory, 'inis')
    ini_file = os.path.join(inis_path, 'IniApendix1.ini')

    os.makedirs(inis_path, exist_ok=True)
    with open(ini_file, 'w') as configfile:
        config.write(configfile)

def read_ini_file_path(ini_file):
    """Чтение пути к файлу из INI."""
    config = configparser.ConfigParser()
    with open(ini_file, 'r', encoding='utf-16') as f:
        config.read_file(f)
    return config['filePath']['filePath']

def read_ini_file_hoc(ini_file):
    """Чтение значения HEAT_OF_COMBUSTION из INI."""
    config = configparser.ConfigParser()
    with open(ini_file, 'r', encoding='utf-16') as f:
        config.read_file(f)
    return config['HEAT_OF_COMBUSTION']['HEAT_OF_COMBUSTION']

def process_fds_file_common(app_instance, k_entry, fpom_entry, psyd_entry, v_entry, m_entry, tmax_entry, psy_entry, hrr_entry, stt_entry, bigM_entry, process_button, process_id, read_ini_file_path_func, read_ini_file_hoc_func):
    """Обработка FDS файла для common."""
    k = k_entry[1].text()
    Fpom = fpom_entry[1].text()
    v_val_str = v_entry[1].text()
    psi_ud = psyd_entry[1].text()
    m_val_str = m_entry[1].text()
    tmax = tmax_entry[1].text()
    Psi_str = psy_entry[1].text()
    Stt = stt_entry[1].text()
    bigM = bigM_entry[1].text()
    HRRPUA = hrr_entry[1].text()

    save_to_ini_common(k, Fpom, v_val_str, psi_ud, m_val_str, tmax, Psi_str, Stt, bigM, HRRPUA)
    current_directory = os.path.dirname(__file__) 
    parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
    inis_path = os.path.join(parent_directory, 'inis')

    ini_path = os.path.join(inis_path, f'filePath_{process_id}.ini')
    ini_path_hoc = os.path.join(inis_path, f'HOC_{process_id}.ini') if process_id is not None else os.path.join(inis_path, 'HOC.ini')

    try:
        HEAT_OF_COMBUSTION = float(read_ini_file_hoc_func(ini_path_hoc))
        Hc = HEAT_OF_COMBUSTION / 1000
        v_val = float(v_val_str)
        m_val = float(m_val_str)
        TAU_Q = -float(tmax)

        fds_path = read_ini_file_path_func(ini_path)

        if m_val > 0:
            MLRPUA = m_val / -TAU_Q
        else:
            MLRPUA = float(Psi_str)
        HRRPUA_val = Hc * MLRPUA * 0.93 * 1000
        if not MLRPUA or not TAU_Q:
            raise ValueError("Поля не должны быть пустыми")

        modified_lines = []
        inside_surf_block = False
        vent_seen = False
        surf_id = None
        hrrpua_found = False
        remove_ctrl_ramp = False
        with open(fds_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            for line in lines:
                if line.strip().startswith('&SURF'):
                    match = re.search(r"ID='([^']*)'", line)
                    if match:
                        surf_id = match.group(1)

                    inside_surf_block = True
                    vent_seen = False
                    if 'HRRPUA' in line:
                        hrrpua_found = True
                        modified_lines.append(f"&SURF ID='{surf_id}', ")
                        modified_lines.append(f"HRRPUA={HRRPUA_val}, ")
                        modified_lines.append(f"COLOR='RED', ")
                        modified_lines.append(f"TAU_Q={TAU_Q}/\n")
                    else:
                        hrrpua_found = False
                        modified_lines.append(line)
                    continue

                if inside_surf_block and hrrpua_found:
                    if line.strip().startswith('&VENT'):
                        line = re.sub(r"CTRL_ID='[^']*'\s*", '', line)
                        if 'SPREAD_RATE' in line:
                            line = re.sub(r"SPREAD_RATE=[^\s]*\s*", '', line)
                        modified_lines.append(line)
                        vent_seen = True
                        continue

                    if '(end)' in line:
                        inside_surf_block = False
                        modified_lines.append(line)
                        continue

                    continue

                if line.strip().startswith('&OBST'):
                    if 'CTRL_ID' in line:
                        line = re.sub(r"CTRL_ID='[^']*'\s*", '', line)
                        remove_ctrl_ramp = True

                    modified_lines.append(line)
                    continue

                if remove_ctrl_ramp and (line.strip().startswith('&CTRL') or line.strip().startswith('&RAMP')):
                    continue
                else:
                    remove_ctrl_ramp = False

                modified_lines.append(line)

        output_dir = os.path.dirname(fds_path)
        os.makedirs(output_dir, exist_ok=True)
        with open(fds_path, 'w', encoding='utf-8') as file:
            file.writelines(modified_lines)
        QMessageBox.information(app_instance, "Успех", f"Модифицированный .fds файл сохранён:\n\n{fds_path}")
        QTimer.singleShot(1000, app_instance.close)

    except Exception as e:
        QMessageBox.critical(app_instance, "Ошибка", str(e))

def process_fds_file_fds5(app_instance, k_entry, fpom_entry, psyd_entry, v_entry, m_entry, tmax_entry, psy_entry, hrr_entry, stt_entry, bigM_entry, process_button, process_id, read_ini_file_path_func, read_ini_file_hoc_func, status_bar):
    """Обработка FDS файла для FDS5."""
    k = k_entry.findChild(QLineEdit).text()
    Fpom = fpom_entry.findChild(QLineEdit).text()
    v_val_str = v_entry.findChild(QLineEdit).text()
    psi_ud = psyd_entry.findChild(QLineEdit).text() 
    m_val_str = m_entry.findChild(QLineEdit).text()
    tmax = tmax_entry.findChild(QLineEdit).text()
    Psi_str = psy_entry.findChild(QLineEdit).text()
    Stt = stt_entry.findChild(QLineEdit).text()
    bigM = bigM_entry.findChild(QLineEdit).text()
    HRRPUA = hrr_entry.findChild(QLineEdit).text()

    save_to_ini_common(k, Fpom, v_val_str, psi_ud, m_val_str, tmax, Psi_str, Stt, bigM, HRRPUA)
    current_directory = os.path.dirname(__file__)
    parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
    inis_path = os.path.join(parent_directory, 'inis')

    ini_path = os.path.join(inis_path, f'filePath_{process_id}.ini')
    ini_path_hoc = os.path.join(inis_path, f'HOC_{process_id}.ini') if process_id is not None else os.path.join(inis_path, 'HOC.ini')

    try:
        HEAT_OF_COMBUSTION = float(read_ini_file_hoc_func(ini_path_hoc))
        Hc = HEAT_OF_COMBUSTION / 1000
        v_val = float(v_val_str)
        m_val = float(m_val_str)
        TAU_Q = -float(tmax)
        fds_path = read_ini_file_path_func(ini_path)

        if m_val > 0:
            MLRPUA = m_val / -TAU_Q
        else:
            MLRPUA = float(Psi_str)
        HRRPUA_val = Hc * MLRPUA * 0.93 * 1000
        if not MLRPUA or not TAU_Q:
            raise ValueError("Поля не должны быть пустыми")
        modified_lines = []
        inside_surf_block = False
        vent_seen = False
        surf_id = None
        hrrpua_found = False
        remove_ctrl_ramp = False
        with open(fds_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            for line in lines:
                if line.strip().startswith('&SURF'):
                    match = re.search(r"ID='([^']*)'", line)
                    if match:
                        surf_id = match.group(1)

                    inside_surf_block = True
                    vent_seen = False

                    if 'HRRPUA' in line:
                        hrrpua_found = True
                        modified_lines.append(f"&SURF ID='{surf_id}', ")
                        modified_lines.append(f"HRRPUA={HRRPUA_val}, ")
                        modified_lines.append(f"COLOR='RED', ")
                        modified_lines.append(f"TAU_Q={TAU_Q}/\n")
                    else:
                        hrrpua_found = False
                        modified_lines.append(line)
                    continue

                if inside_surf_block and hrrpua_found:
                    if line.strip().startswith('&VENT'):
                        line = re.sub(r"CTRL_ID='[^']*'\s*", '', line)
                        if 'SPREAD_RATE' in line:
                            line = re.sub(r"SPREAD_RATE=[^\s]*\s*", '', line)
                        modified_lines.append(line)
                        vent_seen = True
                        continue

                    if '(end)' in line:
                        inside_surf_block = False
                        modified_lines.append(line)
                        continue

                    continue

                if line.strip().startswith('&OBST'):
                    if 'CTRL_ID' in line:
                        line = re.sub(r"CTRL_ID='[^']*'\s*", '', line)
                        remove_ctrl_ramp = True

                    modified_lines.append(line)
                    continue

                if remove_ctrl_ramp and (line.strip().startswith('&CTRL') or line.strip().startswith('&RAMP')):
                    continue
                else:
                    remove_ctrl_ramp = False

                modified_lines.append(line)

        output_dir = os.path.dirname(fds_path)
        os.makedirs(output_dir, exist_ok=True)
        with open(fds_path, 'w', encoding='utf-8') as file:
            file.writelines(modified_lines)
        QMessageBox.information(app_instance, "Успех", f"Модифицированный .fds файл сохранён:\n\n{fds_path}")
        status_bar.showMessage("Файл успешно сохранен.")
        QTimer.singleShot(1000, app_instance.close)
    except Exception as e: 
        QMessageBox.critical(app_instance, "Ошибка", str(e))
        status_bar.showMessage(f"Ошибка при обработке файлов: {e}")

def validate_and_calculate(line_edit, text):
    """
    Validates input to allow only numbers, decimal points, and basic math operators (+, -, *, /).
    Does not evaluate the expression immediately. Evaluation happens on 'Calculate' button click.
    """
    # Remove invalid characters (letters, commas, spaces)
    # Allow digits, decimal point, and basic math operators
    valid_text = re.sub(r"[^\d+\-*/.]", "", text)
    # Update the line edit with the validated text only if it has changed
    # This prevents cursor reset issues when the text is already valid
    if text != valid_text:
        line_edit.setText(valid_text)


def safe_eval(expression: str) -> float:
    """
    Safely evaluates a mathematical expression string.
    Returns the evaluated float result or raises ValueError/ZeroDivisionError.
    """
    if not expression:
        return 0.0
    try:
        # Базовая проверка: убеждаемся, что выражение содержит только разрешенные символы.
        # This is a second layer of protection, though validate_and_calculate should have done this
        if not re.match(r"^[\d+\-*/.() ]+$", expression):
            raise ValueError("Invalid characters in expression")
        # Evaluate the expression
        # Note: eval() can be dangerous with untrusted input.
        # For a more secure approach, consider using a proper expression parser library.
        result = eval(expression)
        # Ensure the result is a number (int or float)
        if not isinstance(result, (int, float)):
            raise ValueError("Expression did not evaluate to a number")
        return float(result)
    except ZeroDivisionError:
        raise ZeroDivisionError("Division by zero in expression")
    except Exception as e:
        raise ValueError(f"Invalid expression: {e}")

def get_icon_path(main_file_path, icon_filename):
    """
    Get the path to an icon file in the .gitpics directory.
    
    Args:
        main_file_path (str): Path to the main Python file (__file__)
        icon_filename (str): Name of the icon file
    Returns:
        str: Full path to the icon file
    """
    # Get the directory containing the main Python file (e.g., p_libs)
    main_dir = os.path.dirname(os.path.abspath(main_file_path))
    # Get the parent directory of p_libs (where .gitpics should be)
    parent_of_main_dir = os.path.dirname(main_dir)
    # Construct path to .gitpics directory
    gitpics_dir = os.path.join(parent_of_main_dir, '.gitpics')
    # Return path to icon file
    return os.path.join(gitpics_dir, icon_filename)