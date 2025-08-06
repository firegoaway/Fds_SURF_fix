import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel,
                             QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
                             QMessageBox, QGroupBox, QStatusBar)
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt, QTimer

try:
    from fsf_utils import (setup_app_palette, get_input_style_common, get_button_style_common,
                           get_group_box_style, get_label_style, create_input_field_common,
                           load_from_ini_common, calculate_common, save_to_ini_common,
                           read_ini_file_path, read_ini_file_hoc, process_fds_file_common,
                           get_icon_path)
except ModuleNotFoundError:
    import os
    import sys
    # Add the directory containing fsf_utils.py to the Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    from fsf_utils import (setup_app_palette, get_input_style_common, get_button_style_common,
                           get_group_box_style, get_label_style, create_input_field_common,
                           load_from_ini_common, calculate_common, save_to_ini_common,
                           read_ini_file_path, read_ini_file_hoc, process_fds_file_common,
                           get_icon_path)

# Глобальная переменная для ProcessID
ProcessID = None
if len(sys.argv) > 1:
    try:
        ProcessID = int(sys.argv[1])
        print(f"Process ID received from AHK: {ProcessID}")
    except ValueError:
        print(f"Invalid Process ID received: {sys.argv[1]}. Using None.")
else:
    print("No Process ID received.")

