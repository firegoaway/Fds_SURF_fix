import os
import re
import csv
import io
import glob
import configparser
import flet
from flet import Page, Text, TextField, ElevatedButton, Row, Column, SnackBar, ScrollMode
from flet.plotly_chart import PlotlyChart
import plotly.graph_objects as go
import plotly.io as pio
import sys

def get_unique_id(ProcessID=None):
    return str(ProcessID) if ProcessID is not None else str(os.getpid())

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

def main(page: Page):
    unique_id = get_unique_id(ProcessID)

    page.title = f"Расчет СПДЗ ID: {unique_id}"
    page.vertical_alignment = flet.MainAxisAlignment.CENTER
    page.horizontal_alignment = flet.CrossAxisAlignment.CENTER
    page.window.width = 620
    page.window.height = 640
    page.scroll = ScrollMode.AUTO
    page.padding = 20
    page.spacing = 10
    
    inis_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "inis"))
    fds_file_ini_path = os.path.join(inis_folder, f"filePath_{unique_id}.ini")
    inideltaZ_ini_path = os.path.join(inis_folder, "InideltaZ.ini")
    
    if not os.path.isfile(fds_file_ini_path):
        page.add(Text(f"Error: {fds_file_ini_path} not found.", color="red"))
        return
    
    if not os.path.isfile(inideltaZ_ini_path):
        page.add(Text(f"Error: {inideltaZ_ini_path} not found.", color="red"))
        return
    
    config = configparser.ConfigParser()
    
    with io.open(inideltaZ_ini_path, mode="r", encoding="utf-16") as f:
        config.read_file(f)
    
    default_delta_z_str = config.get("InideltaZ", "deltaZ", fallback="0.75")
    cfg_fds = configparser.ConfigParser()
    
    with io.open(fds_file_ini_path, mode="r", encoding="utf-16") as f:
        cfg_fds.read_file(f)
    
    try:
        path_to_fds = None
        for section in cfg_fds.sections():
            if cfg_fds.has_option(section, "path"):
                path_to_fds = cfg_fds.get(section, "path")
                break
        if path_to_fds is None:
            with io.open(fds_file_ini_path, mode="r", encoding="utf-16") as f1:
                lines = f1.read().splitlines()
                path_to_fds = lines[-1] if lines else ""
    except:
        page.add(Text("Could not parse the .fds path.", color="red"))
        return
    
    path_to_fds = path_to_fds.strip()
    
    if not os.path.isfile(path_to_fds):
        page.add(Text(f"Error: FDS file '{path_to_fds}' not found.", color="red"))
        return
    
    chid = extract_chid_from_fds(path_to_fds)
    deltaZ_field = TextField(label="deltaZ value", value=default_delta_z_str, width=100)
    apply_button = ElevatedButton(text="Применить")
    track_button = ElevatedButton(text="Рассчитать", disabled=False)
    save_plots_button = ElevatedButton(text="Сохранить графики", disabled=True)
    status_text = Text(value="", color="blue")
    plotted_figures_non_koridor = []
    plotted_figures_koridor = []
    controls_row = Row([deltaZ_field, apply_button, track_button, save_plots_button], spacing=10)
    page.add(controls_row, status_text)
    non_koridor_row = Row([], alignment="center", spacing=15)
    koridor_row = Row([], alignment="center", spacing=15)
    plot_container = Column([non_koridor_row, koridor_row], spacing=20)
    page.add(plot_container)
    
    def apply_modifications():
        try:
            user_delta_z = float(deltaZ_field.value.strip())
        except ValueError:
            page.open(SnackBar(content=Text("Invalid deltaZ value!"), bgcolor="red"))
            return
        
        try:
            with io.open(path_to_fds, mode="r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except:
            page.open(SnackBar(content=Text("Could not read .fds file!"), bgcolor="red"))
            return
        
        updated_lines = []
        count_0001 = 0
        count_0002 = 0
        init_line_pattern = re.compile(r"^\s*&INIT.*TEMPERATURE\s*=\s*(\d+\.\d+)", re.IGNORECASE)
        xb_pattern = re.compile(r"XB\s*=\s*([-\d\.]+)\s*,\s*([-\d\.]+)\s*,\s*([-\d\.]+)\s*,\s*([-\d\.]+)\s*,\s*([-\d\.]+)\s*,\s*([-\d\.]+)", re.IGNORECASE)
        
        for line in lines:
            updated_lines.append(line)
            match_init = init_line_pattern.search(line)
            if match_init:
                temperature_value_str = match_init.group(1)
                match_xb = xb_pattern.search(line)
                if not match_xb:
                    continue
                x1, x2, y1, y2, z1, z2 = [float(g) for g in match_xb.groups()]
                z2_adjusted = z2 - (user_delta_z / 2.0)
                if temperature_value_str.endswith("0001"):
                    count_0001 += 1
                    devc_id_suffix = f"_{count_0001}"
                    devc_ids = [
                        f"h{devc_id_suffix}",
                        f"Density_VM{devc_id_suffix}",
                        f"Tg 3D{devc_id_suffix}",
                        f"MFLOW+{devc_id_suffix}"
                    ]
                elif temperature_value_str.endswith("0002"):
                    count_0002 += 1
                    devc_id_suffix = f"_Koridor_{count_0002}"
                    devc_ids = [
                        f"h{devc_id_suffix}",
                        f"Density_VM{devc_id_suffix}",
                        f"Tg 3D{devc_id_suffix}",
                        f"MFLOW+{devc_id_suffix}"
                    ]
                else:
                    continue
                devc_lines = [
                    f"&DEVC ID='{devc_ids[0]}', QUANTITY='LAYER HEIGHT', XB={x1},{x2},{y1},{y2},{z1},{z2_adjusted}/\n",
                    f"&DEVC ID='{devc_ids[1]}', QUANTITY='DENSITY', STATISTICS='VOLUME MEAN', XB={x1},{x2},{y1},{y2},{z1},{z2_adjusted}/\n",
                    f"&DEVC ID='{devc_ids[2]}', QUANTITY='GAS TEMPERATURE', STATISTICS='MEAN', XB={x1},{x2},{y1},{y2},{z1},{z2_adjusted}/\n",
                    f"&DEVC ID='{devc_ids[3]}', QUANTITY='MASS FLOW +', XB={x1},{x2},{y1},{y2},{z2_adjusted},{z2_adjusted}/\n",
                ]
                updated_lines.extend(devc_lines)
        try:
            with io.open(path_to_fds, mode="w", encoding="utf-8") as f:
                f.writelines(updated_lines)
        except:
            page.open(SnackBar(content=Text("Could not write to .fds file!"), bgcolor="red"))
            return
        
        status_text.value = "Файл .fds успешно изменён!"
        deltaZ_field.disabled = True
        apply_button.disabled = True
        track_button.disabled = False
        page.update()
    
    def track_values():
        nonlocal plotted_figures_non_koridor
        nonlocal plotted_figures_koridor
        plotted_figures_non_koridor = []
        plotted_figures_koridor = []
        plot_container.controls.clear()
        fds_dir = os.path.dirname(path_to_fds)
        csv_files = glob.glob(os.path.join(fds_dir, f"{chid}*_devc.csv"))
        devc_data = {}
        pattern_dev_id = re.compile(r'^(h(_Koridor)?_\d+|Density_VM(_Koridor)?_\d+|Tg 3D(_Koridor)?_\d+|MFLOW\+(_Koridor)?_\d+)$', re.IGNORECASE)
        time_column_name = "FDS Time"
        
        for csv_file in csv_files:
            try:
                with io.open(csv_file, mode="r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.reader(f)
                    lines_read = 0
                    headers = []
                    for row in reader:
                        lines_read += 1
                        if lines_read == 2:
                            headers = [h.strip().strip('"') for h in row]
                            relevant_indices = {}
                            for idx, col_name in enumerate(headers):
                                if col_name == time_column_name:
                                    relevant_indices[idx] = time_column_name
                                elif pattern_dev_id.match(col_name):
                                    relevant_indices[idx] = col_name
                                    if col_name not in devc_data:
                                        devc_data[col_name] = {"time": [], "values": []}
                        elif lines_read > 2:
                            if not headers:
                                continue
                            t_val = None
                            for idx in relevant_indices:
                                col_name = relevant_indices[idx]
                                if idx < len(row):
                                    cell_value = row[idx].strip()
                                    if col_name == time_column_name:
                                        try:
                                            t_val = float(cell_value)
                                        except:
                                            t_val = None
                                    else:

                                        if t_val is not None:
                                            try:
                                                val = float(cell_value)
                                            except:
                                                val = 0.0
                                            devc_data[col_name]["time"].append(t_val)
                                            devc_data[col_name]["values"].append(val)
            except:
                continue
        
        density_vm_min = None
        mflow_plus_values_for_avg = []
        non_koridor_row = Row(wrap=True, scroll=ScrollMode.AUTO, spacing=5)
        koridor_row = Row(wrap=True, scroll=ScrollMode.AUTO, spacing=5)
        #non_koridor_row = Row(wrap=True)
        #koridor_row = Row(wrap=True)
        
        for dev_id, data_dict in devc_data.items():
            t_arr = data_dict["time"]
            v_arr = data_dict["values"]
            if len(t_arr) == 0 or len(v_arr) == 0:
                continue
            if dev_id.startswith("Density_VM"):
                local_min = min(v_arr)
                if density_vm_min is None or local_min < density_vm_min:
                    density_vm_min = local_min
            if dev_id.startswith("MFLOW+"):
                local_max = max(v_arr)
                mflow_plus_values_for_avg.append(local_max)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=t_arr, y=v_arr, mode='lines', name=dev_id))
            fig.update_layout(title=dev_id, xaxis_title="Время (сек)", 
                              yaxis_title="Высота дымового слоя (м)" if dev_id.startswith("h") else
                                           "Среднеобъемная температура газов (\u2103)" if dev_id.startswith("Tg") else
                                           "Массовый расход газов (кг/с)" if dev_id.startswith("MFLOW+") else
                                           "Среднеобъемная плотность газов (кг/м^3)" if dev_id.startswith("Density_VM") else 
                                           "Value",
                              height=400, width=450, margin=dict(l=50, r=50, t=50, b=50))
            #fig.update_layout(title=dev_id, xaxis_title="Time (s)", yaxis_title="Value", height=250, width=300, margin=dict(l=40, r=40, t=40, b=40))
            if "_Koridor_" in dev_id:
                plotted_figures_koridor.append(fig)
            else:
                plotted_figures_non_koridor.append(fig)
        
        for fig in plotted_figures_non_koridor:
            non_koridor_row.controls.append(PlotlyChart(fig, expand=False))
        
        for fig in plotted_figures_koridor:
            koridor_row.controls.append(PlotlyChart(fig, expand=False))
        
        plot_container.controls.append(Text("Графики для помещения с очагом пожара:", weight="bold"))
        plot_container.controls.append(non_koridor_row)
        plot_container.controls.append(Text("Графики для остальных помещений:", weight="bold"))
        plot_container.controls.append(koridor_row)
        
        if density_vm_min is not None and len(mflow_plus_values_for_avg) > 0:
            avg_max_mflow_plus = sum(mflow_plus_values_for_avg) / len(mflow_plus_values_for_avg)
            gsm = avg_max_mflow_plus / density_vm_min
            gp = gsm * 0.7
            plot_container.controls.append(Text(f"Density_VM(MIN) = {density_vm_min:.4g}\nAvg(MFLOW+(MAX)) = {avg_max_mflow_plus:.4g}\nGsm = {gsm:.4g}\nGp = {gp:.4g}\nGsmf = {gsm*3600:.4g}\nGpf = {gp*3600:.4g}"))
        else:
            plot_container.controls.append(Text("Недостаточно данных для расчета Gsm/Gp!"))
        
        save_plots_button.disabled = False
        page.update()
    
    def save_plots():
        nonlocal plotted_figures_non_koridor
        nonlocal plotted_figures_koridor
        output_dir = os.path.dirname(path_to_fds)
        
        for i, fig in enumerate(plotted_figures_non_koridor, start=1):
            outpath = os.path.join(output_dir, f"{chid}_non_koridor_plot_{i}.png")
            pio.write_image(fig, outpath, format="png")
        
        for i, fig in enumerate(plotted_figures_koridor, start=1):
            outpath = os.path.join(output_dir, f"{chid}_koridor_plot_{i}.png")
            pio.write_image(fig, outpath, format="png")
        
        page.open(SnackBar(content=Text("Графики успешно сохранены!"), bgcolor="green"))
    
    apply_button.on_click = lambda e: apply_modifications()
    track_button.on_click = lambda e: track_values()
    save_plots_button.on_click = lambda e: save_plots()
    page.update()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ProcessID = int(sys.argv[1])
        print(f"Process ID received from AHK: {ProcessID}")
    else:
        print("No Process ID received.")
    
    flet.app(target=main)