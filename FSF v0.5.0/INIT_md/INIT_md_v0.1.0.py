import configparser
import re
import os
import glob
import threading
import time
import flet as ft
import plotly.graph_objects as go
import csv
import sys
import psutil

tracking_active = False
tracking_thread = None

def extract_chid_from_fds(filePath):
    try:
        with open(filePath, 'r', encoding='utf-8') as file:
            for line in file:
                if line.strip().startswith("&HEAD") and "CHID=" in line:
                    match = re.search(r"CHID\s*=\s*['\"]?([^'\"]+)['\"]?", line)
                    if match:
                        chid = match.group(1).strip()
                        print(f"Extracted CHID: {chid}")
                        return chid
        raise ValueError("CHID not found in the .fds file.")
    except Exception as e:
        print(f"Error extracting CHID: {e}")
        sys.exit(1)

def modify_fds_file(page):
    global tracking_active, tracking_thread

    page.title = "Расчёт СПДЗ"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window.width = 880
    page.window.height = 640
    page.scroll = "auto"

    def read_ini_filePath(ini_file):
        try:
            config = configparser.ConfigParser()
            with open(ini_file, 'r', encoding='utf-16') as f:
                config.read_file(f)
            filepath = config['filePath']['filePath']
            if not os.path.isabs(filepath):
                filepath = os.path.abspath(os.path.join(os.path.dirname(ini_file), filepath))
            return filepath
        except Exception as e:
            print(f"Error reading INI file: {e}")
            return None

    def read_ini_InideltaZ(ini_file):
        try:
            config = configparser.ConfigParser()
            with open(ini_file, 'r', encoding='utf-16') as f:
                config.read_file(f)
            return float(config['InideltaZ']['deltaZ'])
        except Exception as e:
            print(f"Error reading INI file: {e}")
            return None

    def get_latest_unique_id():
        target_process_substring = "ZmejkaFDS"
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if target_process_substring.lower() in proc.info['name'].lower():
                    process_id = proc.info['pid']
                    print(f"Found active process: {proc.info['name']} (PID: {process_id})")
                    return process_id
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        raise RuntimeError(f"No active process found with name containing '{target_process_substring}'.")

    current_directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
    inis_path = os.path.join(parent_directory, 'inis')

    ProcessID = None
    if len(sys.argv) > 1:
        try:
            ProcessID = int(sys.argv[1])
            print(f"Process ID received from command-line: {ProcessID}")
        except ValueError:
            print("Invalid ProcessID provided via command-line.")
    else:
        try:
            ProcessID = get_latest_unique_id()
            print(f"The latest UniqueID retrieved from INI files: {ProcessID}")
        except Exception as e:
            print(f"Error retrieving ProcessID: {e}")
            sys.exit(1)

    ini_filePath = os.path.join(inis_path, f'filePath_{ProcessID}.ini')
    if not os.path.exists(ini_filePath):
        print(f"Critical error: Missing filePath file: {ini_filePath}")
        sys.exit(1)

    filePath = read_ini_filePath(ini_filePath)

    ini_deltaZ = os.path.join(inis_path, 'InideltaZ.ini')
    if not os.path.exists(ini_deltaZ):
        print(f"Critical error: Missing InideltaZ file: {ini_deltaZ}")
        sys.exit(1)

    deltaZ = read_ini_InideltaZ(ini_deltaZ)
    print(f"deltaZ = {deltaZ}")

    if not filePath or deltaZ is None:
        print("Critical error: Missing filePath or deltaZ.")
        sys.exit(1)

    try:
        chid = extract_chid_from_fds(filePath)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    cached_data = None
    cached_time_data = None

    def start_tracking(e, page):
        global tracking_active, tracking_thread

        main_layout = None
        
        for control in page.controls[:]:
            if isinstance(control, ft.Column) and len(control.controls) > 0 and isinstance(control.controls[0], ft.Text):
                main_layout = control
            else:
                page.controls.remove(control)
        
        if main_layout:
            page.clean()
            page.add(main_layout)
        
        page.update()

        tracking_active = True
        track_button.visible = False
        stop_button.visible = True
        page.update()

        def track_data():
            while tracking_active:
                parse_and_plot_csv(page)
                time.sleep(5)

        tracking_thread = threading.Thread(target=track_data, daemon=True)
        tracking_thread.start()

    def stop_tracking(e, page):
        global tracking_active
        tracking_active = False
        track_button.visible = True
        stop_button.visible = False
        page.update()
        
    csv_directory = os.path.dirname(filePath)
    print(f"CSV directory set to: {csv_directory}")

    PLOT_YAXIS_TITLES = {
        "h": "Высота дымового слоя (м)",
        "Density_VM": "Плотность газов (кг/м^3)",
        "Tg 3D": "Температура газов (℃)",
        "MFLOW+": "Массовый расход дыма (кг/с)"
    }
    
    max_time = None

    def clear_gui(page):
        for i in range(len(page.controls) - 1, -1, -1):
            control = page.controls[i]
            if isinstance(control, ft.Image) or isinstance(control, ft.Text):
                page.controls.pop(i)
        page.update()

    def clear_plot_images(csv_directory):
        try:
            plot_files = glob.glob(os.path.join(csv_directory, "*.png"))
            for file in plot_files:
                try:
                    os.remove(file)
                    print(f"Deleted old plot file: {file}")
                except Exception as e:
                    print(f"Error deleting file {file}: {e}")
        except Exception as e:
            print(f"Error clearing plot images: {e}")
            
    def clear_plot_rows(page):
        for i in range(len(page.controls) - 1, -1, -1):
            control = page.controls[i]
            if isinstance(control, ft.Row) and any(isinstance(child, ft.Image) for child in control.controls):
                page.controls.pop(i)
            elif isinstance(control, ft.Text) and "Plots" in control.value:
                page.controls.pop(i)
        page.update()

    def create_plot_row(page, plots_dict, row_title):
        plot_images = []
        for key, values in plots_dict.items():
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=cached_time_data, y=values, mode='lines', name=key))

            yaxis_title = None
            for plot_type, title in PLOT_YAXIS_TITLES.items():
                if key.startswith(plot_type):
                    yaxis_title = title
                    break

            fig.update_layout(
                title=key,
                xaxis_title="Time (s)",
                yaxis_title=yaxis_title or "Value"
            )
            plot_path = os.path.join(csv_directory, f"{key}_plot.png")
            fig.write_image(plot_path)
            plot_images.append(ft.Image(src=plot_path, width=200, height=150))

        if plot_images:
            page.add(ft.Text(row_title, size=16))
            page.add(ft.Row(plot_images, spacing=10))

    def parse_and_plot_csv(page):
        nonlocal cached_data, cached_time_data

        clear_gui(page)

        clear_plot_images(csv_directory)

        clear_plot_rows(page)

        csv_path = os.path.join(csv_directory, f"{chid}*_devc.csv")
        csv_files = glob.glob(csv_path)
        print(f"Found {len(csv_files)} CSV files: {csv_files}")
        if not csv_files:
            print("No CSV files found!")
            return

        data = {}
        time_data = []

        for csv_file in csv_files:
            with open(csv_file, 'r') as file:
                reader = csv.reader(file)
                next(reader)
                headers = next(reader)
                headers = [header.strip().strip('"') for header in headers]
                values = []

                for row in reader:
                    try:
                        row = [float(val) for val in row]
                        if len(row) == len(headers):
                            values.append(row)
                        else:
                            print(f"Skipping malformed row: {row}")
                    except ValueError as e:
                        print(f"Error parsing row: {row} - {e}")
                        continue

                time_data.extend([row[0] for row in values])

                for i, header in enumerate(headers):
                    if (
                        header.startswith(("h_", "Density_VM_", "Tg 3D_", "MFLOW+_"))
                        or header.startswith(("h ", "Density_VM ", "Tg 3D ", "MFLOW+ "))
                    ):
                        if header not in data:
                            data[header] = []
                        data[header].extend([row[i] for row in values])

        print(f"Data to plot: {data}")
        print(f"FDS Time values: {time_data}")
        if not data or not time_data:
            print("No data to plot!")
            return

        max_time = max(time_data)
        print(f"Maximum FDS Time value: {max_time}")

        cached_data = data
        cached_time_data = time_data

        density_vm_koridor_values = [
            values for key, values in data.items() if "Density_VM Koridor" in key
        ]
        min_density_vm_koridor = None
        if density_vm_koridor_values:
            min_density_vm_koridor = min(min(values) for values in density_vm_koridor_values)

        mflow_koridor_values = [
            values for key, values in data.items() if "MFLOW+ Koridor" in key
        ]
        avg_max_mflow_koridor = None
        if mflow_koridor_values:
            max_values = [max(values) for values in mflow_koridor_values]
            avg_max_mflow_koridor = sum(max_values) / len(max_values)

        print(f"Minimum Density_VM Koridor value: {min_density_vm_koridor}")
        print(f"Average Maximum MFLOW+ Koridor value: {avg_max_mflow_koridor}")

        standard_plots = {}
        koridor_plots = {}

        for key, values in data.items():
            if "Koridor" in key:
                koridor_plots[key] = values
            else:
                standard_plots[key] = values

        create_plot_row(page, standard_plots, "Standard Plots")
        create_plot_row(page, koridor_plots, "Koridor Plots")

        return max_time

    def start_tracking(e, page):
        global tracking_active, tracking_thread
        tracking_active = True
        track_button.visible = False
        stop_button.visible = True
        page.update()

        def track_data():
            max_time = parse_and_plot_csv(page)

            if cached_time_data and cached_time_data[-1] >= max_time:
                print("Simulation time reached the maximum value. Stopping tracking.")
                stop_tracking(None, page)
            else:
                track_button.visible = True
                stop_button.visible = False
                page.update()

        tracking_thread = threading.Thread(target=track_data, daemon=True)
        tracking_thread.start()

    def stop_tracking(e, page):
        global tracking_active
        tracking_active = False
        track_button.visible = True
        stop_button.visible = False
        page.update()

    def save_plots_clicked(e):
        nonlocal cached_data, cached_time_data

        clear_gui(page)

        clear_plot_images(csv_directory)

        if not cached_data or not cached_time_data:
            page.add(ft.Text("No cached data to save!"))
            page.update()
            return

        for key, values in cached_data.items():
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=cached_time_data, y=values, mode='lines', name=key))
            
            yaxis_title = None
            for plot_type, title in PLOT_YAXIS_TITLES.items():
                if key.startswith(plot_type):
                    yaxis_title = title
                    break
            
            fig.update_layout(
                title=key,
                xaxis_title="Время (сек)",
                yaxis_title=yaxis_title or "Value"
            )
            plot_path = os.path.join(csv_directory, f"{key}_plot.png")
            fig.write_image(plot_path)
            page.add(ft.Text(f"Saved plot: {plot_path}"))

        page.update()

    def update_charts(page, data, time_data):
        if not data or not time_data:
            page.add(ft.Text("No data to plot!"))
            page.update()
            return

        for child in page.controls[:]:
            if isinstance(child, ft.Image):
                page.controls.remove(child)

        standard_plots = {}
        koridor_plots = {}

        for key, values in data.items():
            if "Koridor" in key:
                koridor_plots[key] = values
            else:
                standard_plots[key] = values

        def create_plot_row(plots_dict, row_title):
            plot_images = []
            for key, values in plots_dict.items():
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=time_data, y=values, mode='lines', name=key))

                yaxis_title = None
                for plot_type, title in PLOT_YAXIS_TITLES.items():
                    if key.startswith(plot_type):
                        yaxis_title = title
                        break

                fig.update_layout(
                    title=key,
                    xaxis_title="Time (s)",
                    yaxis_title=yaxis_title or "Value"
                )
                plot_path = f"{csv_directory}\\{key}_plot.png"
                fig.write_image(plot_path)
                plot_images.append(ft.Image(src=plot_path, width=200, height=150))

            if plot_images:
                page.add(ft.Text(row_title, size=16))
                page.add(ft.Row(plot_images, spacing=10))

        create_plot_row(standard_plots, "Standard Plots")

        create_plot_row(koridor_plots, "Koridor Plots")

        page.update()

    def save_clicked(e):
        global tracking_active, tracking_thread

        try:
            user_z2 = float(z2_input.value)
            page.session.set("user_z2", user_z2)
            
            output_lines = []
            devc_counter_0001 = 1
            devc_counter_0002 = 1

            with open(filePath, 'r') as file:
                for line in file:
                    output_lines.append(line)
                    if line.strip().startswith("&INIT"):
                        xb_match = re.search(r'XB=([\d\.\-,]+)', line)
                        temp_match = re.search(r'TEMPERATURE=(\d+\.\d+)', line)

                        if xb_match and temp_match:
                            xb_values = list(map(float, xb_match.group(1).split(',')))
                            temperature = temp_match.group(1)

                            x1, x2, y1, y2, z1, z2_orig = xb_values
                            z2 = user_z2 - (deltaZ / 2)

                            if temperature.endswith(".0001"):
                                devc_lines = [
                                    f"&DEVC ID='h_{devc_counter_0001}', QUANTITY='LAYER HEIGHT', XB={x1},{x2},{y1},{y2},{z1},{z2}/\n",
                                    f"&DEVC ID='Density_VM_{devc_counter_0001}', QUANTITY='DENSITY', STATISTICS='VOLUME MEAN', XB={x1},{x2},{y1},{y2},{z1},{z2}/\n",
                                    f"&DEVC ID='Tg 3D_{devc_counter_0001}', QUANTITY='GAS TEMPERATURE', STATISTICS='MEAN', XB={x1},{x2},{y1},{y2},{z1},{z2}/\n",
                                    f"&DEVC ID='MFLOW+_{devc_counter_0001}', QUANTITY='MASS FLOW +', XB={x1},{x2},{y1},{y2},{z2},{z2}/\n"
                                ]
                                output_lines.extend(devc_lines)
                                devc_counter_0001 += 1

                            elif temperature.endswith(".0002"):
                                devc_lines = [
                                    f"&DEVC ID='h Koridor_{devc_counter_0002}', QUANTITY='LAYER HEIGHT', XB={x1},{x2},{y1},{y2},{z1},{z2}/\n",
                                    f"&DEVC ID='Density_VM Koridor_{devc_counter_0002}', QUANTITY='DENSITY', STATISTICS='VOLUME MEAN', XB={x1},{x2},{y1},{y2},{z1},{z2}/\n",
                                    f"&DEVC ID='Tg 3D Koridor_{devc_counter_0002}', QUANTITY='GAS TEMPERATURE', STATISTICS='MEAN', XB={x1},{x2},{y1},{y2},{z1},{z2}/\n",
                                    f"&DEVC ID='MFLOW+ Koridor_{devc_counter_0002}', QUANTITY='MASS FLOW +', XB={x1},{x2},{y1},{y2},{z2},{z2}/\n"
                                ]
                                output_lines.extend(devc_lines)
                                devc_counter_0002 += 1

            with open(filePath, 'w') as file:
                file.writelines(output_lines)

            page.window.destroy()

        except ValueError:
            z2_input.error_text = "Введите рациональное число"
            page.update()

    # GUI
    z2_input = ft.TextField(label="Введите высоту помещения, м", hint_text="до нижней плоскости перекрытия")
    track_button = ft.ElevatedButton(text="Track", on_click=lambda e: start_tracking(e, page))
    stop_button = ft.ElevatedButton(text="Stop", on_click=lambda e: stop_tracking(e, page), visible=False)
    save_plots_button = ft.ElevatedButton(text="Сохранить графики", on_click=save_plots_clicked)
    apply_button = ft.ElevatedButton(text="Применить", on_click=save_clicked)

    # Главный контейнер
    main_layout = ft.Column([
        ft.Text("1. Отдельно отрисуйте помещения, в которых хотите измерить параметры СПДЗ.\n2. Выделите помещение, в свойствах поставьте галочку 'Учитывать температуру'.\n3. Для помещения с очагом пожара температуру воздуха установите ',0001',\nа для всех остальных помещений температуру выставьте ',0002'.\n4. Введите высоту помещения ниже и нажмите 'Применить'.\n5. Запустите расчет.\n6. Спустя 10 секунд после начала расчета можно нажать 'Track',\nчтобы отслеживать изменение параметров СПДЗ в реальном времени.", size=12),
        z2_input,
        ft.Row([apply_button, track_button, stop_button, save_plots_button], alignment=ft.MainAxisAlignment.CENTER),
    ])

    # Кнопки и отступы
    page.add(
        ft.Container(main_layout, padding=10),
        ft.Container(height=20),
        ft.Divider(),
        ft.Container(height=50)
    )

if __name__ == "__main__":
    ft.app(target=modify_fds_file)