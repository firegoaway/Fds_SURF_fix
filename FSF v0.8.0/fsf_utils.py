import os
import re
import configparser
import json
import logging
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
            padding: 6px 15px;
            font-weight: bold;
            min-width: 110px;
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
            padding: 6px 25px;
            font-size: 15px;
            font-weight: bold;
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

def load_from_ini_common(app_instance, k_entry, fpom_entry, psyd_entry, v_entry, m_entry, t_entry):
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
            t_entry[1].setText("0.0")
        except KeyError as e:
            QMessageBox.warning(app_instance, "Ошибка загрузки INI", f"Значения не найдены в INI файле: {e}")

def load_from_ini_fds5(app_instance, k_entry, fpom_entry, psyd_entry, v_entry, m_entry, t_entry):
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
            t_entry.findChild(QLineEdit).setText("0.0")  # Default value
        except KeyError as e:
            QMessageBox.warning(app_instance, "Ошибка загрузки INI", f"Значения не найдены: {e}")
        except Exception as e:
            QMessageBox.critical(app_instance, "Ошибка", f"Произошла непредвиденная ошибка при загрузке INI: {e}")
            
def calculate_common(app_instance, k_entry, fpom_entry, psyd_entry, v_entry, m_entry, t_entry, tmax_entry, psy_entry, hrr_entry, stt_entry, bigM_entry, process_button, status_bar, process_id, read_ini_file_hoc_func):
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
        t = safe_eval(t_entry[1].text())

        tmax = sqrt((k * Fpom) / (pi * v**2))
        # Если t задано и не равно 0, используем его как tmax
        if t != 0:
            tmax = t
        Psi = psi_ud * pi * v**2 * tmax**2
        Stt = pi * (v * tmax)**2
        HEAT_OF_COMBUSTION = float(read_ini_file_hoc_func(ini_path_hoc))
        Hc = HEAT_OF_COMBUSTION / 1000
        eta = 0.93

        if m > 0:
            bigM = Psi * tmax
            Psi = m / tmax
            bigM = m
            HRRPUA = Hc * Psi * eta * 1000
        else:
            bigM = Psi * tmax
            HRRPUA = Hc * Psi * eta * 1000
        tmax_entry[1].setText(f"{tmax:.4f}")
        psy_entry[1].setText(f"{Psi:.4f}")
        hrr_entry[1].setText(f"{HRRPUA:.4f}")
        stt_entry[1].setText(f"{Stt:.4f}")
        bigM_entry[1].setText(f"{bigM:.4f}")

        stt_entry[1].setToolTip(f"Площадь поверхности горючей нагрузки в помещении, охватываемая пожаром за время tmax = {tmax:.4f} м²")
        process_button.setEnabled(True)
        status_bar.showMessage("Вычисления выполнены успешно.")

    except ValueError as ve:
        QMessageBox.warning(app_instance, "Ошибка ввода", f"Ошибка ввода: {ve}")
        status_bar.showMessage("Ошибка ввода: Проверьте введенные значения.")
    except Exception as ex:
        QMessageBox.critical(app_instance, "Ошибка", f"Произошла ошибка: {ex}")
        status_bar.showMessage("Произошла критическая ошибка.")

def calculate_fds5(app_instance, k_entry, fpom_entry, psyd_entry, v_entry, m_entry, t_entry, tmax_entry, psy_entry, hrr_entry, stt_entry, bigM_entry, process_button, status_bar, process_id, read_ini_file_hoc_func):
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
        t = safe_eval(t_entry.findChild(QLineEdit).text())

        tmax = sqrt((k * Fpom) / (pi * v**2))
        # Если t задано и не равно 0, используем его как tmax
        if t != 0:
            tmax = t
        Psi = psi_ud * pi * v**2 * tmax**2
        Stt = pi * (v * tmax)**2
        HEAT_OF_COMBUSTION = float(read_ini_file_hoc_func(ini_path_hoc))
        Hc = HEAT_OF_COMBUSTION / 1000
        eta = 0.93

        if m > 0:
            bigM = Psi * tmax
            Psi = m / tmax
            bigM = m
            HRRPUA = Hc * Psi * eta * 1000
        else:
            bigM = Psi * tmax
            Psi = 0.45 * (1 / k) * (bigM / tmax)
            HRRPUA = Hc * Psi * eta * 1000

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

