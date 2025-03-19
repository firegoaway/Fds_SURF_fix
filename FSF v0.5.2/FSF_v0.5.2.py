import os
import re
import configparser
from math import sqrt, pi, ceil, floor
import flet as ft
import time
import asyncio
import sys

class FDSProcessorApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = f"FSF v0.5.2 ID:{ProcessID}"
        self.page.window.width = 400
        self.page.window.height = 780
        self.page.scroll = "auto"
        
        # Инициализация компонентов пользовательского интерфейса (GUI)
        self.k_entry = ft.TextField(
            label="k",
            label_style=ft.TextStyle(size=24),
            hint_text="Коэффициент k",
            tooltip="Коэффициент, учитывающий отличие фактической площади горючей нагрузки в помещении и площади помещения. Для помещений классов функциональной пожарной опасности Ф1 - Ф4 следует принимать равным 2",
            prefix_icon=ft.icons.EDIT_OUTLINED,  # Иконка "Edit"
            prefix_text="* ",  # Префикс
            #border_color=ft.colors.BLUE,  # Синяя граница
            border_width=2,  # Толще границы
        )
        self.fpom_entry = ft.TextField(
            label="Fпом",
            label_style=ft.TextStyle(size=24),
            hint_text="Площадь помещения с очагом пожара, м\u00b2",
            tooltip="Площадь помещения с очагом пожара, м\u00b2",
            prefix_icon=ft.icons.EDIT_OUTLINED,  # Иконка "Edit"
            prefix_text="* ",  # Префикс
            #border_color=ft.colors.BLUE,  # Синяя граница
            border_width=2,  # Толще границы
        )
        self.v_entry = ft.TextField(
            label="v",
            label_style=ft.TextStyle(size=24),
            hint_text="Линейная скорость распространения пламени, м/с",
            tooltip="Линейная скорость распространения пламени, м/с",
            prefix_icon=ft.icons.EDIT_OUTLINED,  # Иконка "Edit"
            prefix_text="* ",  # Префикс
            #border_color=ft.colors.BLUE,  # Синяя граница
            border_width=2,  # Толще границы
        )
        self.psyd_entry = ft.TextField(
            label="\u03c8уд",
            label_style=ft.TextStyle(size=24),
            hint_text="Удельная массовая скорость выгорания, кг/(с*м\u00b2)",
            tooltip="Удельная массовая скорость выгорания (для жидкостей установившаяся), кг/(с*м\u00b2)",
            prefix_icon=ft.icons.EDIT_OUTLINED,  # Иконка "Edit"
            prefix_text="* ",  # Префикс
            #border_color=ft.colors.BLUE,  # Синяя граница
            border_width=2,  # Толще границы
        )
        self.m_entry = ft.TextField(
            label="m",
            label_style=ft.TextStyle(size=24),
            hint_text="Полная масса сгораемой нагрузки, кг",
            tooltip="Полная масса сгораемой нагрузки (кг)\n\n0 - значение по умолчанию\n\nПри разработке компенсирующих мероприятий,\nнаправленных на сокращение горючей нагрузки в очаговой зоне,\nукажите это значение.\nОно должно быть меньше M при m = 0",
            prefix_icon=ft.icons.EDIT_OUTLINED,  # Иконка "Edit"
            prefix_text="* ",  # Префикс
            #border_color=ft.colors.BLUE,  # Синяя граница
            border_width=2,  # Толще границы
        )

        # Нередактируемые поля
        self.tmax_entry = ft.TextField(
            label="t\u2098\u2090\u2093",
            label_style=ft.TextStyle(size=24),
            hint_text="Время охвата пожаром всей поверхности, сек",
            read_only=True,
            tooltip="Время охвата пожаром всей поверхности горючей нагрузки в помещении, сек",
            prefix_icon=ft.icons.EDIT_OFF_OUTLINED,  # Иконка "Edit"
            prefix_text="= ",  # Префикс
            #border_color=ft.colors.ORANGE,  # Синие границы
            #border_width=2,  # Толще границы
        )
        self.psy_entry = ft.TextField(
            label="\u03a8",
            label_style=ft.TextStyle(size=24),
            hint_text="Зависимость скорости выгорания от времени, кг/с",
            read_only=True,
            tooltip="Зависимость скорости выгорания от времени, (кг/с)",
            prefix_icon=ft.icons.EDIT_OFF_OUTLINED,  # Иконка "Edit"
            prefix_text="= ",  # Префикс
            #border_color=ft.colors.ORANGE,  # Синие границы
            #border_width=2,  # Толще границы
        )
        self.hrr_entry = ft.TextField(
            label="Q",
            label_style=ft.TextStyle(size=24),
            hint_text="Полная тепловая мощность очага пожара, кДж",
            read_only=True,
            tooltip="Полная тепловая мощность очага пожара, кДж",
            prefix_icon=ft.icons.EDIT_OFF_OUTLINED,  # Иконка "Edit"
            prefix_text="= ",  # Префикс
            #border_color=ft.colors.ORANGE,  # Синие границы
            #border_width=2,  # Толще границы
        )
        self.stt_entry = ft.TextField(
            label="Stt",
            hint_text="Площадь поверхности горючей нагрузки, м\u00b2",
            read_only=True,
            tooltip=f"Площадь поверхности горючей нагрузки в помещении, охватываемая пожаром за время t\u2098\u2090\u2093, м\u00b2",
            prefix_icon=ft.icons.EDIT_OFF_OUTLINED,  # Иконка "Edit"
            prefix_text="= ",  # Префикс
            #border_color=ft.colors.ORANGE,  # Синие границы
            #border_width=2,  # Толще границы
        )
        self.bigM_entry = ft.TextField(
            label="M",
            hint_text="Полная масса горючей нагрузки, кг",
            read_only=True,
            tooltip="Полная масса горючей нагрузки (кг), охваченной пожаром за время tmax",
            prefix_icon=ft.icons.EDIT_OFF_OUTLINED,  # Иконка "Edit"
            prefix_text="= ",  # Префикс
            #border_color=ft.colors.ORANGE,  # Синие границы
            #border_width=2,  # Толще границы
        )

        # Кнопки
        self.calculate_button = ft.ElevatedButton(
            text="Рассчитать",
            on_click=self.calculate,
            style=ft.ButtonStyle(
                padding=ft.padding.symmetric(horizontal=25, vertical=20),
                shape=ft.RoundedRectangleBorder(radius=8),
                text_style=ft.TextStyle(
                    size=15.0 # Здесь хранится размер шрифта
                )
            )
        )

        self.process_button = ft.ElevatedButton(
            text="Сохранить",
            disabled=True,
            on_click=self.process_files,
            style=ft.ButtonStyle(
                padding=ft.padding.symmetric(horizontal=25, vertical=20),
                shape=ft.RoundedRectangleBorder(radius=8),
                text_style=ft.TextStyle(
                    size=15.0  # Здесь хранится размер шрифта
                )
            )
        )
        
        # Кнопочный ряд
        button_row = ft.Row(
            controls=[
                self.calculate_button,  # Кнопка "Рассчитать" слева
                ft.Container(width=20),  # Горизонтальный интервал для кнопки справа
                self.process_button,  # Кнопка "Сохранить" справа
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,  # Пробел между кнопками
        )

        # Вертикальный интервал между кнопками
        button_container = ft.Column(
            controls=[
                ft.Container(height=20),  # Добавляем вертикальный отступ (20 пикселей)
                button_row,  # Включаем button_row в паттерн
            ],
        )
        
        # Добавляем заголовки
        input_heading = ft.Row(
            controls=[
                ft.Text(
                    text_align=ft.TextAlign.CENTER,
                    value="Введите значения переменных",
                    size=18,
                    weight=ft.FontWeight.W_100,
                    selectable=True
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER
        )

        result_heading = ft.Row(
            controls=[
                ft.Text(
                    text_align=ft.TextAlign.CENTER,
                    value="Результат",
                    size=18,
                    weight=ft.FontWeight.W_100,
                    selectable=True
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER
        )
        
        # Добавляем компоненты в GUI
        self.page.add(
            input_heading,
            self.k_entry,
            self.fpom_entry,
            self.v_entry,
            self.psyd_entry,
            self.m_entry,
            result_heading,
            self.tmax_entry,
            self.psy_entry,
            self.hrr_entry,
            self.stt_entry,
            self.bigM_entry,
            button_container,
        )

        # Загружаем информацию из INI файла
        self.load_from_ini()

    def load_from_ini(self):
        current_directory = os.path.dirname(__file__)
        parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
        inis_path = os.path.join(parent_directory, 'inis')
        ini_file = os.path.join(inis_path, 'IniApendix1.ini')

        if os.path.exists(ini_file):
            config = configparser.ConfigParser()
            config.read(ini_file)
            try:
                self.k_entry.value = config['Calculations']['k']
                self.fpom_entry.value = config['Calculations']['Fpom']
                self.v_entry.value = config['Calculations']['v']
                self.psyd_entry.value = config['Calculations']['psi_ud']
                self.m_entry.value = "0.0"  # Default value
                #self.tmax_entry.value = config['Calculations']['tmax']
                #self.psy_entry.value = config['Calculations']['Psi']
                #self.stt_entry.value = config['Calculations']['Stt']
                #self.bigM_entry.value = config['Calculations']['bigM']
            except KeyError as e:
                self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Значения не найдены: {e}"))
                self.page.snack_bar.open = True
                self.page.update()
            
            # Обновляем GUI, чтобы отразить загруженные значения
            self.page.update()

    def calculate(self, e):
        current_directory = os.path.dirname(__file__)
        parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
        inis_path = os.path.join(parent_directory, 'inis')

        ini_path = os.path.join(inis_path, f'filePath_{ProcessID}.ini')
        ini_path_hoc = os.path.join(inis_path, f'HOC_{ProcessID}.ini')
        
        try:
            # Парсим входные переменные
            k = float(self.k_entry.value)
            Fpom = float(self.fpom_entry.value)
            v = float(self.v_entry.value)
            psi_ud = float(self.psyd_entry.value)
            m = float(self.m_entry.value)

            # Производим вычисления
            tmax = sqrt((k * Fpom) / (pi * v**2))
            Psi = psi_ud * pi * v**2 * tmax**2
            Stt = pi * (v * tmax)**2
            
            HEAT_OF_COMBUSTION = int(self.read_ini_file_HOC(ini_path_hoc))
            Hc = HEAT_OF_COMBUSTION / 1000

            if m > 0:
                bigM = Psi * tmax
                Psi = m / tmax
                bigM = m
                HRRPUA = Hc * Psi * 0.93 * 1000
            else:
                bigM = Psi * tmax
                Psi = 0.3 * (1 / k) * (bigM / tmax)
                HRRPUA = Hc * Psi * 0.93 * 1000
            
            """
            D = (HRRPUA / (1.204 * 1.005 * 38 * sqrt(9.81))) ** (2/5)
            dx16 = D / 16
            dx10 = D / 10
            dx4 = D / 4
            
            trecmod = tmax / ((16 / D) ** -(5/2))

            # Отобразить уведомление в графическом интерфейсе с рекомендуемым Cs
            snack_bar = ft.SnackBar(
                content=ft.Text(
                    f"Минимальный размер ячейки = {dx16:.2f}\n"
                    f"Допустимый размер ячейки = {dx10:.2f}\n"
                    f"Максимальный размер ячейки = {dx4:.2f}\n"
                    f"Критическое время моделирования = {trecmod:.0f} сек\n"
                ),
                action="OK",
                action_color=ft.colors.GREEN,
                duration=3000,  # Показываем уведомление 3 секунды
            )
            self.page.overlay.append(snack_bar)
            snack_bar.open = True
            """

            # Обновляем нередактируемые поля вычисленными значениями
            self.tmax_entry.value = f"{tmax:.4f}"
            self.psy_entry.value = f"{Psi:.4f}"
            self.hrr_entry.value = f"{HRRPUA:.4f}"
            self.stt_entry.value = f"{Stt:.4f}"
            self.bigM_entry.value = f"{bigM:.4f}"

            # Обновляем tooltip для self.stt_entry
            self.stt_entry.tooltip = f"Площадь поверхности горючей нагрузки в помещении, охватываемая пожаром за время t\u2098\u2090\u2093 = {tmax:.4f} м\u00b2"

            # Активируем кнопку "Сохранить"
            self.process_button.disabled = False

            # Обновляем GUI
            self.page.update()

        except ValueError as ve:
            snack_bar = ft.SnackBar(content=ft.Text(f"Ошибка ввода: {ve}"))
            self.page.overlay.append(snack_bar)
            snack_bar.open = True
            self.page.update()
        except Exception as ex:
            snack_bar = ft.SnackBar(content=ft.Text(f"Произошла ошибка: {ex}"))
            self.page.overlay.append(snack_bar)
            snack_bar.open = True
            self.page.update()

        except ValueError as ve:
            snack_bar = ft.SnackBar(content=ft.Text(f"Ошибка ввода: {ve}"))
            self.page.overlay.append(snack_bar)
            snack_bar.open = True
            self.page.update()
        except Exception as ex:
            snack_bar = ft.SnackBar(content=ft.Text(f"Произошла ошибка: {ex}"))
            self.page.overlay.append(snack_bar)
            snack_bar.open = True
            self.page.update()

    def save_to_ini(self, k, Fpom, v, psi_ud, m, tmax, Psi, Stt, bigM, HRRPUA):
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

        with open(ini_file, 'w') as configfile:
            config.write(configfile)

    def process_files(self, e):
        # Собираем введенные и рассчитанные переменные
        k = self.k_entry.value
        Fpom = self.fpom_entry.value
        v = self.v_entry.value
        psi_ud = self.psyd_entry.value
        m = self.m_entry.value
        tmax = self.tmax_entry.value
        Psi = self.psy_entry.value
        Stt = self.stt_entry.value
        bigM = self.bigM_entry.value
        HRRPUA = self.hrr_entry.value

        # Сохраняем в INI
        self.save_to_ini(k, Fpom, v, psi_ud, m, tmax, Psi, Stt, bigM, HRRPUA)
        
        current_directory = os.path.dirname(__file__)
        parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
        inis_path = os.path.join(parent_directory, 'inis')

        ini_path = os.path.join(inis_path, f'filePath_{ProcessID}.ini')
        ini_path_hoc = os.path.join(inis_path, f'HOC_{ProcessID}.ini')

        try:
            HEAT_OF_COMBUSTION = int(self.read_ini_file_HOC(ini_path_hoc))
            Hc = HEAT_OF_COMBUSTION / 1000
            v = float(self.v_entry.value)
            m = float(self.m_entry.value)
            Fpom = float(self.fpom_entry.value)
            TAU_Q = -float(self.tmax_entry.value)

            fds_path = self.read_ini_file(ini_path)

            if m > 0:
                MLRPUA = m / -TAU_Q
            else:
                MLRPUA = float(self.psy_entry.value)
            
            HRRPUA = Hc * MLRPUA * 0.93 * 1000
            
            if not MLRPUA or not TAU_Q:
                raise ValueError("Поля не должны быть пустыми")
            
            self.process_fds_file(fds_path, HRRPUA, TAU_Q)
            snack_bar = ft.SnackBar(content=ft.Text(f"Модифицированный .fds файл сохранён:\n\n{fds_path.replace('.fds', '.fds')}"))
            self.page.overlay.append(snack_bar)
            snack_bar.open = True
            self.page.update()
            
            # Планируем закрытие с помощью close_window coroutine
            async def close_window():
                await asyncio.sleep(1)  # Ждём 1 секунду
                self.page.window.close()  # Закрываем окно
            
            self.process_button.color = "GREY400"
            self.process_button.update()
            
            # Запускаем сопрограмму в цикле обработки событий
            self.page.run_task(close_window)
        
        except Exception as e:
            snack_bar = ft.SnackBar(content=ft.Text(str(e)))
            self.page.overlay.append(snack_bar)
            snack_bar.open = True
            self.page.update()
    
    def read_ini_file(self, ini_file):
        config = configparser.ConfigParser()
        with open(ini_file, 'r', encoding='utf-16') as f:
            config.read_file(f)
        return config['filePath']['filePath']
    
    def read_ini_file_HOC(self, ini_file):
        config = configparser.ConfigParser()
        with open(ini_file, 'r', encoding='utf-16') as f:
            config.read_file(f)
        return config['HEAT_OF_COMBUSTION']['HEAT_OF_COMBUSTION']
    
    def process_fds_file(self, fds_path, HRRPUA, TAU_Q):
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
                    v = float(self.v_entry.value)

                    if 'HRRPUA' in line:
                        hrrpua_found = True
                        inside_surf_block = True
                        modified_lines.append(f"&SURF ID='{surf_id}', ")
                        modified_lines.append(f"HRRPUA={HRRPUA}, ")
                        modified_lines.append(f"COLOR='RED', ")
                        modified_lines.append(f"TAU_Q={TAU_Q}/\n")
                    else:
                        hrrpua_found = False
                        modified_lines.append(line)
                    continue

                if inside_surf_block and hrrpua_found:
                    if line.startswith('&VENT'):
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


if __name__ == "__main__":
    if len(sys.argv) > 1:
        ProcessID = int(sys.argv[1])
        print(f"Process ID received from AHK: {ProcessID}")
    else:
        print("No Process ID received.")
    
    ft.app(target=FDSProcessorApp, view=ft.AppView.FLET_APP)
    