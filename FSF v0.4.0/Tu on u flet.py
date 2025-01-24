import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
import flet as ft
import io
import base64

# Используем не-GUI бэкенд для Matplotlib
plt.switch_backend('Agg')

# Функция, определяющая дифференциальное уравнение
def sprinkler_sensor_temp(Tu, t, T_func):
    T = T_func(t)   # T_func предоставляет значение T для данного t
    return np.sqrt(u_dynamic(T)) / K * (T - Tu)

# Модифицированная функция интерполяции для T, в зависимости от времени t
def gas_temperature(t):
    T = ((1 / Delta(t)) * (q(t) / (epsilon * sigma)) * np.exp(-(alpha * hu))) ** (1/4)
    return T

# Динамическая функция для вычисления `u` на основе формулы
def u_dynamic(T):
    return np.sqrt(2 * g * hu * (T / (Tu_0 + 273.15)))

def main(page: ft.Page):
    page.title = "Расчёт времени активации спринклера v0.1a"
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
        value="31.700",
        label_style=ft.TextStyle(size=24),
        hint_text="Низшая теплота сгорания, МДж/м\u00b2",
        tooltip="Низшая теплота сгорания горючего материала, МДж/м\u00b2",
        prefix_icon=ft.icons.EDIT_OUTLINED,
        prefix_text="* ",
        border_width=2,
    )
    v_input = ft.TextField(
        label="v",
        value="0.0068",
        label_style=ft.TextStyle(size=24),
        hint_text="Линейная скорость распространения пламени, м/с",
        tooltip="Линейная скорость распространения пламени, м/с\n\nСправочная величина, которая для может быть найдена в пожарно-технических справочниках или других специальных литературных источниках",
        prefix_icon=ft.icons.EDIT_OUTLINED,
        prefix_text="* ",
        border_width=2,
    )
    psi_yd_input = ft.TextField(
        label="\u03c8уд",
        value="0.0233",
        label_style=ft.TextStyle(size=24),
        hint_text="Удельная массовая скорость выгорания, кг/(с*м\u00b2)",
        tooltip="Удельная массовая скорость выгорания (для жидкостей установившаяся), кг/(с*м\u00b2)",
        prefix_icon=ft.icons.EDIT_OUTLINED,
        prefix_text="* ",
        border_width=2,
    )
    Cs_input = ft.TextField(
        label="Cs",
        value="0.425",
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
        hint_text="Высота помещения с очагом пожара, м",
        tooltip="Высота до потолка, м",
        prefix_icon=ft.icons.EDIT_OUTLINED,
        prefix_text="* ",
        border_width=2,
    )
    L_input = ft.TextField(
        label="L",
        value="4",
        label_style=ft.TextStyle(size=24),
        hint_text="Нормативное расстояние между спринклерами, м",
        tooltip="Противоположный катет, м",
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
        tooltip="k = 2 для Ф1-Ф4\nk = 4 для Ф5.2 при высоте хранения до 5.5м\nk = 10 для Ф5.2 при высоте хранения свыше 5.5м\nДля Ф5.1 k не вычисляется",
        prefix_icon=ft.icons.EDIT_OUTLINED,
        prefix_text="* ",
        border_width=2,
    )
    Tu_0_input = ft.TextField(
        label="Tu\u2080",
        value="24",
        label_style=ft.TextStyle(size=24),
        hint_text="Начальная температура чувствительного элемента спринклера, \u00b0C",
        tooltip="Начальная температура чувствительного элемента спринклера, \u00b0C",
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
        prefix_icon=ft.icons.EDIT_OFF_OUTLINED,
        prefix_text="= ",
        border_width=2,
    )
    angle_result = ft.TextField(
        label="angle",
        label_style=ft.TextStyle(size=24),
        read_only=True,
        prefix_icon=ft.icons.EDIT_OFF_OUTLINED,
        prefix_text="= ",
        border_width=2,
    )
    tmax_result = ft.TextField(
        label="tmax",
        label_style=ft.TextStyle(size=24),
        read_only=True,
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
        global Fpom, HRR, v, psi_yd, Cs, Hpom, L, epsilon, alpha, K, k, Tu_0, Tu_i, hu, angle, tmax, t_mod, q, phi, beta, Delta, sigma, g, x_mark
        try:
            Fpom = float(Fpom_input.value)
            HRR = float(HRR_input.value)
            v = float(v_input.value)
            psi_yd = float(psi_yd_input.value)
            Cs = float(Cs_input.value)
            Hpom = float(Hpom_input.value)
            L = float(L_input.value)
            epsilon = float(epsilon_input.value)
            #alpha = float(alpha_input.value)
            k = float(k_input.value)
            Tu_0 = float(Tu_0_input.value)
            Tu_i = float(Tu_i_input.value)

            # Вычисление K в зависимости от выбранного типа головки
            sprinkler_type = sprinkler_type_dropdown.value
            if sprinkler_type == "Стальная":
                K = np.sqrt((0.265 * 0.46) / 0.05)
            elif sprinkler_type == "Медная":
                K = np.sqrt((0.265 * 0.385) / 0.385)
            elif sprinkler_type == "Латунная":
                K = np.sqrt((0.265 * 0.375) / 0.11)
            else:
                K = 50  # Значение по умолчанию, если ничего не выбрано

            hu = Hpom - Cs
            angle = np.arctan(L / hu)
            tmax = np.sqrt((k * Fpom) / (np.pi * v**2))
            t_mod = tmax
            q = lambda t: HRR * psi_yd * np.pi * v**2 * t**2
            phi = lambda t: np.sqrt(1 + v**2 * t**2)
            beta = np.sqrt(1 + angle * (np.pi / 180))
            Delta = lambda t: np.arctan(phi(t)) * np.arctan(beta)
            sigma = 5.670374419e-8
            g = 9.81
            d = np.sqrt((4 * Fpom) / np.pi)
            alpha = 10e-4 * np.exp(-7 * 10e-4 * (L - 0.5*d))
            

            # Решение дифференциального уравнения для нахождения x_mark
            t_values = np.linspace(0, t_mod, 1000000)
            Tu_solution = odeint(sprinkler_sensor_temp, Tu_0, t_values, args=(gas_temperature,))

            x_mark = None
            for i in range(len(Tu_solution)):
                if Tu_solution[i, 0] >= Tu_i:
                    x_mark = t_values[i]
                    break

            # Обновление полей с результатами
            hu_result.value = f"{hu:.4f}"
            angle_result.value = f"{angle:.4f}"
            tmax_result.value = f"{tmax:.4f}"
            t_result.value = f"{x_mark:.2f}" if x_mark is not None else "N/A"
            alpha_input.value = f"{alpha:.7f}"

            calculate_button.color = "GREY400"
            calculate_button.update()

            generate_plot(e)

            page.update()

        except ValueError:
            snack_bar = ft.SnackBar(
                content=ft.Text(
                    "Пожалуйста, введите допустимые положительные числа в поля ввода!",
                    text_align=ft.TextAlign.CENTER,
                    size=18,
                    weight=ft.FontWeight.W_100,
                    selectable=True,
                    height="25"
                )
            )
            page.overlay.append(snack_bar)
            snack_bar.open = True
            page.update()

    def generate_plot(e):
        global x_mark

        t_values = np.linspace(0, t_mod, 1000000)
        Tu_solution = odeint(sprinkler_sensor_temp, Tu_0, t_values, args=(gas_temperature,))

        x_mark, y_mark = None, None
        cut_index = len(Tu_solution)

        for i in range(len(Tu_solution)):
            if Tu_solution[i, 0] >= Tu_i:
                x_mark = t_values[i]
                y_mark = Tu_solution[i, 0]
                cut_index = i
                break

        t_values_cut = t_values[:cut_index+1]
        Tu_solution_cut = Tu_solution[:cut_index+1]

        # Создание графика
        plt.figure(figsize=(10, 6))
        plt.plot(t_values_cut, Tu_solution_cut, label="dTu", color='black', linewidth=5, linestyle=':')

        if x_mark is not None and y_mark is not None:
            plt.scatter(x_mark, y_mark, color='red', marker='x', s=500, label=f"Tu = {Tu_i} °C \n  t = {x_mark:.2f} сек")
            print(f"Фрагмент значений при Tu={Tu_i} °C -> Время (t): {x_mark:.2f} сек, Температура (Tu): {y_mark:.2f} °C")

        plt.title("График времени прогрева термочувствительного элемента до температуры, \n соответствующей порогу срабатывания (Tu)")
        plt.xlabel("Время (t) [сек]")
        plt.ylabel("Температура чувствительного элемента спринклера (Tu) [°C]")
        plt.legend(loc='right')
        plt.grid()

        # Сохранение графика в объект BytesIO
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)

        # Преобразование графика в строку base64
        plot_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plot_image.src_base64 = plot_base64
        
        plot_image.update()

        # Закрытие графика для освобождения памяти
        plt.close()

        # Показ кнопки сохранения графика
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