def save_to_ini_common(k, Fpom, v, psi_ud, m, t, tmax, Psi, Stt, bigM, HRRPUA):
    """Сохранение значений в INI файл для common."""
    config = configparser.ConfigParser()
    config['Calculations'] = {
        'k': k,
        'Fpom': Fpom,
        'v': v,
        'psi_ud': psi_ud,
        'm': m,
        't': t,
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

def process_fds_file_common(app_instance, k_entry, fpom_entry, psyd_entry, v_entry, m_entry, t_entry, tmax_entry, psy_entry, hrr_entry, stt_entry, bigM_entry, process_button, process_id, read_ini_file_path_func, read_ini_file_hoc_func, status_bar):
    """Обработка FDS файла для common."""
    k = k_entry[1].text()
    Fpom = fpom_entry[1].text()
    v_val_str = v_entry[1].text()
    psi_ud = psyd_entry[1].text()
    m_val_str = m_entry[1].text()
    t_val_str = t_entry[1].text()
    tmax = tmax_entry[1].text()
    Psi_str = psy_entry[1].text()
    Stt = stt_entry[1].text()
    bigM = bigM_entry[1].text()
    HRRPUA = hrr_entry[1].text()

    save_to_ini_common(k, Fpom, v_val_str, psi_ud, m_val_str, t_val_str, tmax, Psi_str, Stt, bigM, HRRPUA)
    current_directory = os.path.dirname(__file__)
    parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
    inis_path = os.path.join(parent_directory, 'inis')

    ini_path = os.path.join(inis_path, f'filePath_{process_id}.ini')
    ini_path_hoc = os.path.join(inis_path, f'HOC_{process_id}.ini') if process_id is not None else os.path.join(inis_path, 'HOC.ini')

    try:
        HEAT_OF_COMBUSTION = float(read_ini_file_hoc_func(ini_path_hoc))
        Hc = HEAT_OF_COMBUSTION / 1000
        v_val = safe_convert_to_float(v_val_str)
        m_val = safe_convert_to_float(m_val_str)
        t_val = safe_convert_to_float(t_val_str)
        # Если t задано и не равно 0, используем его как TAU_Q, иначе рассчитанный tmax
        TAU_Q = -t_val if t_val != 0 else -safe_convert_to_float(tmax)
        eta = 0.93

        fds_path = read_ini_file_path_func(ini_path)

        if m_val > 0:
            MLRPUA = m_val / -TAU_Q
        else:
            MLRPUA = safe_convert_to_float(Psi_str)
        HRRPUA_val = Hc * MLRPUA * eta * 1000
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
        create_check_ini_file(process_id, "Done")
        QTimer.singleShot(1000, app_instance.close)

    except Exception as e:
        QMessageBox.critical(app_instance, "Ошибка", str(e))
        status_bar.showMessage(f"Ошибка при обработке файлов: {e}")
        create_check_ini_file(process_id, "None")

def process_fds_file_fds5(app_instance, k_entry, fpom_entry, psyd_entry, v_entry, m_entry, t_entry, tmax_entry, psy_entry, hrr_entry, stt_entry, bigM_entry, process_button, process_id, read_ini_file_path_func, read_ini_file_hoc_func, status_bar):
    """Обработка FDS файла для FDS5."""
    k = k_entry.findChild(QLineEdit).text()
    Fpom = fpom_entry.findChild(QLineEdit).text()
    v_val_str = v_entry.findChild(QLineEdit).text()
    psi_ud = psyd_entry.findChild(QLineEdit).text()
    m_val_str = m_entry.findChild(QLineEdit).text()
    t_val_str = t_entry.findChild(QLineEdit).text()
    tmax = tmax_entry.findChild(QLineEdit).text()
    Psi_str = psy_entry.findChild(QLineEdit).text()
    Stt = stt_entry.findChild(QLineEdit).text()
    bigM = bigM_entry.findChild(QLineEdit).text()
    HRRPUA = hrr_entry.findChild(QLineEdit).text()

    save_to_ini_common(k, Fpom, v_val_str, psi_ud, m_val_str, t_val_str, tmax, Psi_str, Stt, bigM, HRRPUA)
    current_directory = os.path.dirname(__file__)
    parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
    inis_path = os.path.join(parent_directory, 'inis')

    ini_path = os.path.join(inis_path, f'filePath_{process_id}.ini')
    ini_path_hoc = os.path.join(inis_path, f'HOC_{process_id}.ini') if process_id is not None else os.path.join(inis_path, 'HOC.ini')

    try:
        HEAT_OF_COMBUSTION = float(read_ini_file_hoc_func(ini_path_hoc))
        Hc = HEAT_OF_COMBUSTION / 1000
        v_val = safe_convert_to_float(v_val_str)
        m_val = safe_convert_to_float(m_val_str)
        t_val = safe_convert_to_float(t_val_str)
        # Если t задано и не равно 0, используем его как TAU_Q, иначе рассчитанный tmax
        TAU_Q = -t_val if t_val != 0 else -safe_convert_to_float(tmax)
        eta = 0.93

        fds_path = read_ini_file_path_func(ini_path)

        if m_val > 0:
            MLRPUA = m_val / -TAU_Q
        else:
            MLRPUA = safe_convert_to_float(Psi_str)
        HRRPUA_val = Hc * MLRPUA * eta * 1000
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
        create_check_ini_file(process_id, "Done")
        QTimer.singleShot(1000, app_instance.close)
    except Exception as e: 
        QMessageBox.critical(app_instance, "Ошибка", str(e))
        status_bar.showMessage(f"Ошибка при обработке файлов: {e}")
        create_check_ini_file(process_id, "None")

def validate_and_calculate(line_edit, text):
    """
    Проверяет ввод, разрешая цифры, десятичные точки, основные математические операторы (+, -, *, /), 
    возведение в степень (^) и скобки ().
    Не вычисляет выражение немедленно. Вычисление происходит при нажатии кнопки 'Рассчитать'.
    """
    # Remove invalid characters (letters, commas, spaces)
    # Allow digits, decimal point, basic math operators, exponentiation, and parentheses
    valid_text = re.sub(r"[^\d+\-*/.^()]", "", text)
    # Update the line edit with the validated text only if it has changed
    # This prevents cursor reset issues when the text is already valid
    if text != valid_text:
        line_edit.setText(valid_text)


def safe_eval(expression: str) -> float:
    """
    Безопасно вычисляет строку математического выражения с поддержкой:
    - Основных операторов: +, -, *, /
    - Возведения в степень: ^ (правоассоциативное)
    - Скобок: () для группировки
    - Правильного порядка операций: Скобки, Степени, Умножение/Деление, Сложение/Вычитание
    
    Возвращает вычисленный результат с плавающей точкой или вызывает ValueError/ZeroDivisionError.
    """
    if not expression:
        return 0.0
    
    # Remove whitespace
    expression = expression.replace(' ', '')
    
    if not expression:
        return 0.0
    
    try:
        # Tokenize the expression
        tokens = _tokenize(expression)
        # Parse and evaluate the expression
        result, _ = _parse_expression(tokens, 0)
        return float(result)
    except ZeroDivisionError:
        raise ZeroDivisionError("Division by zero in expression")
    except Exception as e:
        raise ValueError(f"Invalid expression: {e}")

def _tokenize(expression: str) -> list:
    """Преобразует строку выражения в список токенов."""
    tokens = []
    i = 0
    while i < len(expression):
        char = expression[i]
        if char.isdigit() or char == '.':
            # Parse number (including decimals)
            num_str = ''
            while i < len(expression) and (expression[i].isdigit() or expression[i] == '.'):
                num_str += expression[i]
                i += 1
            tokens.append(float(num_str))
            continue
        elif char in '+-*/^()':
            # Handle negative numbers: if +/- is at start or after another operator/parenthesis
            if char in '+-' and (i == 0 or expression[i-1] in '+-*/^('):
                # Check if it's followed by a digit or decimal point
                j = i + 1
                while j < len(expression) and expression[j] == ' ':
                    j += 1
                if j < len(expression) and (expression[j].isdigit() or expression[j] == '.'):
                    # This is a unary operator, treat it as part of the number
                    num_str = char
                    i += 1
                    while i < len(expression) and (expression[i].isdigit() or expression[i] == '.'):
                        num_str += expression[i]
                        i += 1
                    tokens.append(float(num_str))
                    continue
            tokens.append(char)
        elif char == ' ':
            # Skip whitespace
            pass
        else:
            raise ValueError(f"Invalid character: {char}")
        i += 1
    return tokens

def _parse_expression(tokens: list, pos: int = 0) -> tuple:
    """Анализирует и вычисляет выражение с правильным порядком операций."""
    if not tokens:
        return 0.0, pos
    return _parse_addition_subtraction(tokens, pos)

def _parse_addition_subtraction(tokens: list, pos: int) -> tuple:
    """Анализирует сложение и вычитание (низкий приоритет)."""
    left, pos = _parse_multiplication_division(tokens, pos)
    
    while pos < len(tokens) and tokens[pos] in ['+', '-']:
        op = tokens[pos]
        pos += 1
        right, pos = _parse_multiplication_division(tokens, pos)
        if op == '+':
            left += right
        else:
            left -= right
    
    return left, pos

def _parse_multiplication_division(tokens: list, pos: int) -> tuple:
    """Анализирует умножение и деление."""
    left, pos = _parse_exponentiation(tokens, pos)
    
    while pos < len(tokens) and tokens[pos] in ['*', '/']:
        op = tokens[pos]
        pos += 1
        right, pos = _parse_exponentiation(tokens, pos)
        if op == '*':
            left *= right
        else:
            if right == 0:
                raise ZeroDivisionError("Division by zero")
            left /= right
    
    return left, pos

def _parse_exponentiation(tokens: list, pos: int) -> tuple:
    """Анализирует возведение в степень (^) с правоассоциативностью."""
    left, pos = _parse_unary(tokens, pos)
    
    if pos < len(tokens) and tokens[pos] == '^':
        pos += 1
        # Right-associative: parse the rest of the expression as the right operand
        right, pos = _parse_exponentiation(tokens, pos)
        left = left ** right
    
    return left, pos

def _parse_unary(tokens: list, pos: int) -> tuple:
    """Анализирует унарные операторы и скобки."""
    if pos >= len(tokens):
        raise ValueError("Unexpected end of expression")
    
    # Handle unary minus
    if tokens[pos] == '-':
        pos += 1
        value, pos = _parse_unary(tokens, pos)
        return -value, pos
    # Handle unary plus
    elif tokens[pos] == '+':
        pos += 1
        return _parse_unary(tokens, pos)
    else:
        return _parse_primary(tokens, pos)

def _parse_primary(tokens: list, pos: int) -> tuple:
    """Анализирует числа и скобки."""
    if pos >= len(tokens):
        raise ValueError("Unexpected end of expression")
    
    token = tokens[pos]
    
    # Handle numbers
    if isinstance(token, (int, float)):
        return float(token), pos + 1
    # Handle parentheses
    elif token == '(':
        pos += 1
        result, pos = _parse_expression(tokens, pos)
        if pos >= len(tokens) or tokens[pos] != ')':
            raise ValueError("Mismatched parentheses")
        return result, pos + 1  # Skip the closing parenthesis
    else:
        raise ValueError(f"Unexpected token: {token}")

def safe_convert_to_float(value: str) -> float:
    """
    Безопасно конвертирует строковое значение в число с плавающей точкой.
    Поддерживает как обычные числа, так и символьные выражения.
    
    Args:
        value (str): Строковое значение для конвертации
        
    Returns:
        float: Преобразованное значение
        
    Raises:
        ValueError: Если значение не может быть преобразовано
    """
    if not value or not isinstance(value, str):
        return 0.0
    
    # Удаляем пробелы
    value = value.strip()
    
    if not value:
        return 0.0
    
    try:
        # Пытаемся сначала преобразовать как обычное число
        return float(value)
    except ValueError:
        try:
            # Если не удалось, пытаемся вычислить как символьное выражение
            return safe_eval(value)
        except Exception as e:
            # Если и это не удалось, выбрасываем исключение
            raise ValueError(f"Could not convert '{value}' to float: {e}")

def get_icon_path(main_file_path, icon_filename):
    """
    Получает путь к файлу иконки в каталоге .gitpics.
    
    Аргументы:
        main_file_path (str): Путь к основному файлу Python (__file__)
        icon_filename (str): Имя файла иконки
    Возвращает:
        str: Полный путь к файлу иконки
    """
    # Получаем каталог, содержащий основной файл Python (например, p_libs)
    main_dir = os.path.dirname(os.path.abspath(main_file_path))
    # Получаем родительский каталог p_libs (где должен быть .gitpics)
    parent_of_main_dir = os.path.dirname(main_dir)
    # Формируем путь к каталогу .gitpics
    gitpics_dir = os.path.join(parent_of_main_dir, '.gitpics')
    # Возвращаем путь к файлу иконки
    return os.path.join(gitpics_dir, icon_filename)

def create_check_ini_file(process_id, state="None"):
    """
    Создание checkSURFFIX_{process_id}.ini файла с указанным состоянием.
    Также добавляет CheckSURFFIX=state в конец .fds файла и проверяет состояние в .fds.
    
    Args:
        process_id: ID процесса (может быть None)
        state: Состояние ("Done" или "None")
    """
    try:
        current_directory = os.path.dirname(__file__)
        parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
        inis_path = os.path.join(parent_directory, 'inis')
        os.makedirs(inis_path, exist_ok=True)
        
        # Получаем путь к .fds файлу
        ini_filename_path = f'filePath_{process_id}.ini' if process_id is not None else 'filePath.ini'
        ini_path_file = os.path.join(inis_path, ini_filename_path)
        
        if os.path.exists(ini_path_file):
            # Читаем путь к .fds файлу из INI файла
            config = configparser.ConfigParser()
            with open(ini_path_file, 'r', encoding='utf-16') as f:
                config.read_file(f)
            fds_path = config['filePath']['filePath']
            
            if os.path.exists(fds_path):
                # Читаем .fds файл для проверки существующего состояния CheckSURFFIX
                with open(fds_path, 'r', encoding='utf-8') as fds_file:
                    fds_content = fds_file.read()
                
                # Проверяем существующее состояние в .fds
                if 'CheckSURFFIX=Done' in fds_content:
                    state = "Done"
                elif 'CheckSURFFIX=None' in fds_content:
                    state = "None"
                # Если CheckSURFFIX не найден, оставляем переданное состояние
                
                # Добавляем CheckSURFFIX=state в конец .fds файла
                if 'CheckSURFFIX=' not in fds_content:
                    # Если нет строки CheckSURFFIX, добавляем её
                    with open(fds_path, 'a', encoding='utf-8') as fds_file:
                        fds_file.write(f'\nCheckSURFFIX={state}\n')
                else:
                    # Если строка CheckSURFFIX уже существует, обновляем её
                    updated_content = re.sub(r'CheckSURFFIX=(Done|None)', f'CheckSURFFIX={state}', fds_content)
                    with open(fds_path, 'w', encoding='utf-8') as fds_file:
                        fds_file.write(updated_content)
        
        # Создаем или обновляем .ini файл с точным форматом без пробелов вокруг =
        ini_filename = f'CheckSURFFIX_{process_id}.ini' if process_id is not None else 'CheckSURFFIX.ini'
        ini_path = os.path.join(inis_path, ini_filename)
        
        # Записываем INI файл вручную без пробелов вокруг =
        with open(ini_path, 'w', encoding='utf-16') as configfile:
            configfile.write('[CheckSURFFIX]\n')
            configfile.write(f'CheckSURFFIX={state}\n')
            
    except Exception as e:
        # Игнорируем ошибки создания файла, чтобы не прерывать основной поток выполнения
        pass

def generate_report_md(app_instance, k, Fpom, v, psi_ud, m, t, tmax, Psi, Stt, bigM, HRRPUA, process_id):
    """
    Генерация Markdown-отчёта для Приложения 1 Методики 1140.

    Args:
        app_instance: Экземпляр приложения
        k: Коэффициент отношения площади
        Fpom: Площадь помещения, м²
        v: Линейная скорость распространения пламени, м/с
        psi_ud: Удельная массовая скорость выгорания, кг/(с·м²)
        m: Полная масса сгораемой нагрузки, кг
        t: Время развития пожара, сек (пользовательское)
        tmax: Время охвата пожаром всей поверхности, сек
        Psi: Скорость выгорания, кг/с
        Stt: Площадь поверхности горючей нагрузки, м²
        bigM: Полная масса горючей нагрузки, кг
        process_id: ID процесса

    Returns:
        str: Содержимое Markdown-отчёта
    """
    # Определяем тип распространения пожара (круговое по умолчанию)
    fire_type = "круговом"

    # Определяем класс функциональной пожарной опасности
    fp_class = "Ф1 - Ф4"  # По умолчанию, k=2

    report = []

    # ===========================================================================
    # ЗАГОЛОВОК
    # ===========================================================================
    report.append("# **Расчёт параметров пожара согласно Приложению 1 Методики 1140**\n")

    # ===========================================================================
    # 1. НОРМАТИВНАЯ БАЗА
    # ===========================================================================
    report.append("## **1. Нормативная база**\n")
    report.append("Настоящий расчёт выполнен в соответствии с **Приложением 1 Методики 1140** — «Порядок проведения расчета и математическая модель для определения времени блокирования путей эвакуации опасными факторами пожара».\n")
    report.append("Расчёт производится на основе экспертного выбора сценария пожара, при котором ожидаются наихудшие последствия для находящихся в здании людей.\n")
    report.append("Формулировка сценария развития пожара включает следующие этапы:\n")
    report.append("* выбор места нахождения первоначального очага пожара и закономерностей его развития;\n")
    report.append("* задание расчётной области (выбор рассматриваемой при расчёте системы помещений, определение учитываемых при расчёте элементов внутренней структуры помещений, задание состояния проёмов);\n")
    report.append("* задание параметров окружающей среды и начальных значений параметров внутри помещений.\n")
    report.append("При расчёте рассматривается **круговое распространение пожара** по твёрдой горючей нагрузке.\n")

    # ===========================================================================
    # 2. ИСХОДНЫЕ ДАННЫЕ
    # ===========================================================================
    report.append("## **2. Исходные данные**\n")
    report.append("Расчёт выполняется на основе следующих входных параметров:\n")
    report.append("| **Параметр** | **Обозначение** | **Значение** | **Ед. изм.** |")
    report.append("|:---|:---:|:---:|:---:|")
    report.append(f"| Коэффициент отношения площади горючей нагрузки к площади помещения | $k$ | {safe_convert_to_float(k):.2f} | – |")
    report.append(f"| Площадь помещения с очагом пожара | $F_{{пом}}$ | {safe_convert_to_float(Fpom):.2f} | м² |")
    report.append(f"| Линейная скорость распространения пламени | $v$ | {safe_convert_to_float(v):.4f} | м/с |")
    report.append(f"| Удельная массовая скорость выгорания | $\\psi_{{уд}}$ | {safe_convert_to_float(psi_ud):.4f} | кг/(с·м²) |")
    report.append(f"| Полная масса сгораемой нагрузки | $m$ | {safe_convert_to_float(m):.2f} | кг |")
    if safe_convert_to_float(t) != 0:
        report.append(f"| Время развития пожара (задано пользователем) | $t$ | {safe_convert_to_float(t):.2f} | с |")
    else:
        report.append(f"| Время развития пожара | $t$ | — (расчётное) | с |")
    report.append("")

    # ===========================================================================
    # 3. РАСЧЁТНЫЕ ФОРМУЛЫ
    # ===========================================================================
    report.append("## **3. Расчётные формулы**\n")
    report.append("### **3.1. Время охвата пожаром всей поверхности горючей нагрузки**\n")
    report.append("Время $t_{{max}}$ определяется по формуле для **кругового** распространения пожара:\n")
    report.append("$$")
    report.append(f"t_{{max}} = \\sqrt{{\\frac{{k \\cdot F_{{пом}}}}{{\\pi \\cdot v^2}}}}")
    report.append("$$\n")
    report.append("Подставляя значения:\n")
    report.append("$$")
    report.append(f"t_{{max}} = \\sqrt{{\\frac{{{safe_convert_to_float(k):.2f} \\cdot {safe_convert_to_float(Fpom):.2f}}}{{\\pi \\cdot {safe_convert_to_float(v):.4f}^2}}}} = {safe_convert_to_float(tmax):.4f} \\text{{ с}}")
    report.append("$$\n")

    if safe_convert_to_float(t) != 0:
        report.append("> **Примечание:** Пользователем задано время развития пожара $t = " + f"{safe_convert_to_float(t):.2f}$ с. В расчёте принято $t_{{max}} = t = {safe_convert_to_float(tmax):.4f}$ с.\n")

    report.append("**Физический смысл:** Время $t_{{max}}$ — это момент, когда фронт пламени достигает границ расчётной площади горючей нагрузки. До этого момента площадь горения растёт по закону круга $S = \\pi (vt)^2$, после — остаётся постоянной.\n")

    report.append("### **3.2. Скорость выгорания**\n")
    report.append("Зависимость скорости выгорания $\\Psi$ (кг/с) от времени для **кругового** распространения пожара определяется формулой:\n")
    report.append("$$")
    report.append(r"\Psi(t) = \begin{cases} \psi_{уд} \cdot \pi \cdot v^2 \cdot t^2 & \text{при } t \le t_{max} \\ \psi_{уд} \cdot \pi \cdot v^2 \cdot t_{max}^2 & \text{при } t > t_{max} \end{cases}, \quad \text{(П1.1)}")
    report.append("$$\n")
    report.append("где $\\psi_{{уд}}$ — удельная скорость выгорания (для жидкостей установившаяся), кг/(с·м²).\n")

    if safe_convert_to_float(m) > 0:
        report.append("При учёте полной массы сгораемой нагрузки $m = " + f"{safe_convert_to_float(m):.2f}$ кг скорость выгорания определяется как:\n")
        report.append("$$")
        report.append(f"\\Psi = \\frac{{m}}{{t_{{max}}}} = \\frac{{{safe_convert_to_float(m):.2f}}}{{{safe_convert_to_float(tmax):.4f}}} = {safe_convert_to_float(Psi):.4f} \\text{{ кг/с}}")
        report.append("$$\n")
    else:
        report.append("Расчётная скорость выгорания:\n")
        report.append("$$")
        report.append(f"\\Psi = \\psi_{{уд}} \\cdot \\pi \\cdot v^2 \\cdot t_{{max}}^2 = {safe_convert_to_float(psi_ud):.4f} \\cdot \\pi \\cdot {safe_convert_to_float(v):.4f}^2 \\cdot {safe_convert_to_float(tmax):.4f}^2 = {safe_convert_to_float(Psi):.4f} \\text{{ кг/с}}")
        report.append("$$\n")

    report.append("### **3.3. Площадь поверхности горючей нагрузки, охватываемая пожаром**\n")
    report.append("Площадь $S_{{tt}}$ определяется по формуле:\n")
    report.append("$$")
    report.append(f"S_{{tt}} = \\pi \\cdot (v \\cdot t_{{max}})^2 = \\pi \\cdot ({safe_convert_to_float(v):.4f} \\cdot {safe_convert_to_float(tmax):.4f})^2 = {safe_convert_to_float(Stt):.4f} \\text{{ м²}}")
    report.append("$$\n")
    report.append(f"Физический смысл: площадь поверхности горючей нагрузки в помещении, охватываемая пожаром за время $t_{{max}}$.\n")

    report.append("### **3.4. Полная масса горючей нагрузки, охваченной пожаром**\n")
    if safe_convert_to_float(m) > 0:
        report.append("С учётом заданной пользователем массы $m$:\n")
        report.append("$$")
        report.append(f"M = m = {safe_convert_to_float(bigM):.4f} \\text{{ кг}}")
        report.append("$$\n")
    else:
        report.append("Полная масса горючей нагрузки, охваченной пожаром за время $t_{{max}}$:\n")
        report.append("$$")
        report.append(f"M = \\Psi \\cdot t_{{max}} = {safe_convert_to_float(Psi):.4f} \\cdot {safe_convert_to_float(tmax):.4f} = {safe_convert_to_float(bigM):.4f} \\text{{ кг}}")
        report.append("$$\n")

    report.append("### **3.5. Полная тепловая мощность очага пожара**\n")
    report.append("Полная тепловая мощность очага пожара $Q$ определяется по формуле:\n")
    report.append("$$")
    report.append(r"Q = H_c \cdot \Psi \cdot n \cdot 1000")
    report.append("$$\n")
    report.append("где:\n")
    report.append(f"* $H_c$ — теплота сгорания, МДж/кг (из файла HOC);\n")
    report.append(f"* $\\Psi = {safe_convert_to_float(Psi):.4f}$ кг/с — скорость выгорания;\n")
    report.append(f"* $n = 0.93$ — коэффициент полноты сгорания;\n")
    report.append(f"* множитель 1000 — перевод из МДж/с в кВт.\n")
    report.append("$$")
    report.append(f"Q = {safe_convert_to_float(HRRPUA):.4f} \\text{{ кВт}}")
    report.append("$$\n")

    # ===========================================================================
    # 4. РЕЗУЛЬТАТЫ РАСЧЁТА
    # ===========================================================================
    report.append("## **4. Результаты расчёта**\n")
    report.append("| **Параметр** | **Обозначение** | **Значение** | **Ед. изм.** |")
    report.append("|:---|:---:|:---:|:---:|")
    report.append(f"| Время охвата пожаром всей поверхности | $t_{{max}}$ | {safe_convert_to_float(tmax):.4f} | с |")
    report.append(f"| Скорость выгорания | $\\Psi$ | {safe_convert_to_float(Psi):.4f} | кг/с |")
    report.append(f"| Полная тепловая мощность очага пожара | $Q$ | {safe_convert_to_float(HRRPUA):.4f} | кВт |")
    report.append(f"| Площадь поверхности горючей нагрузки | $S_{{tt}}$ | {safe_convert_to_float(Stt):.4f} | м² |")
    report.append(f"| Полная масса горючей нагрузки | $M$ | {safe_convert_to_float(bigM):.4f} | кг |")
    report.append("")

    # ===========================================================================
    # 5. ВЫВОДЫ И ОБОСНОВАНИЕ
    # ===========================================================================
    report.append("## **5. Выводы и обоснование**\n")
    report.append("Расчёт параметров пожара выполнен в соответствии с **Приложением 1 Методики 1140**, регламентирующим порядок определения времени блокирования путей эвакуации опасными факторами пожара.\n")
    report.append(f"На основе введённых пользователем исходных данных (коэффициент $k = {safe_convert_to_float(k):.2f}$, площадь помещения $F_{{пом}} = {safe_convert_to_float(Fpom):.2f}$ м², линейная скорость распространения пламени $v = {safe_convert_to_float(v):.4f}$ м/с, удельная массовая скорость выгорания $\\psi_{{уд}} = {safe_convert_to_float(psi_ud):.4f}$ кг/(с·м²)) рассчитаны ключевые параметры развития пожара:\n")
    report.append(f"* **Время охвата пожаром всей поверхности** $t_{{max}} = {safe_convert_to_float(tmax):.4f}$ с — определяет момент, когда вся горючая нагрузка в помещении оказывается охваченной пламенем;\n")
    report.append(f"* **Скорость выгорания** $\\Psi = {safe_convert_to_float(Psi):.4f}$ кг/с — характеризует интенсивность расхода горючей нагрузки;\n")
    report.append(f"* **Полная тепловая мощность очага пожара** $Q = {safe_convert_to_float(HRRPUA):.4f}$ кВт — определяет энерговклад пожара в формирование опасных факторов;\n")
    report.append(f"* **Площадь поверхности горючей нагрузки** $S_{{tt}} = {safe_convert_to_float(Stt):.4f}$ м² — площадь, охватываемая пожаром за время $t_{{max}}$;\n")
    report.append(f"* **Полная масса горючей нагрузки** $M = {safe_convert_to_float(bigM):.4f}$ кг — масса горючего вещества, вовлечённого в горение.\n")

    if safe_convert_to_float(m) > 0:
        report.append(f"\nВ расчёте учтена сокращённая масса горючей нагрузки $m = {safe_convert_to_float(m):.2f}$ кг, что соответствует компенсирующим мероприятиям, направленным на сокращение горючей нагрузки в очаговой зоне.\n")

    report.append("Полученные значения могут быть использованы для:\n")
    report.append("* оценки времени блокирования путей эвакуации опасными факторами пожара;\n")
    report.append("* определения необходимых параметров систем противопожарной защиты;\n")
    report.append("* верификации численных моделей в программах полей (FDS и др.).\n")

    # ===========================================================================
    # ПОДПИСЬ
    # ===========================================================================
    report.append("---\n")
    report.append("*Расчёт выполнен в соответствии с Приложением 1 Методики 1140.*\n")

    return "\n".join(report)


def export_report_md(app_instance, k, Fpom, v, psi_ud, m, t, tmax, Psi, Stt, bigM, HRRPUA, process_id):
    """
    Экспорт отчёта в Markdown файл.

    Args:
        app_instance: Экземпляр приложения (QMainWindow)
        ... параметры расчёта ...
        process_id: ID процесса
    """
    from PyQt6.QtWidgets import QFileDialog, QMessageBox

    file_path, _ = QFileDialog.getSaveFileName(
        app_instance, "Сохранить отчёт (MD)", "report_annex_1.md",
        "Markdown File (*.md);;All Files (*)")

    if file_path:
        try:
            report_content = generate_report_md(
                app_instance, k, Fpom, v, psi_ud, m, t, tmax, Psi, Stt, bigM, HRRPUA, process_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            QMessageBox.information(
                app_instance, "Экспорт завершён",
                f"Отчёт успешно сохранён в:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(
                app_instance, "Ошибка экспорта",
                f"Не удалось сохранить отчёт: {e}")


def export_report_docx(app_instance, k, Fpom, v, psi_ud, m, t, tmax, Psi, Stt, bigM, HRRPUA, process_id):
    """
    Экспорт отчёта в DOCX файл через md_to_docx.

    Args:
        app_instance: Экземпляр приложения (QMainWindow)
        ... параметры расчёта ...
        process_id: ID процесса
    """
    from PyQt6.QtWidgets import QFileDialog, QMessageBox
    import tempfile

    file_path, _ = QFileDialog.getSaveFileName(
        app_instance, "Сохранить отчёт (DOCX)", "report_annex_1.docx",
        "Word Document (*.docx);;All Files (*)")

    if file_path:
        try:
            # Генерируем MD содержимое
            report_content = generate_report_md(
                app_instance, k, Fpom, v, psi_ud, m, t, tmax, Psi, Stt, bigM, HRRPUA, process_id)

            # Создаём временный MD файл
            temp_md = os.path.join(tempfile.gettempdir(), f"temp_report_annex_1_{os.getpid()}.md")
            with open(temp_md, 'w', encoding='utf-8') as f:
                f.write(report_content)

            try:
                from md_to_docx import MarkdownToDocxConverter

                # Определяем путь к pandoc
                current_directory = os.path.dirname(__file__)
                pandoc_exe = os.path.join(current_directory, 'pandoc_embed', 'pandoc.exe')

                converter = MarkdownToDocxConverter(
                    use_pandoc=True,
                    pandoc_path=pandoc_exe if os.path.isfile(pandoc_exe) else None)

                success = converter.convert(temp_md, file_path, preserve_images=True)

                if success:
                    QMessageBox.information(
                        app_instance, "Экспорт завершён",
                        f"Отчёт DOCX успешно сохранён в:\n{file_path}")
                else:
                    QMessageBox.warning(
                        app_instance, "Упрощённая конвертация",
                        "Pandoc не найден. Конвертация выполнена в упрощённом режиме.")
            except ImportError:
                QMessageBox.critical(
                    app_instance, "Ошибка",
                    "Модуль md_to_docx не найден. Убедитесь, что файл md_to_docx.py находится в той же директории.")
            finally:
                if os.path.exists(temp_md):
                    os.unlink(temp_md)

        except Exception as e:
            QMessageBox.critical(
                app_instance, "Ошибка экспорта",
                f"Не удалось сохранить отчёт DOCX: {e}")

