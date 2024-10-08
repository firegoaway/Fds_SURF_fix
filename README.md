# FSF - FDS SURF FIX

> Язык: **Python**

> Интерфейс: **Tkinter**

## Особенности и описание работы утилиты
Утилита позволяет привести параметры моделирования пожара в сценариях, создаваемых ***Fenix+*** и ***Pyrosim***, к требуемым согласно [***Приложению 1 Методики 1140***](https://ivo.garant.ru/#/document/406577165/paragraph/184/doclist/198/1/0/0/методика%201140:0).

![Прил1](https://raw.githubusercontent.com/firegoaway/Fds_SURF_fix/main/.gitpics/прил1.PNG)

Особенность этих формул состоит в том, что мощность и результаты развития пожара на выходе **инвариантны** к размерам очага пожара в пожарной модели **FDS**.

### Поддерживаемые версии FDS
> [**FDS 6.9.1**](https://github.com/firemodels/fds/releases/tag/FDS-6.9.1)
> [**FDS 6.9.0**](https://github.com/firemodels/fds/releases/tag/FDS-6.9.0)
> [**FDS 6.8.0**](https://github.com/firemodels/fds/releases/tag/FDS-6.8.0)

## Как установить и пользоваться

|	№ п/п	|	Действие	|
|---------|---------|
|	1	|	Скачайте последнюю версию **ZmejkaFDS** в разделе [**Releases**](https://github.com/firegoaway/Zmejka/releases)	|
|	2	|	Запустите **ZmejkaFDS.exe**. Нажмите **"Выбрать .fds"** и выберите файл сценария FDS	|
|	3	|	Во вкладке **"Параметры"** нажмите **"SURF_FIX"**. Откроется новое окно	|
|	4	|	В окне **FDS SURF FIX** заполните все необходимые входные данные. Следуйте всплывающим подсказкам. Они помогут вам неошибиться в значениях. Помните, что десятичным разделителем является **точка**, а не запятая (например, число ***"3,3"*** должно быть введено так - ***"3.3"***	|
|	5	|	Нажмите на кнопку **Рассчитать**, и утилита рассчитает необходимые параметры моделирования пожара	|
|	6	|	Нажмите **"Сохранить"** и утилита сохранит изменения в вашем файле сценария **".fds"**	|
|	7	|	Готово! Файл сценария **.fds** готов к запуску	|

> **FSF** работает как самостоятельно, так и в связке с утилитой [**Zmejka**](https://github.com/firegoaway/Zmejka)

## Статус разработки
> **Альфа**

## Профилактика вирусов и угроз
- Утилита **"FSF"** предоставляется **"как есть"**.
- Актуальная версия утилиты доступна в разделе [**Releases**](https://github.com/firegoaway/Fds_SURF_fix/releases), однако использовать утилиту в отрыве от [**ZmejkaFDS**](https://github.com/firegoaway/Zmejka) не рекомендуется.
- Файлы, каким-либо образом полученные не из текущего репозитория, несут потенциальную угрозу вашему ПК.
- Файл с расширением **.exe**, полученный из данного репозитория, имеет уникальную Хэш-сумму, позволяющую отличить оригинальную утилиту от подделки.
- Хэш-сумма обновляется только при обновлении версии утилиты и всегда доступна в конце файла **README.md**.

### Актуальные Хэш-суммы
> SURF_FIX.exe - **c97c0fe122947043e0ba81615b028f2b**