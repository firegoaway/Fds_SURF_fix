import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint

# Константы и параметры
Fpom = 500
HRR = 31.700
v = 0.0068
psi_yd = 0.0233
Cs = 0.425  # Размер ячейки
Hpom = 3    # Расстояние от пола до потолка в месте, где находится спринклер
hu = Hpom - Cs  # Высота размещения спринклера / прилегающая сторона
L = 4   # Нормативное расстояние между спринклерами / противоположная сторона
epsilon = 0.85  # Коэффициент облучённости (эмиссивность материала горючей нагрузки)
sigma = 5.670374419e-8  # Постоянная Стефана-Больцмана
alpha = 2e-4    # Коэффициент пропускания атмосферы
g = 9.81    # Гравитационная постоянная
K = 50  # Коэффициент тепловой инерционности спринклера
k = 4   # Коэффициент, описывающий отношение поверхности горючей нагрузки к площади помещения
Tu_0 = 24   # Начальная температура элемента датчика спринклера
angle = np.arctan(L/hu) # Угол по нормали к очагу

tmax = np.sqrt((k * Fpom) / (np.pi * v**2)) # Время охвата пожаром всей горючей нагрузки в помещении
t_mod = tmax    # Время моделирования пожара
q = lambda t: HRR * psi_yd * np.pi * v**2 * t**2    # Тепловая мощность пожара, кВт
phi = lambda t: np.sqrt(1 + v**2 * t**2)    # Угловой коэффициент облучённости по нормали к очагу
beta = np.sqrt(1 + angle * (np.pi / 180))   # Угловой коэффициент облучённости по окружности к очагу
Delta = lambda t: np.arctan(phi(t)) * np.arctan(beta)   # Дельта угловой облучённости

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

t_values = np.linspace(0, t_mod, 1000000)  # Диапазон времени для расчетов

# Вычисление и решение для Tu(t)
Tu_solution = odeint(
    sprinkler_sensor_temp,
    Tu_0,
    t_values,
    args=(gas_temperature,)
)

# Найдите, где ось y (Tu) достигает 57°C и отметьте это
x_mark, y_mark = None, None
cut_index = len(Tu_solution)  # Используем полную длину по умолчанию, если условие не выполнено

for i in range(len(Tu_solution)):
    if Tu_solution[i, 0] >= 57:
        x_mark = t_values[i]
        y_mark = Tu_solution[i, 0]
        cut_index = i  # Обновляем индекс точки останова, чтобы остановить отстраивание графика после отметки 'x'
        break

# Отсекаем данные для графика до достигнутого значения
t_values_cut = t_values[:cut_index+1]
Tu_solution_cut = Tu_solution[:cut_index+1]

# Построение графика результатов
plt.figure(figsize=(10, 6))
plt.plot(t_values_cut, Tu_solution_cut, label="dTu", color='black', linewidth=5, linestyle=':')

# Добавление красного маркера 'x', если 57°C была достигнута
if x_mark is not None and y_mark is not None:
    plt.scatter(x_mark, y_mark, color='red', marker='x', s=500, label=f"Tu = 57 °C \n t = {x_mark:.2f} сек")
    print(f"Фрагмент значений при Tu=57 °C -> Время (t): {x_mark:.2f} сек, Температура (Tu): {y_mark:.2f} °C")

# Форматирование графика
plt.title("График времени прогрева термочувствительного элемента до температуры, \n соответствующей порогу срабатывания (Tu)")
plt.xlabel("Время (t) [сек]")
plt.ylabel("Температура чувствительного элемента спринклера (Tu) [°C]")
plt.legend(loc='right')
plt.grid()
plt.show()
