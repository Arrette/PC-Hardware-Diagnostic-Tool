import psutil
import cpuinfo
from typing import Dict, List, Tuple
import time
import logging
import os

class CPUMonitor:
    """Класс для мониторинга и анализа CPU"""
    
    def __init__(self):
        """Инициализация монитора CPU"""
        self.cpu_info = cpuinfo.get_cpu_info()
        self.prev_cpu_times = psutil.cpu_times()
        self.prev_time = time.time()

    def get_cpu_info(self) -> Dict:
        """
        Получение основной информации о процессоре
        
        Returns:
            Dict: Словарь с информацией о процессоре
        """
        return {
            'model': self.cpu_info['brand_raw'],
            'architecture': self.cpu_info['arch'],
            'cores_physical': psutil.cpu_count(logical=False),
            'cores_logical': psutil.cpu_count(logical=True),
            'frequency_max': psutil.cpu_freq().max,
            'frequency_current': psutil.cpu_freq().current
        }

    def get_cpu_usage(self) -> float:
        """
        Получение текущей загрузки CPU
        
        Returns:
            float: Процент загрузки CPU
        """
        try:
            # Получаем загрузку CPU без интервала ожидания
            return psutil.cpu_percent(interval=None)
        except Exception as e:
            logging.warning(f"Ошибка при получении загрузки CPU: {str(e)}")
            return 0.0

    def get_cpu_temperature(self) -> Dict[str, float]:
        """
        Получение температуры CPU
        
        Returns:
            Dict[str, float]: Словарь с температурами
        """
        temps = {}
        
        # Для Windows пробуем получить через WMI
        if os.name == 'nt':
            try:
                import wmi
                w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
                temperature_infos = w.Sensor()
                for sensor in temperature_infos:
                    if sensor.SensorType == 'Temperature' and ('CPU' in sensor.Name or 'Core' in sensor.Name):
                        temps[sensor.Name] = float(sensor.Value)
            except Exception as e:
                logging.debug(f"Не удалось получить температуру через WMI: {str(e)}")
                
                # Пробуем через MSI Afterburner если он установлен
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                       r"SOFTWARE\WOW6432Node\MSI\Afterburner",
                                       0, winreg.KEY_READ)
                    msi_path = winreg.QueryValueEx(key, "InstallPath")[0]
                    if os.path.exists(msi_path):
                        temps["CPU"] = 0  # Заглушка, так как реальные данные получить сложно
                except:
                    pass
        
        # Для Linux и других систем используем psutil
        else:
            try:
                sensors = psutil.sensors_temperatures()
                if sensors:
                    for name, entries in sensors.items():
                        if any(x.lower() in name.lower() for x in ['cpu', 'core', 'package']):
                            for idx, entry in enumerate(entries):
                                if hasattr(entry, 'current') and entry.current:
                                    label = entry.label if entry.label else f"Core {idx}"
                                    temps[label] = float(entry.current)
            except Exception as e:
                logging.debug(f"Не удалось получить температуру через psutil: {str(e)}")
        
        # Если температура не найдена, пробуем через другие методы
        if not temps:
            try:
                # Пробуем получить через команду системы
                if os.name == 'nt':
                    import subprocess
                    try:
                        result = subprocess.check_output(['wmic', 'temperature', 'get', 'currentreading'], 
                                                       universal_newlines=True)
                        temp = float(result.strip().split('\n')[1])
                        if temp > 0:
                            temps['CPU'] = temp
                    except:
                        pass
                else:
                    # Для Linux пробуем через sensors
                    try:
                        result = subprocess.check_output(['sensors'], universal_newlines=True)
                        for line in result.split('\n'):
                            if ':' in line and any(x in line.lower() for x in ['cpu', 'core', 'package']):
                                parts = line.split(':')
                                if len(parts) == 2:
                                    try:
                                        temp = float(parts[1].split('°')[0])
                                        temps[parts[0].strip()] = temp
                                    except:
                                        continue
                    except:
                        pass
            except Exception as e:
                logging.debug(f"Не удалось получить температуру через альтернативные методы: {str(e)}")
        
        if not temps:
            return {'error': 'Temperature sensors not available'}
        
        return temps

    def get_detailed_usage(self) -> List[float]:
        """
        Получение загрузки по ядрам
        
        Returns:
            List[float]: Список загрузки каждого ядра
        """
        try:
            # Получаем загрузку по ядрам без интервала ожидания
            return psutil.cpu_percent(interval=None, percpu=True)
        except Exception as e:
            logging.warning(f"Ошибка при получении загрузки ядер CPU: {str(e)}")
            return [0.0] * psutil.cpu_count()

    def calculate_cpu_speed(self) -> float:
        """
        Расчет производительности CPU через простой бенчмарк
        
        Returns:
            float: Оценка производительности
        """
        start_time = time.time()
        counter = 0
        while time.time() - start_time < 1.0:
            counter += 1
            _ = [i ** 2 for i in range(1000)]
        return counter / (time.time() - start_time) 