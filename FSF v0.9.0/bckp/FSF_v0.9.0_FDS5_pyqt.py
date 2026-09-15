import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel,
                             QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
                             QMessageBox, QGroupBox, QStatusBar, QComboBox, QCheckBox)
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt, QTimer

try:
    from fsf_utils import (setup_app_palette, get_input_style_common, get_button_style_common, get_button_style_fds5,
                           get_group_box_style, get_label_style, create_input_field_common,
                           load_from_ini_common, calculate_common, save_to_ini_common,
                           read_ini_file_path, read_ini_file_hoc, process_fds_file_common,
                           get_icon_path, safe_convert_to_float, export_report_md, export_report_docx)
except ModuleNotFoundError:
    import os
    import sys
    # Добавляем директорию, содержащую fsf_utils.py, в Python-путь
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    from fsf_utils import (setup_app_palette, get_input_style_common, get_button_style_common, get_button_style_fds5,
                           get_group_box_style, get_label_style, create_input_field_common,
                           load_from_ini_common, calculate_common, save_to_ini_common,
                           read_ini_file_path, read_ini_file_hoc, process_fds_file_common,
                           get_icon_path, safe_convert_to_float, export_report_md, export_report_docx)

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
        self.setWindowTitle(f"FSF v0.9.0 ID:{self.process_id if self.process_id is not None else 'N/A'}")
        self.setMinimumSize(450, 1150)

        # Устанавливаем иконку
        try:
            icon_path = get_icon_path(__file__, 'fsf.ico')
            self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            print(f"Error setting window icon: {e}")


        setup_app_palette(self)
        self._setup_ui()
        load_from_ini_common(self, self.k_entry, self.fpom_entry, self.psyd_entry, self.v_entry, self.m_entry, self.t_entry)
        
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

        # ==================== Выбор режима расчёта Q ====================
        q_mode_group = QGroupBox("Режим расчёта мощности очага пожара (Q)")
        q_mode_group.setStyleSheet(get_group_box_style())
        q_mode_layout = QVBoxLayout(q_mode_group)

        self.q_mode_combo = QComboBox()
        self.q_mode_combo.addItem("Расчетная массовая скорость выгорания (Методика 1140)")
        self.q_mode_combo.addItem("Произвольный Q")
        self.q_mode_combo.setFont(QFont("Segoe UI", 11))
        self.q_mode_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #cbd5e1;
                border-radius: 5px;
                background-color: white;
            }
            QComboBox:hover {
                border: 1px solid #7dd3fc;
            }
        """)
        self.q_mode_combo.currentIndexChanged.connect(self._on_q_mode_changed)
        q_mode_layout.addWidget(self.q_mode_combo)

        # ==================== Чекбокс АУПТ ====================
        self.aupt_checkbox = QCheckBox("Уменьшать массовую скорость выгорания в 2 раза (сработка АУПТ)")
        self.aupt_checkbox.setFont(QFont("Segoe UI", 11))
        self.aupt_checkbox.setStyleSheet(get_label_style())
        self.aupt_checkbox.stateChanged.connect(self._on_aupt_changed)

        # Поле ввода t_АУПТ (скрыто по умолчанию)
        aupt_input_container = QWidget()
        aupt_input_layout = QHBoxLayout(aupt_input_container)
        aupt_input_layout.setContentsMargins(0, 5, 0, 0)
        aupt_label = QLabel("t_{АУПТ} (с):")
        aupt_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        aupt_label.setStyleSheet(get_label_style())
        aupt_input_layout.addWidget(aupt_label)

        self.t_aupt_entry = QLineEdit()
        self.t_aupt_entry.setPlaceholderText("Время сработки АУПТ, сек")
        self.t_aupt_entry.setToolTip("Время сработки автоматической установки пожаротушения (сек)")
        self.t_aupt_entry.setStyleSheet(get_input_style_common())
        self.t_aupt_entry.setFixedWidth(150)
        aupt_input_layout.addWidget(self.t_aupt_entry)
        aupt_input_layout.addStretch()

        aupt_input_container.setVisible(False)

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
        self.t_entry = self._create_input_field("t", "Время развития пожара, сек", "Время развития пожара (сек)\n\n0 или пусто - значение по умолчанию (tmax рассчитывается автоматически)\n\nЕсли указано, tmax = t", prefix="* ")

        # Нередактируемые поля
        self.tmax_entry = self._create_input_field("tmax", "Время охвата пожаром всей поверхности, сек", "Время охвата пожаром всей поверхности горючей нагрузки в помещении, сек", read_only=True, prefix="= ")
        self.psy_entry = self._create_input_field("Ψ", "Зависимость скорости выгорания от времени, кг/с", "Зависимость скорости выгорания от времени, (кг/с)", read_only=True, prefix="= ")
        self.hrr_entry = self._create_input_field("Q", "Полная тепловая мощность очага пожара, кДж", "Полная тепловая мощность очага пожара, кДж", read_only=True, prefix="= ")
        self.stt_entry = self._create_input_field("Stt", "Площадь поверхности горючей нагрузки, м²", f"Площадь поверхности горючей нагрузки в помещении, охватываемая пожаром за время tmax, м²", read_only=True, prefix="= ")
        self.bigM_entry = self._create_input_field("M", "Полная масса горючей нагрузки, кг", "Полная масса горючей нагрузки (кг), охваченной пожаром за время tmax", read_only=True, prefix="= ")

        # Сохраняем ссылку на QLabel поля Q для изменения текста
        self.hrr_labels = self.hrr_entry[0].findChildren(QLabel)
        self.hrr_lineedit = self.hrr_entry[1]
        self.hrr_original_label_text = "Q"

        # Кнопки
        self.calculate_button = QPushButton("Рассчитать")
        self.calculate_button.setFont(QFont("Segoe UI", 11, QFont.Weight.Light))
        self.calculate_button.setStyleSheet(get_button_style_fds5())
        self.calculate_button.setFixedWidth(200)
        self.calculate_button.clicked.connect(lambda: self._calculate_and_enable_reports())

        self.process_button = QPushButton("Сохранить")
        self.process_button.setFont(QFont("Segoe UI", 11, QFont.Weight.Light))
        self.process_button.setStyleSheet(get_button_style_fds5())
        self.process_button.setFixedWidth(200)
        self.process_button.setEnabled(False)
        self.process_button.clicked.connect(self._process_fds_file)
        self.process_button.clicked.connect(lambda: self.report_md_button.setEnabled(True))
        self.process_button.clicked.connect(lambda: self.report_docx_button.setEnabled(True))

        # Кнопки экспорта отчёта
        self.report_md_button = QPushButton("Вывести в отчёт (MD)")
        self.report_md_button.setFont(QFont("Segoe UI", 11, QFont.Weight.Light))
        self.report_md_button.setStyleSheet(get_button_style_fds5())
        self.report_md_button.setFixedWidth(240)
        self.report_md_button.setEnabled(False)
        self.report_md_button.clicked.connect(self._export_report_md)

        self.report_docx_button = QPushButton("Вывести в отчёт (DOCX)")
        self.report_docx_button.setFont(QFont("Segoe UI", 11, QFont.Weight.Light))
        self.report_docx_button.setStyleSheet(get_button_style_fds5())
        self.report_docx_button.setFixedWidth(240)
        self.report_docx_button.setEnabled(False)
        self.report_docx_button.clicked.connect(self._export_report_docx)

        # Layouts
        input_layout.addWidget(q_mode_group)
        input_layout.addWidget(self.aupt_checkbox)
        input_layout.addWidget(aupt_input_container)
        input_layout.addWidget(self.k_entry[0])
        input_layout.addWidget(self.fpom_entry[0])
        input_layout.addWidget(self.v_entry[0])
        input_layout.addWidget(self.psyd_entry[0])
        input_layout.addWidget(self.m_entry[0])
        input_layout.addWidget(self.t_entry[0])

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

        # Кнопки отчётов - отдельный ряд
        report_button_row_layout = QHBoxLayout()
        report_button_row_layout.addStretch()
        report_button_row_layout.addWidget(self.report_md_button)
        report_button_row_layout.addSpacing(20)
        report_button_row_layout.addWidget(self.report_docx_button)
        report_button_row_layout.addStretch()

        main_layout.addWidget(input_group_box)
        main_layout.addWidget(result_group_box)
        main_layout.addLayout(button_row_layout)
        main_layout.addLayout(report_button_row_layout)
        main_layout.addStretch()

    def _on_q_mode_changed(self, index):
        """Обработка изменения режима расчёта Q."""
        if index == 1:
            for lbl in self.hrr_labels:
                if lbl.text() == self.hrr_original_label_text:
                    lbl.setText("Ψ(t)")
                    lbl.setStyleSheet("""
                        QLabel {
                            font-size: 14px;
                            font-weight: 500;
                            color: #cbd5e1;
                        }
                    """)
                    break
            self.hrr_lineedit.setVisible(False)
            existing_placeholder = self.hrr_entry[0].findChild(QLabel, "hrr_placeholder")
            if not existing_placeholder:
                placeholder = QLabel("Контролируется функцией Ψ(t)")
                placeholder.setObjectName("hrr_placeholder")
                placeholder.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                placeholder.setStyleSheet("""
                    QLabel {
                        color: #94a3b8;
                        padding: 12px;
                        border: 1px solid #cbd5e1;
                        border-radius: 5px;
                        background-color: #f1f5f9;
                    }
                """)
                layout = self.hrr_entry[0].layout()
                layout.addWidget(placeholder)
        else:
            for lbl in self.hrr_labels:
                if lbl.text() == "Ψ(t)":
                    lbl.setText(self.hrr_original_label_text)
                    lbl.setStyleSheet(get_label_style())
                    break
            self.hrr_lineedit.setVisible(True)
            placeholder = self.hrr_entry[0].findChild(QLabel, "hrr_placeholder")
            if placeholder:
                placeholder.deleteLater()

    def _on_aupt_changed(self, state):
        """Показываем/скрываем поле ввода t_АУПТ."""
        parent = self.t_aupt_entry.parent()
        if parent:
            parent.setVisible(state == Qt.CheckState.Checked.value)

    def _process_fds_file(self):
        """Обработка FDS файла с учётом режима АУПТ."""
        aupt_enabled = self.aupt_checkbox.isChecked()
        t_aupt_str = self.t_aupt_entry.text().strip() if aupt_enabled else ""

        process_fds_file_common(
            self, self.k_entry, self.fpom_entry, self.psyd_entry, self.v_entry,
            self.m_entry, self.t_entry, self.tmax_entry, self.psy_entry,
            self.hrr_entry, self.stt_entry, self.bigM_entry, self.process_button,
            ProcessID, read_ini_file_path, read_ini_file_hoc, self.statusBar,
            aupt_enabled=aupt_enabled, t_aupt_str=t_aupt_str)

    def _calculate_and_enable_reports(self):
        """Выполняет расчёт и включает кнопки отчётов."""
        calculate_common(self, self.k_entry, self.fpom_entry, self.psyd_entry, self.v_entry, self.m_entry, self.t_entry, self.tmax_entry, self.psy_entry, self.hrr_entry, self.stt_entry, self.bigM_entry, self.process_button, self.statusBar, ProcessID, read_ini_file_hoc)
        # Включаем кнопки отчётов после успешного расчёта
        self.report_md_button.setEnabled(True)
        self.report_docx_button.setEnabled(True)

    def _export_report_md(self):
        """Экспорт отчёта в Markdown."""
        self.statusBar.showMessage("Экспорт в MD...")
        export_report_md(
            self,
            self.k_entry[1].text(), self.fpom_entry[1].text(),
            self.v_entry[1].text(), self.psyd_entry[1].text(),
            self.m_entry[1].text(), self.t_entry[1].text(),
            self.tmax_entry[1].text(), self.psy_entry[1].text(),
            self.stt_entry[1].text(), self.bigM_entry[1].text(),
            self.hrr_entry[1].text(), ProcessID)
        self.statusBar.showMessage("Экспорт в MD завершён.")

    def _export_report_docx(self):
        """Экспорт отчёта в DOCX."""
        self.statusBar.showMessage("Экспорт в DOCX...")
        export_report_docx(
            self,
            self.k_entry[1].text(), self.fpom_entry[1].text(),
            self.v_entry[1].text(), self.psyd_entry[1].text(),
            self.m_entry[1].text(), self.t_entry[1].text(),
            self.tmax_entry[1].text(), self.psy_entry[1].text(),
            self.stt_entry[1].text(), self.bigM_entry[1].text(),
            self.hrr_entry[1].text(), ProcessID)
        self.statusBar.showMessage("Экспорт в DOCX завершён.")

    def _create_input_field(self, label_text, hint_text, tooltip_text, read_only=False, prefix=""):
        return create_input_field_common(self, label_text, hint_text, tooltip_text, read_only, prefix)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Устанавливаем иконку
    try:
        icon_path = get_icon_path(__file__, 'fsf.ico')
        app.setWindowIcon(QIcon(icon_path))
    except Exception as e:
        print(f"Error setting application icon: {e}")

    main_window = FDSProcessorAppQt(ProcessID)
    main_window.show()
    sys.exit(app.exec())