class FDSProcessorAppQt(QMainWindow):
    def __init__(self, process_id=None):
        super().__init__()
        self.process_id = process_id
        self.setWindowTitle(f"FSF v0.6.0 ID:{self.process_id if self.process_id is not None else 'N/A'}")
        self.setMinimumSize(450, 850)

        # Set the application icon
        try:
            icon_path = get_icon_path(__file__, 'fsf.ico')
            self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            print(f"Error setting window icon: {e}")


        setup_app_palette(self)
        self._setup_ui()
        load_from_ini_common(self, self.k_entry, self.fpom_entry, self.psyd_entry, self.v_entry, self.m_entry)
        
    def _setup_ui(self):
        """Настройка пользовательского интерфейса."""

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Готово")
        
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # Заголовок приложения
        header1 = QLabel("Параметры пожара")
        header1.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header1.setStyleSheet("color: rgb(3, 105, 161); padding: 1px;")
        main_layout.addWidget(header1)

        header2 = QLabel("(согласно Приложению 1 Методики 1140)")
        header2.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        header2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header2.setStyleSheet("color: rgb(3, 105, 161); padding: 1px;")
        main_layout.addWidget(header2)

        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        self.setCentralWidget(central_widget)

        input_group_box = QGroupBox("Введите значения переменных")
        input_group_box.setStyleSheet(get_group_box_style())
        input_layout = QVBoxLayout(input_group_box)

        result_group_box = QGroupBox("Результат")
        result_group_box.setStyleSheet(get_group_box_style())
        result_layout = QVBoxLayout(result_group_box)

        # Входные поля
        self.k_entry = self._create_input_field("k", "Коэффициент k", "Коэффициент, учитывающий отличие фактической площади горючей нагрузки в помещении и площади помещения.\n\nДля помещений классов функциональной пожарной опасности Ф1 - Ф4 следует принимать равным 2", prefix="* ")
        self.fpom_entry = self._create_input_field("Fпом", "Площадь помещения с очагом пожара, м²", "Площадь помещения с очагом пожара, м²", prefix="* ")
        self.v_entry = self._create_input_field("v", "Линейная скорость распространения пламени, м/с", "Линейная скорость распространения пламени, м/с", prefix="* ")
        self.psyd_entry = self._create_input_field("ψуд", "Удельная массовая скорость выгорания, кг/(с·м²)", "Удельная массовая скорость выгорания (для жидкостей установившаяся), кг/(с·м²)", prefix="* ")
        self.m_entry = self._create_input_field("m", "Полная масса сгораемой нагрузки, кг", "Полная масса сгораемой нагрузки (кг)\n\n0 - значение по умолчанию\n\nПри разработке компенсирующих мероприятий,\nнаправленных на сокращение горючей нагрузки в очаговой зоне,\nукажите это значение.\nОно должно быть меньше M при m = 0", prefix="* ")

        # Нередактируемые поля
        self.tmax_entry = self._create_input_field("tmax", "Время охвата пожаром всей поверхности, сек", "Время охвата пожаром всей поверхности горючей нагрузки в помещении, сек", read_only=True, prefix="= ")
        self.psy_entry = self._create_input_field("Ψ", "Зависимость скорости выгорания от времени, кг/с", "Зависимость скорости выгорания от времени, (кг/с)", read_only=True, prefix="= ")
        self.hrr_entry = self._create_input_field("Q", "Полная тепловая мощность очага пожара, кДж", "Полная тепловая мощность очага пожара, кДж", read_only=True, prefix="= ")
        self.stt_entry = self._create_input_field("Stt", "Площадь поверхности горючей нагрузки, м²", f"Площадь поверхности горючей нагрузки в помещении, охватываемая пожаром за время tmax, м²", read_only=True, prefix="= ")
        self.bigM_entry = self._create_input_field("M", "Полная масса горючей нагрузки, кг", "Полная масса горючей нагрузки (кг), охваченной пожаром за время tmax", read_only=True, prefix="= ")

        # Кнопки
        self.calculate_button = QPushButton("Рассчитать")
        self.calculate_button.setFont(QFont("Segoe UI", 11, QFont.Weight.Light))
        self.calculate_button.setStyleSheet(get_button_style_common())
        self.calculate_button.clicked.connect(lambda: calculate_common(self, self.k_entry, self.fpom_entry, self.psyd_entry, self.v_entry, self.m_entry, self.tmax_entry, self.psy_entry, self.hrr_entry, self.stt_entry, self.bigM_entry, self.process_button, self.statusBar, ProcessID, read_ini_file_hoc))

        self.process_button = QPushButton("Сохранить")
        self.process_button.setFont(QFont("Segoe UI", 11, QFont.Weight.Light))
        self.process_button.setStyleSheet(get_button_style_common())
        self.process_button.setEnabled(False)
        self.process_button.clicked.connect(lambda: process_fds_file_common(self, self.k_entry, self.fpom_entry, self.psyd_entry, self.v_entry, self.m_entry, self.tmax_entry, self.psy_entry, self.hrr_entry, self.stt_entry, self.bigM_entry, self.process_button, ProcessID, read_ini_file_path, read_ini_file_hoc))

        # Layouts
        input_layout.addWidget(self.k_entry[0])
        input_layout.addWidget(self.fpom_entry[0])
        input_layout.addWidget(self.v_entry[0])
        input_layout.addWidget(self.psyd_entry[0])
        input_layout.addWidget(self.m_entry[0])

        result_layout.addWidget(self.tmax_entry[0])
        result_layout.addWidget(self.psy_entry[0])
        result_layout.addWidget(self.hrr_entry[0])
        result_layout.addWidget(self.stt_entry[0])
        result_layout.addWidget(self.bigM_entry[0])

        button_row_layout = QHBoxLayout()
        button_row_layout.addStretch()
        button_row_layout.addWidget(self.calculate_button)
        button_row_layout.addSpacing(20)
        button_row_layout.addWidget(self.process_button)
        button_row_layout.addStretch()

        main_layout.addWidget(input_group_box)
        main_layout.addWidget(result_group_box)
        main_layout.addLayout(button_row_layout)
        main_layout.addStretch()

    def _create_input_field(self, label_text, hint_text, tooltip_text, read_only=False, prefix=""):
        return create_input_field_common(self, label_text, hint_text, tooltip_text, read_only, prefix)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Set the application icon
    try:
        icon_path = get_icon_path(__file__, 'fsf.ico')
        app.setWindowIcon(QIcon(icon_path))
    except Exception as e:
        print(f"Error setting application icon: {e}")

    main_window = FDSProcessorAppQt(ProcessID)
    main_window.show()
    sys.exit(app.exec())