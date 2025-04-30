import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
import flet as ft
import io
import base64
import random

# Используем не-GUI бэкенд для Matplotlib
plt.switch_backend('Agg')

temperatures_gas = []
critical_time_gas = None
Tu_solution = []
x_mark_dTu = None
y_mark_dTu = None

# Функция, определяющая дифференциальное уравнение
def sprinkler_sensor_temp(Tu, t, T_func):
    T = T_func(t)   # T_func предоставляет значение T для данного t
    if T < Tu_0:
        return 0  # Tu растёт только если T >= Tu_0
    return np.sqrt(u_dynamic(T)) / K * (T - Tu)

# Модифицированная функция интерполяции для T, в зависимости от времени t
def gas_temperature(t):
    T = ((1 / Delta(t)) * (q(t) / (epsilon * sigma)) * np.exp(-(alpha * hu))) ** (1/4)
    return max(T, Tu_0)  # Чтобы T не падал ниже Tu_0

# Динамическая функция для вычисления `u` на основе формулы
def u_dynamic(T):
    return np.sqrt(2 * g * hu * (T / (Tu_0+273.15)))

def main(page: ft.Page):
    page.title = "Расчёт времени активации спринклера v0.5.2"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window.width = 1280
    page.window.height = 720
    page.scroll = "auto"
    
    # Заголовки
    main_heading = ft.Row(
        controls=[
            ft.Text(
                text_align=ft.TextAlign.CENTER,
                value="Расчёт времени задержки, связанного с инерционностью АУПТ",
                size=24,
                weight=ft.FontWeight.W_100,
                selectable=True,
                height="50"
            )
        ],
        alignment=ft.MainAxisAlignment.CENTER
    )
    input_heading = ft.Row(
        controls=[
            ft.Text(
                text_align=ft.TextAlign.LEFT,
                value="Введите значения\nпеременных",
                size=16,
                weight=ft.FontWeight.W_100,
                selectable=True,
                height="50"
            )
        ],
        alignment=ft.MainAxisAlignment.START
    )
    result_heading = ft.Row(
        controls=[
            ft.Text(
                text_align=ft.TextAlign.CENTER,
                value="Результаты",
                size=18,
                weight=ft.FontWeight.W_100,
                selectable=True,
                height="50"
            )
        ],
        alignment=ft.MainAxisAlignment.CENTER
    )

    # Поля ввода для параметров
    Fpom_input = ft.TextField(
        label="Fpom",
        value="500",
        label_style=ft.TextStyle(size=24),
        hint_text="Площадь помещения с очагом пожара, м\u00b2",
        tooltip="Площадь помещения с очагом пожара, м\u00b2",
        prefix_icon=ft.icons.EDIT_OUTLINED,
        prefix_text="* ",
        border_width=2,
    )
    HRR_input = ft.TextField(
        label="HRR",
        value="13.800",
        label_style=ft.TextStyle(size=24),
        hint_text="Низшая теплота сгорания, МДж/м\u00b2",
        tooltip="Низшая теплота сгорания горючего материала, МДж/м\u00b2",
        prefix_icon=ft.icons.EDIT_OUTLINED,
        prefix_text="* ",
        border_width=2,
    )
    v_input = ft.TextField(
        label="v",
        value="0.0055",
        label_style=ft.TextStyle(size=24),
        hint_text="Линейная скорость распространения пламени, м/с",
        tooltip="Линейная скорость распространения пламени, м/с\n\nСправочная величина, которая для может быть найдена в пожарно-технических справочниках или других специальных литературных источниках",
        prefix_icon=ft.icons.EDIT_OUTLINED,
        prefix_text="* ",
        border_width=2,
    )
    psi_yd_input = ft.TextField(
        label="\u03c8уд",
        value="0.015",
        label_style=ft.TextStyle(size=24),
        hint_text="Удельная массовая скорость выгорания, кг/(с*м\u00b2)",
        tooltip="Удельная массовая скорость выгорания (для жидкостей установившаяся), кг/(с*м\u00b2)",
        prefix_icon=ft.icons.EDIT_OUTLINED,
        prefix_text="* ",
        border_width=2,
    )
    Cs_input = ft.TextField(
        label="Cs",
        value="0.1",
        label_style=ft.TextStyle(size=24),
        hint_text="Размер ячейки, м",
        tooltip="Размер ячейки, м",
        prefix_icon=ft.icons.EDIT_OUTLINED,
        prefix_text="* ",
        border_width=2,
    )
    Hpom_input = ft.TextField(
        label="Hпом",
        value="3",
        label_style=ft.TextStyle(size=24),
        hint_text="Высота помещения, м",
        tooltip="Высота помещения с очагом пожара (высота до потолка), м",
        prefix_icon=ft.icons.EDIT_OUTLINED,
        prefix_text="* ",
        border_width=2,
    )
    L_input = ft.TextField(
        label="L",
        value="4",
        label_style=ft.TextStyle(size=24),
        hint_text="Нормативное расстояние между спринклерами, м",
        tooltip="Нормативное расстояние между спринклерами, м.\nПротивоположный катет.",
        prefix_icon=ft.icons.EDIT_OUTLINED,
        prefix_text="* ",
        border_width=2,
    )
    epsilon_input = ft.TextField(
        label="\u03b5",
        value="0.85",
        label_style=ft.TextStyle(size=24),
        hint_text="Коэффициент облучённости",
        tooltip="Эмиссивность материала горючей нагрузки",
        prefix_icon=ft.icons.EDIT_OUTLINED,
        prefix_text="* ",
        border_width=2,
    )
    # Dropdown для выбора типа головки спринклера
    sprinkler_type_dropdown = ft.Dropdown(
        label="Головка",
        options=[
            ft.dropdown.Option("Стальная"),
            ft.dropdown.Option("Медная"),
            ft.dropdown.Option("Латунная"),
        ],
        value="Стальная головка",  # Значение по умолчанию
        label_style=ft.TextStyle(size=18),
        prefix_icon=ft.icons.EDIT_OUTLINED,
        prefix_text="* ",
        border_width=2,
    )
    k_input = ft.TextField(
        label="k",
        value="2",
        label_style=ft.TextStyle(size=24),
        hint_text="Коэффициент, описывающий отношение поверхности горючей нагрузки к площади помещения",
        tooltip="k = 2 для Ф1-Ф4\nk = 4 для Ф5.2 при высоте хранения до 5.5м\nk = 10 для Ф5.2 при высоте хранения свыше 5.5м\nНе вычисляется для Ф5.1",
        prefix_icon=ft.icons.EDIT_OUTLINED,
        prefix_text="* ",
        border_width=2,
    )
    Tu_0_input = ft.TextField(
        label="Tu\u2080",
        value="24",
        label_style=ft.TextStyle(size=24),
        hint_text="Максимально возможная в течение года температура, \u00b0C",
        tooltip="Максимально возможная в течение года температура,\nона же - начальная температура чувствительного элемента спринклера, \u00b0C",
        prefix_icon=ft.icons.EDIT_OUTLINED,
        prefix_text="* ",
        border_width=2,
    )
    Tu_i_input = ft.TextField(
        label="Tu\u1d62",
        value="57",
        label_style=ft.TextStyle(size=24),
        hint_text="Критическая температура чувствительного элемента спринклера, \u00b0C",
        tooltip="Критическая температура чувствительного элемента спринклера, \u00b0C",
        prefix_icon=ft.icons.EDIT_OUTLINED,
        prefix_text="* ",
        border_width=2,
    )

    # Поля для отображения результатов
    alpha_input = ft.TextField(
        label="\u03b1",
        label_style=ft.TextStyle(size=24),
        read_only=True,
        hint_text="Коэффициент пропускания атмосферы",
        tooltip="Оптическая толщина атмосферы (коэффициент пропускания атмосферы).\nРассчитывается эмпирическим путём (см. Методику 533).",
        prefix_icon=ft.icons.EDIT_OFF_OUTLINED,
        prefix_text="= ",
        border_width=2,
    )
    hu_result = ft.TextField(
        label="hu",
        label_style=ft.TextStyle(size=24),
        read_only=True,
        hint_text="Высота (м)",
        tooltip="Высота расположения термочувствительного элемента спринклера (м)",
        prefix_icon=ft.icons.EDIT_OFF_OUTLINED,
        prefix_text="= ",
        border_width=2,
    )
    angle_result = ft.TextField(
        label="angle",
        label_style=ft.TextStyle(size=24),
        read_only=True,
        hint_text="Угловой коэффициент теплового переноса",
        tooltip="Угловой коэффициент теплового переноса",
        prefix_icon=ft.icons.EDIT_OFF_OUTLINED,
        prefix_text="= ",
        border_width=2,
    )
    tmax_result = ft.TextField(
        label="tmax",
        label_style=ft.TextStyle(size=24),
        read_only=True,
        hint_text="Время охвата пожаром всей поверхности горючей нагрузки в помещении (сек)",
        tooltip="Время охвата пожаром всей поверхности горючей нагрузки в помещении (сек)",
        prefix_icon=ft.icons.EDIT_OFF_OUTLINED,
        prefix_text="= ",
        border_width=2,
    )
    t_mod_result = ft.TextField(
        label="t_mod",
        label_style=ft.TextStyle(size=24),
        read_only=True,
        prefix_icon=ft.icons.EDIT_OFF_OUTLINED,
        prefix_text="= ",
        border_width=2,
    )
    t_result = ft.TextField(
        label="tобн_инерц",
        label_style=ft.TextStyle(size=24),
        read_only=True,
        hint_text="Время задержки, связанное с инерционностью АУПТ (сек)",
        tooltip="Время задержки, связанное с инерционностью АУПТ (сек)",
        prefix_icon=ft.icons.EDIT_OFF_OUTLINED,
        prefix_text="= ",
        border_width=2,
    )
    tT_result = ft.TextField(
        label="tпор",
        label_style=ft.TextStyle(size=24),
        read_only=True,
        hint_text="Время достижения порогового значения срабатывания АУПТ (сек)",
        tooltip="Время достижения порогового значения срабатывания АУПТ (сек)",
        prefix_icon=ft.icons.EDIT_OFF_OUTLINED,
        prefix_text="= ",
        border_width=2,
    )

    # Виджет для отображения графика
    plot_image = ft.Image(src_base64=None, width=800, height=600)

    # FilePicker для сохранения графика
    save_file_dialog = ft.FilePicker()
    page.overlay.append(save_file_dialog)
    page.update()

    # Глобальная переменная для x_mark
    global x_mark
    x_mark = None

    def calculate(e):
        global time, Fpom, HRR, v, psi_yd, Cs, Hpom, L, epsilon, alpha, K, k, Tu_0, Tu_i, hu, angle, tmax, t_mod, q, phi, beta, Delta, sigma, g, x_mark, temperatures_gas, critical_time_gas, Tu_solution, x_mark_dTu, y_mark_dTu
        
        try:
            Fpom = float(Fpom_input.value)
            HRR = float(HRR_input.value)
            v = float(v_input.value)
            psi_yd = float(psi_yd_input.value)
            Cs = float(Cs_input.value)
            Hpom = float(Hpom_input.value)
            L = float(L_input.value)
            epsilon = float(epsilon_input.value)
            k = float(k_input.value)
            Tu_0 = float(Tu_0_input.value)
            Tu_i = float(Tu_i_input.value)
            T_ambient = Tu_0

            # Выбор материала спринклера
            if sprinkler_type_dropdown.value == "Стальная":
                K = np.sqrt((0.265 * 0.46) / 0.05)
            elif sprinkler_type_dropdown.value == "Медная":
                K = np.sqrt((0.265 * 0.385) / 0.385)
            elif sprinkler_type_dropdown.value == "Латунная":
                K = np.sqrt((0.265 * 0.375) / 0.11)
            else:
                K = 50

            hu = Hpom - Cs
            angle = np.arctan(L / hu)
            tmax = np.sqrt((k * Fpom) / (np.pi * v**2))
            t_mod = tmax
            q = lambda t: HRR * psi_yd * np.pi * v**2 * t**2 if t < tmax else HRR * psi_yd * np.pi * v**2 * tmax**2
            phi = lambda t: np.sqrt(1 + v**2 * t**2)
            beta = np.sqrt(1 + angle * (np.pi / 180))
            Delta = lambda t: np.arctan(phi(t)) * np.arctan(beta)
            sigma = 5.670374419e-8
            g = 9.81
            d = np.sqrt((4 * Fpom) / np.pi)
            alpha = 10e-4 * np.exp(-7 * 10e-4 * (L - 0.5*d))

            rho = 1.2   # Плотность воздуха (кг/м³)
            cp = 1.005  # Удельная теплоёмкость воздуха (кДж/(кг·K))
            z = hu  # Высота до спринклера (м)

            def Psi(t):
                return q(t)

            def heat_release_rate(t):
                return Psi(t) * 1000 * 0.93

            def temperature_rise(Q):
                return Q**(7/4) / (rho * cp * np.sqrt(g) * L**2 * z**(5/3))

            # Временной порог вычислений
            time = np.linspace(0, tmax, 10**6)

            # Находим температуру газов
            temperatures_gas = [T_ambient + temperature_rise(heat_release_rate(t)) for t in time]

            # Находим критическую температуру на момент времени
            critical_time_gas = next((t for t, temp in zip(time, temperatures_gas) if temp >= Tu_i), None)

            # Интеграл
            Tu_solution = odeint(
                sprinkler_sensor_temp,
                Tu_0,
                time,
                args=(gas_temperature,)
            )
            
            x_mark_dTu, y_mark_dTu = None, None
            for i in range(len(Tu_solution)):
                if Tu_solution[i, 0] >= Tu_i:
                    x_mark_dTu = time[i]
                    y_mark_dTu = Tu_solution[i, 0]
                    break

            # Обновляем результаты в интерфейса
            hu_result.value = f"{hu:.4f}"
            angle_result.value = f"{angle:.4f}"
            tmax_result.value = f"{tmax:.4f}"
            t_result.value = f"{x_mark_dTu:.2f}" if x_mark_dTu is not None else "N/A"
            tT_result.value = f"{critical_time_gas:.2f}" if critical_time_gas is not None else "N/A"
            alpha_input.value = f"{alpha:.7f}"

            calculate_button.color = "GREY400"
            calculate_button.update()
            
            page.update()

            generate_plot(e)

        except ValueError:
            snack_bar = ft.SnackBar(
                content=ft.Text("Пожалуйста, введите допустимые положительные числа в поля ввода!", text_align=ft.TextAlign.CENTER, size=18, weight=ft.FontWeight.W_100, selectable=True, height="25")
            )
            page.overlay.append(snack_bar)
            snack_bar.open = True
            page.update()

    def generate_plot(e):
        global temperatures_gas, critical_time_gas, Tu_solution, x_mark_dTu, y_mark_dTu, time

        # Определяем участок среза графиков исходя из критических температур
        cut_time = max(critical_time_gas or 0, x_mark_dTu or 0) + random.randrange(int(Tu_0), int(Tu_i), 2)
        cut_index = np.searchsorted(time, cut_time)

        # Режем
        time_cut = time[:cut_index]
        temperatures_gas_cut = temperatures_gas[:cut_index]
        Tu_solution_cut = Tu_solution[:cut_index]

        # Двойная ордината
        fig, ax1 = plt.subplots(figsize=(10, 6))

        # Рисуем dTu на левой ординате
        ax1.set_ylabel('Температура чувствительного элемента спринклера (dTu) [°C]', color='black')
        ax1.plot(time_cut, Tu_solution_cut[:, 0], label="dTu", color='black', linewidth=5, linestyle=':')
        if x_mark_dTu is not None and y_mark_dTu is not None:
            ax1.scatter(x_mark_dTu, y_mark_dTu, color='red', marker='x', s=200, label=f"dTu = {Tu_i} °C\ntобн_инерц = {x_mark_dTu:.2f} сек")
        ax1.tick_params(axis='y', labelcolor='black')
        ax1.tick_params(axis='x', colors='black')

        # Рисуем температуру газа на правой ординате
        ax2 = ax1.twinx()
        ax2.set_ylabel('Температура газов [°C]', color='red')
        ax2.plot(time_cut, temperatures_gas_cut, color='red', label="Температура газов")
        if critical_time_gas is not None:
            ax2.scatter(critical_time_gas, Tu_i, color='red', marker='o', s=100, label=f"tпор = {critical_time_gas:.2f} сек")
        ax2.tick_params(axis='y', labelcolor='red')
        
        ax1.set_xlabel(f'Время (с)\nДля Ф1: tнэ = {critical_time_gas:.2f} + {x_mark_dTu:.2f} + 0 + 60 = {critical_time_gas + x_mark_dTu + 0 + 60:.2f}\nДля Ф2-Ф5: tнэ = {critical_time_gas:.2f} + {x_mark_dTu:.2f} + 0 + 30 = {critical_time_gas + x_mark_dTu + 0 + 30:.2f}', color='black')

        # Границы красим в чёрный цвет
        for spine in ax1.spines.values():
            spine.set_edgecolor('black')

        for spine in ax2.spines.values():
            spine.set_edgecolor('black')

        # Добавляем горизонтальные линии для L и input_threshold на соответствующих осях
        ax1.axhline(y=y_mark_dTu, color='black', linestyle=(0, (1, 5)), lw=2, label=f'Темп. колб. = {critical_time_gas:.2f} (°C)', alpha=0.5)
        ax2.axhline(y=y_mark_dTu, color='red', linestyle=(0, (1, 5)), lw=2, label=f'Темп. газ. = {y_mark_dTu:.2f} (°C)', alpha=0.5)

        # Заголовок и легенда
        fig.suptitle("График прогрева термочувствительного элемента спринклера (dTu) до температуры (T),\nсоответствующей порогу срабатывания (Tu)", color='black', y=0.95)
        lines, labels = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        legend = ax1.legend(lines + lines2, labels + labels2, loc='center left', labelcolor='black', prop={'size': 8})
        plt.setp(legend.get_texts(), color='black')

        # Сеточка
        ax1.grid(True)

        # Храним изображение графика в памяти для отображение в Flet
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plot_base64_combined = base64.b64encode(buf.read()).decode('utf-8')

        # Обновляем изображение графика в интерфейсе
        plot_image.src_base64 = plot_base64_combined
        plot_image.update()

        # После расчёта кнопка "Сохранить" становится активна
        save_plot_button.disabled = False
        page.update()

    def save_plot(e):
        # Запрос у пользователя выбора папки и имени файла
        save_file_dialog.save_file(
            allowed_extensions=["png"],
            file_name="dTu_plot.png"
        )
        save_plot_button.color = "GREY400"
        save_plot_button.update()

    def on_save_file_result(e: ft.FilePickerResultEvent):
        if e.path:
            # Сохранение графика по выбранному пути
            with open(e.path, "wb") as f:
                f.write(base64.b64decode(plot_image.src_base64))
            print(f"График сохранён в {e.path}")

            # Закрытие окна приложения
            page.window.close()

    # Кнопки
    calculate_button = ft.ElevatedButton(
        text="Рассчитать",
        on_click=calculate,
        style=ft.ButtonStyle(
            padding=ft.padding.symmetric(horizontal=25, vertical=20),
            shape=ft.RoundedRectangleBorder(radius=8),
            text_style=ft.TextStyle(
                size=15.0
            )
        )
    )
    save_plot_button = ft.ElevatedButton(
        text="Сохранить изображение графика",
        on_click=save_plot,
        disabled=True,
        style=ft.ButtonStyle(
            padding=ft.padding.symmetric(horizontal=25, vertical=20),
            shape=ft.RoundedRectangleBorder(radius=8),
            text_style=ft.TextStyle(
                size=15.0
            )
        )
    )
    
    # Размещаем кнопки в ряд
    button_row = ft.Row(
        controls=[
            calculate_button,
            save_plot_button,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=50,
    )

    # Основной макет
    main_layout = ft.Row(
        controls=[
            # Левая колонка: Поля ввода
            ft.Column(
                controls=[
                    input_heading,
                    Fpom_input,
                    HRR_input,
                    v_input,
                    psi_yd_input,
                    Cs_input,
                    Hpom_input,
                    L_input,
                    epsilon_input,
                    #alpha_input,
                    sprinkler_type_dropdown,  # Добавлен Dropdown для выбора типа головки
                    k_input,
                    Tu_0_input,
                    Tu_i_input,
                ],
                alignment=ft.MainAxisAlignment.START,
                scroll=ft.ScrollMode.AUTO,
                width=150,
            ),
            # Центральная колонка: График
            ft.Column(
                controls=[
                    main_heading,
                    plot_image, 
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            ),
            # Правая колонка: Результаты
            ft.Column(
                controls=[
                    result_heading,
                    alpha_input,
                    hu_result,
                    angle_result,
                    tmax_result,
                    t_result,
                    tT_result,
                ],
                alignment=ft.MainAxisAlignment.START,
                width=200,
            ),
        ],
        expand=True,
    )

    # Основной контейнер с кнопками внизу
    page.add(
        main_layout,
        ft.Container(height=20),  # Вертикальный отступ выше
        button_row,
        ft.Container(height=50),  # Вертикальный отступ ниже
    )

    # Настройка обработчика событий FilePicker
    save_file_dialog.on_result = on_save_file_result

ft.app(target=main)