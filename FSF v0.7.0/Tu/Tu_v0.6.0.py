import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
import io
import base64
import sys
import math

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QComboBox, QMessageBox, QFileDialog, QStatusBar,
                             QFormLayout, QScrollArea)
from PyQt6.QtGui import QPalette, QColor, QFont, QPixmap, QDoubleValidator, QIntValidator
from PyQt6.QtCore import Qt, QLocale, QSize

# Ensure Matplotlib uses a non-GUI backend
plt.switch_backend('Agg')

class SprinklerCalcApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Расчёт времени активации спринклера v0.6.0")
        self.setMinimumSize(1400, 800) # Match original Flet window size

        self._setup_palette()
        self._setup_ui()

        # Initialize instance variables that will hold calculation results
        self.temperatures_gas = []
        self.critical_time_gas = None
        self.Tu_solution = []
        self.x_mark_dTu = None
        self.y_mark_dTu = None
        self.time = None
        self.plot_pixmap = None # To store the generated plot for saving

        # Dynamically assigned callable attributes (initialized to None)
        self.q_func = None
        self.phi_func = None
        self.beta_val = None # This will be a float, not a function
        self.Delta_func = None
        # Fixed constants
        self.sigma = 5.670374419e-8
        self.g = 9.81
        self.rho = 1.2   # Плотность воздуха (кг/м³)
        self.cp = 1.005  # Удельная теплоёмкость воздуха (кДж/(кг·K))

        # Connect button signals
        self.calculate_button.clicked.connect(self.calculate)
        self.save_plot_button.clicked.connect(self.save_plot)
        self.save_plot_button.setEnabled(False) # Initially disabled

        # Set up status bar
        self.statusBar = QStatusBar() 
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Готово к расчёту")

    def _setup_palette(self):
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
        self.setPalette(palette)

    def _get_input_style(self):
        return """
            QLineEdit {
                padding: 8px;
                border: 1px solid #cbd5e1;
                border-radius: 5px;
                background-color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #7dd3fc;
            }
        """

    def _get_button_style(self):
        return """
            QPushButton {
                background-color: #bae6fd;
                color: #0369a1;
                border: none;
                border-radius: 5px;
                padding: 10px 15px;
                font-weight: bold;
                font-size: 14px;
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

    def _create_input_field(self, layout, name, label_text, default_value, tooltip_text, is_float=True):
        label = QLabel(label_text + ":")
        label.setFont(QFont("Segoe UI", 12))
        setattr(self, f"{name}_label", label) # Store label reference

        line_edit = QLineEdit(default_value)
        line_edit.setToolTip(tooltip_text)
        line_edit.setStyleSheet(self._get_input_style())
        if is_float:
            validator = QDoubleValidator()
            validator.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)) # For '.' decimal separator
            line_edit.setValidator(validator)
        else:
            validator = QIntValidator()
            line_edit.setValidator(validator)
        setattr(self, name, line_edit)
        layout.addRow(label, line_edit)

    def _create_output_field(self, layout, name, label_text, tooltip_text):
        label = QLabel(label_text + ":")
        label.setFont(QFont("Segoe UI", 12))

        line_edit = QLineEdit()
        line_edit.setReadOnly(True)
        line_edit.setToolTip(tooltip_text)
        line_edit.setStyleSheet(self._get_input_style())
        setattr(self, name, line_edit)
        layout.addRow(label, line_edit)

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout() # Fix: Remove central_widget as parent
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Left Column: Input Fields
        # Left Column: Input Fields
        left_widget = QWidget()
        left_layout = QFormLayout(left_widget) # Use QFormLayout for alignment
        left_layout.setContentsMargins(10, 10, 10, 10) # Add some padding inside the form layout
        left_layout.setSpacing(10)

        header_label = QLabel("Введите значения\nпеременных")
        header_style = "font-size: 14px; font-weight: bold; color: #0284c7;"
        header_label.setStyleSheet(header_style)
        left_layout.addWidget(header_label)

        # Input Fields with Labels
        self._create_input_field(left_layout, "Fpom_input", "Fпом", "500", "Площадь помещения с очагом пожара, м²")
        self._create_input_field(left_layout, "HRR_input", "HRR", "13.800", "Низшая теплота сгорания, МДж/м²")
        self._create_input_field(left_layout, "v_input", "v", "0.0055", "Линейная скорость распространения пламени, м/с")
        self._create_input_field(left_layout, "psi_yd_input", "ψуд", "0.015", "Удельная массовая скорость выгорания, кг/(с*м²)")
        self._create_input_field(left_layout, "Cs_input", "Cs", "0.1", "Размер ячейки, м")
        self._create_input_field(left_layout, "Hpom_input", "Hпом", "3", "Высота помещения, м")
        self._create_input_field(left_layout, "L_input", "L", "4", "Нормативное расстояние между спринклерами, м")
        self._create_input_field(left_layout, "epsilon_input", "ε", "0.85", "Коэффициент облучённости")

        # Dropdown for sprinkler type
        sprinkler_type_label = QLabel("Головка:")
        sprinkler_type_label.setStyleSheet("font-size: 14px;")
        self.sprinkler_type_dropdown = QComboBox()
        self.sprinkler_type_dropdown.addItems(["Стальная", "Медная", "Латунная"])
        self.sprinkler_type_dropdown.setCurrentText("Стальная")
        self.sprinkler_type_dropdown.setStyleSheet(self._get_input_style())
        left_layout.addRow(sprinkler_type_label, self.sprinkler_type_dropdown) # Changed to addRow

        self._create_input_field(left_layout, "k_input", "k", "2", "Коэффициент, описывающий отношение поверхности горючей нагрузки к площади помещения")
        self._create_input_field(left_layout, "Tu_0_input", "Tu₀", "24", "Максимально возможная в течение года температура, °C", is_float=True)
        self._create_input_field(left_layout, "Tu_i_input", "Tuᵢ", "57", "Критическая температура чувствительного элемента спринклера, °C", is_float=True)
        
        # Add stretch to push inputs to the top within the scrollable widget
        # QFormLayout doesn't directly support stretch, so we add a spacer or let it fill
        # If QFormLayout fills space, stretch might not be needed, but let's keep it for now
        # If alignment issues arise, a spacer widget can be added within the form layout if necessary

        # Add the scrollable widget to the main layout
        main_layout.addWidget(left_widget)

        # Center Column: Plot Area and Main Heading
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)

        main_heading = QLabel("Расчёт времени задержки, связанного с инерционностью АУПТ")
        main_heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_heading.setStyleSheet("font-size: 24px; font-weight: 100;")
        center_layout.addWidget(main_heading)

        self.plot_label = QLabel("График будет отображен здесь")
        self.plot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.plot_label.setMinimumSize(800, 600) # Match original Flet plot size
        self.plot_label.setStyleSheet("border: 1px solid #cbd5e1; background-color: white;")
        center_layout.addWidget(self.plot_label)
        center_layout.addStretch(1) # Push elements to top
        main_layout.addWidget(center_widget)

        # Right Column: Output Fields
        right_container_widget = QWidget()
        right_container_layout = QVBoxLayout(right_container_widget)
        right_container_layout.setContentsMargins(0, 0, 0, 0) # No extra margins for the container

        right_form_widget = QWidget()
        right_layout = QFormLayout(right_form_widget) # Use QFormLayout for output fields
        right_layout.setContentsMargins(10, 10, 10, 10) # Add padding inside the form
        right_layout.setSpacing(10)

        result_heading = QLabel("Результаты")
        result_heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_style = "font-size: 14px; font-weight: bold; color: #0284c7;"
        result_heading.setStyleSheet(result_style)
        right_layout.addWidget(result_heading)

        self._create_output_field(right_layout, "alpha_output", "α", "Коэффициент пропускания атмосферы")
        self._create_output_field(right_layout, "hu_output", "hu", "Высота расположения термочувствительного элемента спринклера (м)")
        self._create_output_field(right_layout, "angle_output", "angle", "Угловой коэффициент теплового переноса")
        self._create_output_field(right_layout, "tmax_output", "tmax", "Время охвата пожаром всей поверхности горючей нагрузки в помещении (сек)")
        self._create_output_field(right_layout, "t_result_output", "tобн_инерц", "Время задержки, связанное с инерционностью АУПТ (сек)")
        self._create_output_field(right_layout, "tT_result_output", "tпор", "Время достижения порогового значения срабатывания АУПТ (сек)")

        right_container_layout.addWidget(right_form_widget)
        right_container_layout.addStretch(1) # Push form content to top within the container
        main_layout.addWidget(right_container_widget)

        # Buttons at the bottom
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(50)

        self.calculate_button = QPushButton("Рассчитать")
        self.calculate_button.setStyleSheet(self._get_button_style())
        button_layout.addWidget(self.calculate_button)

        self.save_plot_button = QPushButton("Сохранить изображение графика")
        self.save_plot_button.setStyleSheet(self._get_button_style())
        button_layout.addWidget(self.save_plot_button)
        
        # Add button_layout to the main vertical layout of the central widget
        # Since main_layout is QHBoxLayout, we need a parent QVBoxLayout for everything
        # Re-structuring: central_widget's layout should be QVBoxLayout first
        # Then add the main_layout (QHBoxLayout for columns) and button_layout (QHBoxLayout)
        
        temp_main_v_layout = QVBoxLayout()
        temp_main_v_layout.addLayout(main_layout)
        temp_main_v_layout.addLayout(button_layout)
        central_widget.setLayout(temp_main_v_layout) # Set this as the central widget's layout

    def sprinkler_sensor_temp(self, Tu, t, T_func):
        T = T_func(t)
        if T < self.Tu_0:
            return 0
        return np.sqrt(self.u_dynamic(T)) / self.K * (T - Tu)

    def gas_temperature(self, t):
        if self.Delta_func is None or self.q_func is None:
            # This should ideally not happen if calculate() is called first
            raise ValueError("Ошибка: Функции Delta_func или q_func не инициализированы.")
        T = ((1 / self.Delta_func(t)) * (self.q_func(t) / (self.epsilon * self.sigma)) * np.exp(-(self.alpha * self.hu))) ** (1/4)
        return max(T, self.Tu_0)

    def u_dynamic(self, T):
        return np.sqrt(2 * self.g * self.hu * (T / (self.Tu_0 + 273.15)))

    def Psi(self, t):
        if self.q_func is None:
            raise ValueError("Ошибка: Функция q_func не инициализирована.")
        return self.q_func(t)

    def heat_release_rate(self, t):
        return self.Psi(t) * 1000 * 0.93

    def temperature_rise(self, Q):
        # L is actually self.L from input
        return Q**(7/4) / (self.rho * self.cp * np.sqrt(self.g) * self.L**2 * self.hu**(5/3))

    def calculate(self):
        try:
            # Input parsing and validation
            self.Fpom = float(self.Fpom_input.text())
            self.HRR = float(self.HRR_input.text())
            self.v = float(self.v_input.text())
            self.psi_yd = float(self.psi_yd_input.text())
            self.Cs = float(self.Cs_input.text())
            self.Hpom = float(self.Hpom_input.text())
            self.L = float(self.L_input.text())
            self.epsilon = float(self.epsilon_input.text())
            self.k = float(self.k_input.text())
            self.Tu_0 = float(self.Tu_0_input.text())
            self.Tu_i = float(self.Tu_i_input.text())

            if not all(val > 0 for val in [self.Fpom, self.HRR, self.v, self.psi_yd, self.Cs, self.Hpom, self.L, self.epsilon, self.k, self.Tu_0, self.Tu_i]):
                raise ValueError("Все входные параметры должны быть положительными числами.")
            
            # Select K based on sprinkler type
            sprinkler_type = self.sprinkler_type_dropdown.currentText()
            if sprinkler_type == "Стальная":
                self.K = np.sqrt((0.265 * 0.46) / 0.05)
            elif sprinkler_type == "Медная":
                self.K = np.sqrt((0.265 * 0.385) / 0.385)
            elif sprinkler_type == "Латунная":
                self.K = np.sqrt((0.265 * 0.375) / 0.11)
            else:
                self.K = 50 # Default or error handling

            # Calculate intermediate parameters
            self.hu = self.Hpom - self.Cs
            if self.hu <= 0:
                raise ValueError("Высота спринклера (hu) должна быть положительной (Hpom > Cs).")

            self.angle = np.arctan(self.L / self.hu)
            self.tmax = np.sqrt((self.k * self.Fpom) / (np.pi * self.v**2))
            
            # Dynamically assign lambda functions that depend on calculated instance variables
            # These must be assigned AFTER all their dependencies (self.HRR, self.v, self.tmax etc.) are set
            self.phi_func = lambda t: np.sqrt(1 + self.v**2 * t**2)
            # beta_val is a float, not a function
            self.beta_val = np.sqrt(1 + self.angle * (np.pi / 180)) 
            # Delta_func depends on phi_func and beta_val, so it must be defined after them
            self.Delta_func = lambda t: np.arctan(self.phi_func(t)) * np.arctan(self.beta_val)
            self.q_func = lambda t: self.HRR * self.psi_yd * np.pi * self.v**2 * t**2 if t < self.tmax else self.HRR * self.psi_yd * np.pi * self.v**2 * self.tmax**2
            
            self.d = np.sqrt((4 * self.Fpom) / np.pi)
            self.alpha = 10e-4 * np.exp(-7 * 10e-4 * (self.L - 0.5 * self.d))

            # Time array for calculations
            self.time = np.linspace(0, self.tmax * 2, 10000) # Extend time range slightly beyond tmax for gas temp trend

            # Calculate gas temperatures
            self.temperatures_gas = [self.Tu_0 + self.temperature_rise(self.heat_release_rate(t)) for t in self.time]

            # Find critical time for gas temperature
            self.critical_time_gas = next((t for t, temp in zip(self.time, self.temperatures_gas) if temp >= self.Tu_i), None)

            # Integrate sprinkler sensor temperature
            # Ensure sprinkler_sensor_temp and gas_temperature use 'self' correctly
            self.Tu_solution = odeint(self.sprinkler_sensor_temp, self.Tu_0, self.time, args=(self.gas_temperature,))
            
            self.x_mark_dTu, self.y_mark_dTu = None, None
            for i in range(len(self.Tu_solution)):
                if self.Tu_solution[i, 0] >= self.Tu_i:
                    self.x_mark_dTu = self.time[i]
                    self.y_mark_dTu = self.Tu_solution[i, 0]
                    break

            # Update output fields
            self.hu_output.setText(f"{self.hu:.4f}")
            self.angle_output.setText(f"{self.angle:.4f}")
            self.tmax_output.setText(f"{self.tmax:.4f}")
            self.alpha_output.setText(f"{self.alpha:.7f}")
            self.t_result_output.setText(f"{self.x_mark_dTu:.2f}" if self.x_mark_dTu is not None else "N/A") 
            self.tT_result_output.setText(f"{self.critical_time_gas:.2f}" if self.critical_time_gas is not None else "N/A")
            
            self.statusBar.showMessage("Расчет завершен успешно.")
            self.save_plot_button.setEnabled(True)
            self.generate_plot()

        except ValueError as ve:
            QMessageBox.warning(self, "Ошибка ввода", f"Пожалуйста, введите допустимые положительные числа!\n{ve}")
            self.statusBar.showMessage("Ошибка ввода.")
            self.save_plot_button.setEnabled(False)
        except ZeroDivisionError:
            QMessageBox.warning(self, "Ошибка расчета", "Деление на ноль. Проверьте входные параметры.")
            self.statusBar.showMessage("Ошибка расчета: Деление на ноль.")
            self.save_plot_button.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Критическая ошибка", f"Произошла непредвиденная ошибка: {type(e).__name__}: {e}")
            self.statusBar.showMessage("Произошла критическая ошибка.")
            self.save_plot_button.setEnabled(False)

    def generate_plot(self):
        try:
            if self.time is None or len(self.time) == 0:
                self.plot_label.setText("Нет данных для построения графика.")
                return

            # Determine plot cut-off time more robustly
            max_plot_time = max(self.critical_time_gas or 0, self.x_mark_dTu or 0)
            if max_plot_time == 0: # If both are None or 0, use tmax
                max_plot_time = self.tmax
            
            # Ensure cut_time is reasonable and within self.time range
            # Add some buffer to the max_plot_time
            buffer_time = max(10, max_plot_time * 0.1) # at least 10 seconds or 10% of max_plot_time
            cut_time = max_plot_time + buffer_time

            cut_index = np.searchsorted(self.time, cut_time)
            # Ensure cut_index is not out of bounds
            if cut_index == 0: cut_index = 1 # At least one point
            if cut_index > len(self.time): cut_index = len(self.time)

            time_cut = self.time[:cut_index]
            temperatures_gas_cut = self.temperatures_gas[:cut_index]
            Tu_solution_cut = self.Tu_solution[:cut_index]

            fig, ax1 = plt.subplots(figsize=(10, 6))

            # Plot dTu on the left y-axis
            ax1.set_ylabel('Температура чувствительного элемента спринклера (Tᵤ) [°C]', color='black')
            ax1.plot(time_cut, Tu_solution_cut[:, 0], label="Tᵤ", color='black', linewidth=3, linestyle='-')
            if self.x_mark_dTu is not None and self.y_mark_dTu is not None:
                ax1.scatter(self.x_mark_dTu, self.y_mark_dTu, color='blue', marker='o', s=150, zorder=5, label=f"Tᵤ = {self.Tu_i} °C\ntобн_инерц = {self.x_mark_dTu:.2f} сек")
                ax1.axhline(y=self.Tu_i, color='blue', linestyle='--', lw=1, label=f'Критическая темп. Tᵤ = {self.Tu_i:.2f} °C', alpha=0.7)
            ax1.tick_params(axis='y', labelcolor='black')
            ax1.tick_params(axis='x', colors='black')

            # Plot gas temperature on the right y-axis
            ax2 = ax1.twinx()
            ax2.set_ylabel('Температура газов (T) [°C]', color='red')
            ax2.plot(time_cut, temperatures_gas_cut, color='red', label="Температура газов")
            if self.critical_time_gas is not None:
                ax2.scatter(self.critical_time_gas, self.Tu_i, color='red', marker='x', s=150, zorder=5, label=f"T = {self.Tu_i} °C\ntпор = {self.critical_time_gas:.2f} сек")
                ax2.axhline(y=self.Tu_i, color='red', linestyle=':', lw=1, label=f'Пороговая темп. T = {self.Tu_i:.2f} °C', alpha=0.7)
            ax2.tick_params(axis='y', labelcolor='red')
            
            # X-axis label with dynamic calculation results (if available)
            tneh_f1 = "N/A"
            tneh_f2_f5 = "N/A"
            if self.critical_time_gas is not None and self.x_mark_dTu is not None:
                tneh_f1 = f"{self.critical_time_gas:.2f} + {self.x_mark_dTu:.2f} + 0 + 60 = {self.critical_time_gas + self.x_mark_dTu + 0 + 60:.2f}"
                tneh_f2_f5 = f"{self.critical_time_gas:.2f} + {self.x_mark_dTu:.2f} + 0 + 30 = {self.critical_time_gas + self.x_mark_dTu + 0 + 30:.2f}"
            ax1.set_xlabel(f'Время (с)\nДля Ф1: tн.э. = {tneh_f1}\nДля Ф2-Ф5: tн.э. = {tneh_f2_f5}', color='black')

            # Set border colors
            for spine in ax1.spines.values():
                spine.set_edgecolor('black')
            for spine in ax2.spines.values():
                spine.set_edgecolor('black')

            # Title and legend
            fig.suptitle("График прогрева термочувствительного элемента спринклера (Tᵤ) до температуры (T),\nсоответствующей порогу срабатывания (Tᵤᵢ)", color='black', y=0.95)
            lines, labels = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            legend = ax1.legend(lines + lines2, labels + labels2, loc='upper left', labelcolor='black', prop={'size': 9}) 
            plt.setp(legend.get_texts(), color='black')

            # Grid
            ax1.grid(True)

            # Save plot to buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            plt.close(fig) # Close the figure to free memory

            # Convert to QPixmap and display
            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue(), "PNG")
            self.plot_label.setPixmap(pixmap.scaled(self.plot_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.plot_pixmap = pixmap # Store for saving

        except Exception as e:
            QMessageBox.critical(self, "Ошибка построения графика", f"Не удалось построить график: {type(e).__name__}: {e}")
            self.statusBar.showMessage("Ошибка построения графика.")
            self.plot_label.setText("Ошибка при построении графика.")
            self.plot_pixmap = None # Clear stored pixmap

    def save_plot(self):
        if self.plot_pixmap is None:
            QMessageBox.warning(self, "Ошибка сохранения", "Нет графика для сохранения. Сначала выполните расчет.")
            self.statusBar.showMessage("Нет графика для сохранения.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить график", "dTu_plot.png", "PNG Image (*.png);;All Files (*)")
        if file_path:
            try:
                self.plot_pixmap.save(file_path, "PNG")
                self.statusBar.showMessage(f"График сохранён в {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка сохранения", f"Не удалось сохранить график: {e}")
                self.statusBar.showMessage("Ошибка сохранения графика.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Set application font
    app_font = QFont("Segoe UI", 10)
    app.setFont(app_font)
    
    window = SprinklerCalcApp()
    window.show()
    sys.exit(app.exec())