from PyQt5.QtWidgets import (QMainWindow, QWidget, QTabWidget,
                             QVBoxLayout, QPushButton, QLabel,
                             QMessageBox, QFileDialog, QGridLayout,
                             QProgressBar)
from PyQt5.QtCore import QTimer
from hardware.cpu_info import CPUMonitor
from hardware.gpu_info import GPUMonitor
from hardware.ram_info import RAMMonitor
from hardware.storage_info import StorageMonitor
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from datetime import datetime
import os
import logging
import psutil

class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PC Hardware Monitor")
        self.setGeometry(100, 100, 1024, 768)
        
        # Инициализация мониторов
        self.cpu_monitor = CPUMonitor()
        self.gpu_monitor = GPUMonitor()
        self.ram_monitor = RAMMonitor()
        self.storage_monitor = StorageMonitor()
        
        # Создание центрального виджета
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Создание вкладок
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Инициализация графиков и данных
        self.cpu_usage_data = []
        self.gpu_usage_data = []
        self.ram_usage_data = []
        
        # Инициализация виджетов CPU
        self.cpu_info_label = None
        self.cpu_usage_bar = None
        self.cpu_temp_label = None
        self.cpu_figure = None
        self.cpu_canvas = None
        self.cpu_cores_bars = []
        
        # Инициализация виджетов GPU
        self.gpu_labels = []
        self.gpu_usage_bars = []
        self.gpu_memory_bars = []
        self.gpu_figure = None
        self.gpu_canvas = None
        
        # Инициализация виджетов RAM
        self.ram_info_label = None
        self.ram_bar = None
        self.swap_info_label = None
        self.swap_bar = None
        self.ram_figure = None
        self.ram_canvas = None
        
        # Инициализация вкладок
        self.setup_cpu_tab()
        self.setup_gpu_tab()
        self.setup_ram_tab()
        self.setup_storage_tab()
        
        # Кнопка генерации отчета
        report_button = QPushButton("Сгенерировать отчет")
        report_button.clicked.connect(self.generate_report)
        layout.addWidget(report_button)
        
        # Таймер для обновления данных
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.start(1000)  # Обновление каждую секунду
        
        # Инициализация начальных значений CPU и GPU
        psutil.cpu_percent(interval=None)  # Первый вызов для инициализации
        psutil.cpu_percent(interval=None, percpu=True)  # Первый вызов для ядер

    def setup_cpu_tab(self):
        """Настройка вкладки CPU"""
        cpu_tab = QWidget()
        self.cpu_layout = QVBoxLayout(cpu_tab)
        
        try:
            # Информация о CPU
            cpu_info = self.cpu_monitor.get_cpu_info()
            self.cpu_info_label = QLabel(f"Процессор: {cpu_info['model']}\n"
                                       f"Ядра: {cpu_info['cores_physical']} "
                                       f"(Логические: {cpu_info['cores_logical']})\n"
                                       f"Максимальная частота: {cpu_info['frequency_max']} MHz")
            self.cpu_layout.addWidget(self.cpu_info_label)
            
            # Общая загрузка CPU
            self.cpu_usage_bar = QProgressBar()
            self.cpu_layout.addWidget(QLabel("Общая загрузка CPU:"))
            self.cpu_layout.addWidget(self.cpu_usage_bar)
            
            # Загрузка по ядрам
            cores_widget = QWidget()
            cores_layout = QGridLayout(cores_widget)
            for i in range(cpu_info['cores_logical']):
                label = QLabel(f"Ядро {i}:")
                bar = QProgressBar()
                self.cpu_cores_bars.append(bar)
                row = i // 4  # 4 ядра в строке
                col = i % 4 * 2  # Умножаем на 2, чтобы оставить место для меток
                cores_layout.addWidget(label, row, col)
                cores_layout.addWidget(bar, row, col + 1)
            self.cpu_layout.addWidget(cores_widget)
            
            # График загрузки CPU
            self.cpu_figure = Figure(figsize=(5, 4), dpi=100)
            self.cpu_canvas = FigureCanvasQTAgg(self.cpu_figure)
            self.cpu_layout.addWidget(self.cpu_canvas)
            self.setup_cpu_plot()
            
            # Кнопка запуска бенчмарка
            benchmark_button = QPushButton("Запустить бенчмарк")
            benchmark_button.clicked.connect(self.run_cpu_benchmark)
            self.cpu_layout.addWidget(benchmark_button)
            
        except Exception as e:
            logging.error(f"Ошибка при настройке вкладки CPU: {str(e)}")
            self.cpu_layout.addWidget(QLabel(f"Ошибка при получении информации о CPU"))
        
        self.tabs.addTab(cpu_tab, "CPU")

    def setup_gpu_tab(self):
        """Настройка вкладки GPU"""
        gpu_tab = QWidget()
        self.gpu_layout = QVBoxLayout(gpu_tab)
        
        try:
            gpu_info = self.gpu_monitor.get_gpu_info()
            if gpu_info:
                for gpu in gpu_info:
                    # Информация о GPU
                    info_label = QLabel()
                    self.gpu_labels.append(info_label)
                    self.gpu_layout.addWidget(info_label)
                    
                    # Прогресс бары
                    usage_bar = QProgressBar()
                    self.gpu_usage_bars.append(usage_bar)
                    self.gpu_layout.addWidget(QLabel("Загрузка GPU:"))
                    self.gpu_layout.addWidget(usage_bar)
                    
                    memory_bar = QProgressBar()
                    self.gpu_memory_bars.append(memory_bar)
                    self.gpu_layout.addWidget(QLabel("Использование памяти:"))
                    self.gpu_layout.addWidget(memory_bar)
                    
                # График загрузки
                self.gpu_figure = Figure(figsize=(5, 4), dpi=100)
                self.gpu_canvas = FigureCanvasQTAgg(self.gpu_figure)
                self.gpu_layout.addWidget(self.gpu_canvas)
                self.setup_gpu_plot()
                
                # Кнопка бенчмарка
                benchmark_button = QPushButton("Запустить бенчмарк GPU")
                benchmark_button.clicked.connect(self.run_gpu_benchmark)
                self.gpu_layout.addWidget(benchmark_button)
            else:
                self.gpu_layout.addWidget(QLabel("GPU не обнаружен"))
        except Exception as e:
            logging.error(f"Ошибка при настройке вкладки GPU: {str(e)}")
            self.gpu_layout.addWidget(QLabel(f"Ошибка при получении информации о GPU"))
        
        self.tabs.addTab(gpu_tab, "GPU")
    
    def setup_ram_tab(self):
        """Настройка вкладки RAM"""
        ram_tab = QWidget()
        self.ram_layout = QVBoxLayout(ram_tab)
        
        try:
            # Основная информация о RAM
            self.ram_info_label = QLabel()
            self.ram_layout.addWidget(self.ram_info_label)
            
            # Прогресс бар RAM
            self.ram_bar = QProgressBar()
            self.ram_layout.addWidget(QLabel("Использование RAM:"))
            self.ram_layout.addWidget(self.ram_bar)
            
            # Информация о SWAP
            self.swap_info_label = QLabel()
            self.ram_layout.addWidget(self.swap_info_label)
            
            # Прогресс бар SWAP
            self.swap_bar = QProgressBar()
            self.ram_layout.addWidget(QLabel("Использование SWAP:"))
            self.ram_layout.addWidget(self.swap_bar)
            
            # График использования
            self.ram_figure = Figure(figsize=(5, 4), dpi=100)
            self.ram_canvas = FigureCanvasQTAgg(self.ram_figure)
            self.ram_layout.addWidget(self.ram_canvas)
            self.setup_ram_plot()
            
            # Кнопка теста скорости
            speed_button = QPushButton("Тест скорости RAM")
            speed_button.clicked.connect(self.run_ram_benchmark)
            self.ram_layout.addWidget(speed_button)
            
        except Exception as e:
            logging.error(f"Ошибка при настройке вкладки RAM: {str(e)}")
            self.ram_layout.addWidget(QLabel(f"Ошибка при получении информации о RAM"))
        
        self.tabs.addTab(ram_tab, "RAM")
    
    def setup_storage_tab(self):
        """Настройка вкладки Storage"""
        storage_tab = QWidget()
        layout = QVBoxLayout(storage_tab)
        
        try:
            drives_info = self.storage_monitor.get_drives_info()
            
            for drive in drives_info:
                # Информация о диске
                drive_text = (f"Диск: {drive['device']}\n"
                            f"Точка монтирования: {drive['mountpoint']}\n"
                            f"Файловая система: {drive['fstype']}\n"
                            f"Всего: {drive['total_gb']:.1f} GB\n"
                            f"Свободно: {drive['free_gb']:.1f} GB\n"
                            f"Использовано: {drive['used_gb']:.1f} GB")
                layout.addWidget(QLabel(drive_text))
                
                # Прогресс бар использования
                usage_bar = QProgressBar()
                usage_bar.setValue(int(drive['percent']))
                layout.addWidget(QLabel(f"Использование {drive['device']}:"))
                layout.addWidget(usage_bar)
            
            # Кнопка теста скорости
            speed_button = QPushButton("Тест скорости дисков")
            speed_button.clicked.connect(self.run_storage_benchmark)
            layout.addWidget(speed_button)
            
        except Exception as e:
            layout.addWidget(QLabel(f"Ошибка при получении информации о накопителях: {str(e)}"))
        
        self.tabs.addTab(storage_tab, "Storage")
    
    def setup_cpu_plot(self):
        """Настройка графика загрузки CPU"""
        if self.cpu_figure is not None:
            self.cpu_figure.clear()
            self.cpu_ax = self.cpu_figure.add_subplot(111)
            self.cpu_ax.set_title('Загрузка CPU')
            self.cpu_ax.set_xlabel('Время (с)')
            self.cpu_ax.set_ylabel('Загрузка (%)')
            self.cpu_ax.set_ylim(0, 100)
            self.cpu_line, = self.cpu_ax.plot([], [])
    
    def setup_gpu_plot(self):
        """Настройка графика загрузки GPU"""
        self.gpu_figure.clear()
        self.ax_gpu = self.gpu_figure.add_subplot(111)
        self.ax_gpu.set_title('Загрузка GPU')
        self.ax_gpu.set_xlabel('Время (с)')
        self.ax_gpu.set_ylabel('Загрузка (%)')
        self.ax_gpu.set_ylim(0, 100)
        self.gpu_line, = self.ax_gpu.plot([], [])
    
    def setup_ram_plot(self):
        """Настройка графика использования RAM"""
        self.ram_figure.clear()
        self.ax_ram = self.ram_figure.add_subplot(111)
        self.ax_ram.set_title('Использование RAM')
        self.ax_ram.set_xlabel('Время (с)')
        self.ax_ram.set_ylabel('Использование (%)')
        self.ax_ram.set_ylim(0, 100)
        self.ram_line, = self.ax_ram.plot([], [])
    
    def update_data(self):
        """Обновление данных в реальном времени"""
        try:
            # Обновление CPU
            if self.cpu_figure is not None:
                cpu_usage = self.cpu_monitor.get_cpu_usage()
                cpu_detailed = self.cpu_monitor.get_detailed_usage()
                
                # Обновление общей загрузки
                if isinstance(cpu_usage, (int, float)) and cpu_usage >= 0:
                    self.cpu_usage_data.append(cpu_usage)
                    if len(self.cpu_usage_data) > 60:
                        self.cpu_usage_data.pop(0)
                    
                    # Обновление графика CPU
                    self.update_cpu_plot()
                    
                    # Обновление прогресс-бара общей загрузки
                    self.cpu_usage_bar.setValue(int(cpu_usage))
                
                # Обновление загрузки ядер
                if isinstance(cpu_detailed, list):
                    for i, usage in enumerate(cpu_detailed):
                        if i < len(self.cpu_cores_bars) and isinstance(usage, (int, float)) and usage >= 0:
                            self.cpu_cores_bars[i].setValue(int(usage))
            
            # Обновление GPU
            gpu_info = self.gpu_monitor.get_gpu_info()
            gpu_usage = self.gpu_monitor.get_gpu_usage()
            
            if gpu_info and self.gpu_figure is not None:
                if gpu_usage and isinstance(gpu_usage[0], (int, float)) and gpu_usage[0] >= 0:
                    self.gpu_usage_data.append(gpu_usage[0])
                    if len(self.gpu_usage_data) > 60:
                        self.gpu_usage_data.pop(0)
                    
                    # Обновление графика GPU
                    self.update_gpu_plot()
                
                # Обновление информации о GPU
                for i, gpu in enumerate(gpu_info):
                    if i < len(self.gpu_labels):
                        temp = gpu.get('temperature', 0)
                        temp_str = f"{temp:.1f}°C" if isinstance(temp, (int, float)) and temp > 0 else "Н/Д"
                        
                        self.gpu_labels[i].setText(
                            f"Видеокарта: {gpu['name']}\n"
                            f"Загрузка: {gpu['load']:.1f}%\n"
                            f"Память: {gpu['used_memory']}/{gpu['total_memory']} MB\n"
                            f"Температура: {temp_str}"
                        )
                        if i < len(self.gpu_usage_bars):
                            self.gpu_usage_bars[i].setValue(int(gpu['load']))
                        if i < len(self.gpu_memory_bars):
                            memory_percent = ((gpu['total_memory'] - gpu['free_memory']) / gpu['total_memory'] * 100) if gpu['total_memory'] > 0 else 0
                            self.gpu_memory_bars[i].setValue(int(memory_percent))
            
            # Обновление RAM
            if self.ram_info_label is not None and self.ram_figure is not None:
                ram_info = self.ram_monitor.get_detailed_ram_info()
                ram_usage = self.ram_monitor.get_ram_usage()
                
                if isinstance(ram_usage, (int, float)) and ram_usage >= 0:
                    self.ram_usage_data.append(ram_usage)
                    if len(self.ram_usage_data) > 60:
                        self.ram_usage_data.pop(0)
                    
                    # Обновление графика RAM
                    self.update_ram_plot()
                
                # Обновление информации о RAM
                self.ram_info_label.setText(
                    f"Всего RAM: {ram_info['ram']['total_gb']:.1f} GB\n"
                    f"Использовано: {ram_info['ram']['used_gb']:.1f} GB\n"
                    f"Свободно: {ram_info['ram']['free_gb']:.1f} GB\n"
                    f"Загрузка: {ram_info['ram']['percent']}%"
                )
                self.ram_bar.setValue(int(ram_info['ram']['percent']))
                
                self.swap_info_label.setText(
                    f"Всего SWAP: {ram_info['swap']['total_gb']:.1f} GB\n"
                    f"Использовано: {ram_info['swap']['used_gb']:.1f} GB\n"
                    f"Свободно: {ram_info['swap']['free_gb']:.1f} GB\n"
                    f"Загрузка: {ram_info['swap']['percent']}%"
                )
                self.swap_bar.setValue(int(ram_info['swap']['percent']))
            
        except Exception as e:
            logging.error(f"Ошибка при обновлении данных: {str(e)}")
    
    def update_cpu_plot(self):
        """Обновление графика CPU"""
        try:
            if self.cpu_figure is not None:
                self.cpu_figure.clear()
                ax = self.cpu_figure.add_subplot(111)
                ax.plot(range(len(self.cpu_usage_data)), self.cpu_usage_data)
                ax.set_title('Загрузка CPU')
                ax.set_xlabel('Время (с)')
                ax.set_ylabel('Загрузка (%)')
                ax.set_ylim(0, 100)
                self.cpu_canvas.draw()
        except Exception as e:
            logging.error(f"Ошибка при обновлении графика CPU: {str(e)}")
    
    def update_gpu_plot(self):
        """Обновление графика GPU"""
        try:
            if self.gpu_figure is not None:
                self.gpu_figure.clear()
                ax = self.gpu_figure.add_subplot(111)
                ax.plot(range(len(self.gpu_usage_data)), self.gpu_usage_data)
                ax.set_title('Загрузка GPU')
                ax.set_xlabel('Время (с)')
                ax.set_ylabel('Загрузка (%)')
                ax.set_ylim(0, 100)
                self.gpu_canvas.draw()
        except Exception as e:
            logging.error(f"Ошибка при обновлении графика GPU: {str(e)}")
    
    def update_ram_plot(self):
        """Обновление графика RAM"""
        try:
            if self.ram_figure is not None:
                self.ram_figure.clear()
                ax = self.ram_figure.add_subplot(111)
                ax.plot(range(len(self.ram_usage_data)), self.ram_usage_data)
                ax.set_title('Использование RAM')
                ax.set_xlabel('Время (с)')
                ax.set_ylabel('Использование (%)')
                ax.set_ylim(0, 100)
                self.ram_canvas.draw()
        except Exception as e:
            logging.error(f"Ошибка при обновлении графика RAM: {str(e)}")
    
    def run_cpu_benchmark(self):
        """Запуск бенчмарка CPU"""
        score = self.cpu_monitor.calculate_cpu_speed()
        QMessageBox.information(
            self,
            "Результаты бенчмарка",
            f"Производительность CPU: {score:.2f} операций/с\n\n"
            f"Чем выше значение, тем лучше производительность."
        )
    
    def generate_report(self):
        """Генерация отчета о состоянии системы"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчет",
            os.path.join(os.path.expanduser("~"), "Desktop", f"hardware_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"),
            "HTML files (*.html);;All Files (*)"
        )
        
        if filename:
            try:
                # Сбор всех данных для отчета
                cpu_info = self.cpu_monitor.get_cpu_info()
                cpu_usage = self.cpu_monitor.get_cpu_usage()
                cpu_detailed = self.cpu_monitor.get_detailed_usage()
                
                gpu_info = self.gpu_monitor.get_gpu_info()
                gpu_memory = self.gpu_monitor.get_gpu_memory_usage()
                
                ram_info = self.ram_monitor.get_detailed_ram_info()
                storage_info = self.storage_monitor.get_drives_info()
                io_info = self.storage_monitor.get_disk_io()
                
                # Генерация HTML отчета
                html_content = f"""
                <html>
                <head>
                    <title>Отчет о состоянии оборудования</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; }}
                        h1 {{ color: #333; }}
                        .section {{ margin: 20px 0; padding: 20px; background: #f5f5f5; border-radius: 5px; }}
                        .warning {{ color: #f44336; }}
                        .good {{ color: #4caf50; }}
                        .table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                        .table th, .table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                        .table th {{ background-color: #f0f0f0; }}
                    </style>
                </head>
                <body>
                    <h1>Отчет о состоянии оборудования</h1>
                    
                    <div class="section">
                        <h2>Процессор (CPU)</h2>
                        <table class="table">
                            <tr><td>Модель:</td><td>{cpu_info['model']}</td></tr>
                            <tr><td>Архитектура:</td><td>{cpu_info['architecture']}</td></tr>
                            <tr><td>Физические ядра:</td><td>{cpu_info['cores_physical']}</td></tr>
                            <tr><td>Логические ядра:</td><td>{cpu_info['cores_logical']}</td></tr>
                            <tr><td>Максимальная частота:</td><td>{cpu_info['frequency_max']} MHz</td></tr>
                            <tr><td>Текущая частота:</td><td>{cpu_info['frequency_current']} MHz</td></tr>
                            <tr><td>Текущая загрузка:</td><td>{cpu_usage}%</td></tr>
                        </table>
                        <h3>Загрузка по ядрам:</h3>
                        <table class="table">
                            {''.join(f'<tr><td>Ядро {i}</td><td>{usage:.1f}%</td></tr>' for i, usage in enumerate(cpu_detailed))}
                        </table>
                    </div>

                    <div class="section">
                        <h2>Видеокарта (GPU)</h2>
                        {''.join(f"""
                        <h3>GPU {i+1}: {gpu['name']}</h3>
                        <table class="table">
                            <tr><td>Загрузка:</td><td>{gpu['load']:.1f}%</td></tr>
                            <tr><td>Температура:</td><td>{gpu['temperature']}°C</td></tr>
                            <tr><td>Память всего:</td><td>{gpu['total_memory']} MB</td></tr>
                            <tr><td>Память свободно:</td><td>{gpu['free_memory']} MB</td></tr>
                            <tr><td>Память использовано:</td><td>{gpu['total_memory'] - gpu['free_memory']} MB</td></tr>
                            <tr><td>Использование памяти:</td><td>{((gpu['total_memory'] - gpu['free_memory']) / gpu['total_memory'] * 100):.1f}%</td></tr>
                        </table>
                        """ for i, gpu in enumerate(gpu_info)) if gpu_info else '<p>GPU не обнаружен</p>'}
                    </div>

                    <div class="section">
                        <h2>Оперативная память (RAM)</h2>
                        <h3>Физическая память</h3>
                        <table class="table">
                            <tr><td>Всего:</td><td>{ram_info['ram']['total_gb']:.1f} GB</td></tr>
                            <tr><td>Использовано:</td><td>{ram_info['ram']['used_gb']:.1f} GB</td></tr>
                            <tr><td>Свободно:</td><td>{ram_info['ram']['free_gb']:.1f} GB</td></tr>
                            <tr><td>Доступно:</td><td>{ram_info['ram']['available_gb']:.1f} GB</td></tr>
                            <tr><td>Загрузка:</td><td>{ram_info['ram']['percent']}%</td></tr>
                            <tr><td>Кэшировано:</td><td>{ram_info['ram']['cached']:.1f} GB</td></tr>
                            <tr><td>Буферы:</td><td>{ram_info['ram']['buffers']:.1f} GB</td></tr>
                        </table>
                        
                        <h3>Файл подкачки (SWAP)</h3>
                        <table class="table">
                            <tr><td>Всего:</td><td>{ram_info['swap']['total_gb']:.1f} GB</td></tr>
                            <tr><td>Использовано:</td><td>{ram_info['swap']['used_gb']:.1f} GB</td></tr>
                            <tr><td>Свободно:</td><td>{ram_info['swap']['free_gb']:.1f} GB</td></tr>
                            <tr><td>Загрузка:</td><td>{ram_info['swap']['percent']}%</td></tr>
                        </table>
                    </div>

                    <div class="section">
                        <h2>Накопители</h2>
                        {''.join(f"""
                        <h3>Диск: {drive['device']}</h3>
                        <table class="table">
                            <tr><td>Точка монтирования:</td><td>{drive['mountpoint']}</td></tr>
                            <tr><td>Файловая система:</td><td>{drive['fstype']}</td></tr>
                            <tr><td>Общий объем:</td><td>{drive['total_gb']:.1f} GB</td></tr>
                            <tr><td>Использовано:</td><td>{drive['used_gb']:.1f} GB</td></tr>
                            <tr><td>Свободно:</td><td>{drive['free_gb']:.1f} GB</td></tr>
                            <tr><td>Загрузка:</td><td>{drive['percent']}%</td></tr>
                        </table>
                        """ for drive in storage_info)}
                        
                        <h3>Статистика ввода/вывода</h3>
                        {''.join(f"""
                        <h4>Диск: {disk}</h4>
                        <table class="table">
                            <tr><td>Прочитано:</td><td>{stats['read_bytes'] / (1024**3):.1f} GB</td></tr>
                            <tr><td>Записано:</td><td>{stats['write_bytes'] / (1024**3):.1f} GB</td></tr>
                            <tr><td>Операций чтения:</td><td>{stats['read_count']}</td></tr>
                            <tr><td>Операций записи:</td><td>{stats['write_count']}</td></tr>
                            <tr><td>Время чтения:</td><td>{stats['read_time']} мс</td></tr>
                            <tr><td>Время записи:</td><td>{stats['write_time']} мс</td></tr>
                        </table>
                        """ for disk, stats in io_info.items())}
                    </div>

                    <div class="section">
                        <p><small>Отчет сгенерирован: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
                    </div>
                </body>
                </html>
                """
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                QMessageBox.information(self, "Успех", f"Отчет сохранен в {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить отчет: {str(e)}")
    
    def run_gpu_benchmark(self):
        """Запуск бенчмарка GPU"""
        try:
            score = self.gpu_monitor.calculate_gpu_score()
            QMessageBox.information(
                self,
                "Результаты бенчмарка GPU",
                f"Производительность GPU: {score:.2f}\n\n"
                f"Чем выше значение, тем лучше производительность."
            )
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось выполнить бенчмарк GPU: {str(e)}")
    
    def run_ram_benchmark(self):
        """Запуск теста скорости RAM"""
        try:
            results = self.ram_monitor.calculate_ram_speed()
            QMessageBox.information(
                self,
                "Результаты теста RAM",
                f"Скорость чтения: {results['read_speed']:.1f} MB/s\n"
                f"Скорость записи: {results['write_speed']:.1f} MB/s\n"
                f"Средняя скорость: {results['total_speed']:.1f} MB/s"
            )
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось выполнить тест RAM: {str(e)}")
    
    def run_storage_benchmark(self):
        """Запуск теста скорости накопителей"""
        try:
            results = self.storage_monitor.calculate_disk_speed()
            message = "Результаты теста накопителей:\n\n"
            for device, speeds in results.items():
                message += f"{device}:\n"
                message += f"Чтение: {speeds['read_speed']:.1f} MB/s\n"
                message += f"Запись: {speeds['write_speed']:.1f} MB/s\n"
                message += f"Средняя скорость: {speeds['total_speed']:.1f} MB/s\n\n"
            
            QMessageBox.information(self, "Тест накопителей", message)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось выполнить тест накопителей: {str(e)}") 
