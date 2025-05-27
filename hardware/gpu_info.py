import GPUtil
from typing import Dict, List
import psutil
import logging
import numpy as np
import time
import os
try:
    from pynvml import *
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False
    logging.warning("NVML не доступен, будет использован GPUtil")

class GPUMonitor:
    """Класс для мониторинга и анализа GPU"""
    
    def __init__(self):
        """Инициализация монитора GPU"""
        self.nvml_initialized = False
        self.handles = []
        self.last_update = 0
        self.update_interval = 0.5  # Увеличиваем интервал обновления до 0.5 секунд
        self.last_valid_load = 0.0
        self.last_valid_info = None
        self.gpus = []
        
        try:
            # Сначала пробуем инициализировать NVML
            if NVML_AVAILABLE:
                try:
                    nvmlInit()
                    self.nvml_initialized = True
                    deviceCount = nvmlDeviceGetCount()
                    for i in range(deviceCount):
                        self.handles.append(nvmlDeviceGetHandleByIndex(i))
                except Exception as e:
                    logging.debug(f"Не удалось инициализировать NVML: {str(e)}")
                    self.nvml_initialized = False
            
            # Затем пробуем GPUtil
            try:
                self.gpus = GPUtil.getGPUs()
            except Exception as e:
                logging.debug(f"Не удалось получить информацию через GPUtil: {str(e)}")
                self.gpus = []
            
            # Если оба метода не сработали, пробуем через WMI
            if not self.gpus and os.name == 'nt':
                try:
                    import wmi
                    w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
                    temperature_infos = w.Sensor()
                    if any(sensor.SensorType == 'Load' and 'GPU' in sensor.Name 
                          for sensor in temperature_infos):
                        self.gpus = [type('GPU', (), {
                            'id': 0,
                            'name': 'Unknown GPU',
                            'load': 0,
                            'memoryTotal': 0,
                            'memoryUsed': 0,
                            'temperature': 0,
                            'uuid': 'N/A'
                        })]
                except Exception as e:
                    logging.debug(f"Не удалось получить информацию через WMI: {str(e)}")
        
        except Exception as e:
            logging.warning(f"Не удалось инициализировать GPU: {str(e)}")
            self.gpus = []
    
    def _update_initial_values(self):
        """Инициализация начальных значений"""
        try:
            if self.nvml_initialized and self.handles:
                utilization = nvmlDeviceGetUtilizationRates(self.handles[0])
                self.last_valid_load = float(utilization.gpu)
            elif self.gpus:
                self.last_valid_load = float(self.gpus[0].load * 100) if self.gpus[0].load is not None else 0.0
            else:
                # Пробуем получить через WMI
                if os.name == 'nt':
                    try:
                        import wmi
                        w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
                        temperature_infos = w.Sensor()
                        for sensor in temperature_infos:
                            if sensor.SensorType == 'Load' and 'GPU' in sensor.Name:
                                self.last_valid_load = float(sensor.Value)
                                break
                    except:
                        pass
        except Exception as e:
            logging.debug(f"Ошибка при инициализации начальных значений GPU: {str(e)}")
    
    def __del__(self):
        """Освобождение ресурсов NVML"""
        if self.nvml_initialized:
            try:
                nvmlShutdown()
            except:
                pass
    
    def _should_update(self) -> bool:
        """Проверка необходимости обновления данных"""
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.last_update = current_time
            return True
        return False
    
    def get_gpu_info(self) -> List[Dict]:
        """
        Получение информации о всех GPU в системе
        
        Returns:
            List[Dict]: Список словарей с информацией о каждом GPU
        """
        gpu_info = []
        current_time = time.time()
        
        # Проверяем, нужно ли обновлять данные
        if current_time - self.last_update < self.update_interval:
            return [self.last_valid_info] if self.last_valid_info else []
        
        self.last_update = current_time
        
        try:
            # Обновляем информацию через GPUtil
            self.gpus = GPUtil.getGPUs()
            
            for i, gpu in enumerate(self.gpus):
                try:
                    if self.nvml_initialized and i < len(self.handles):
                        # Получаем информацию через NVML
                        handle = self.handles[i]
                        utilization = nvmlDeviceGetUtilizationRates(handle)
                        memory = nvmlDeviceGetMemoryInfo(handle)
                        temp = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
                        
                        load = float(utilization.gpu)
                        if load < 0:
                            load = self.last_valid_load
                        else:
                            self.last_valid_load = load
                        
                        info = {
                            'id': gpu.id,
                            'name': gpu.name,
                            'load': load,
                            'free_memory': memory.free // (1024*1024),
                            'total_memory': memory.total // (1024*1024),
                            'used_memory': memory.used // (1024*1024),
                            'temperature': float(temp),
                            'uuid': gpu.uuid
                        }
                    else:
                        # Получаем информацию через GPUtil
                        load = float(gpu.load * 100) if gpu.load is not None else self.last_valid_load
                        if load < 0:
                            load = self.last_valid_load
                        else:
                            self.last_valid_load = load
                        
                        info = {
                            'id': gpu.id,
                            'name': gpu.name,
                            'load': load,
                            'free_memory': int(gpu.memoryFree) if gpu.memoryFree is not None else 0,
                            'total_memory': int(gpu.memoryTotal) if gpu.memoryTotal is not None else 0,
                            'used_memory': int(gpu.memoryUsed) if gpu.memoryUsed is not None else 0,
                            'temperature': float(gpu.temperature) if gpu.temperature is not None else 0,
                            'uuid': gpu.uuid
                        }
                    
                    # Проверяем корректность значений памяти
                    if info['total_memory'] > 0:
                        if info['used_memory'] > info['total_memory']:
                            info['used_memory'] = info['total_memory']
                        if info['free_memory'] > info['total_memory']:
                            info['free_memory'] = info['total_memory'] - info['used_memory']
                    
                    # Сохраняем корректную информацию
                    self.last_valid_info = info
                    gpu_info.append(info)
                    
                except Exception as e:
                    logging.warning(f"Ошибка при получении информации о GPU {gpu.id}: {str(e)}")
                    if self.last_valid_info is not None:
                        gpu_info.append(self.last_valid_info)
        
        except Exception as e:
            logging.warning(f"Ошибка при обновлении списка GPU: {str(e)}")
            if self.last_valid_info is not None:
                gpu_info.append(self.last_valid_info)
        
        return gpu_info
    
    def get_gpu_usage(self) -> List[float]:
        """
        Получение текущей загрузки всех GPU
        
        Returns:
            List[float]: Список значений загрузки в процентах
        """
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return [self.last_valid_load]
        
        try:
            if self.nvml_initialized:
                usage = []
                for handle in self.handles:
                    try:
                        utilization = nvmlDeviceGetUtilizationRates(handle)
                        load = float(utilization.gpu)
                        if load >= 0:
                            self.last_valid_load = load
                        else:
                            load = self.last_valid_load
                        usage.append(load)
                    except:
                        usage.append(self.last_valid_load)
                return usage if usage else [self.last_valid_load]
            else:
                # Получаем свежие данные через GPUtil
                self.gpus = GPUtil.getGPUs()
                usage = []
                for gpu in self.gpus:
                    load = float(gpu.load * 100) if gpu.load is not None else self.last_valid_load
                    if load >= 0:
                        self.last_valid_load = load
                    else:
                        load = self.last_valid_load
                    usage.append(load)
                return usage if usage else [self.last_valid_load]
        except Exception as e:
            logging.warning(f"Ошибка при получении загрузки GPU: {str(e)}")
            return [self.last_valid_load]
    
    def get_gpu_memory_usage(self) -> List[Dict]:
        """
        Получение информации об использовании памяти GPU
        
        Returns:
            List[Dict]: Список словарей с информацией о памяти каждого GPU
        """
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            if self.last_valid_info:
                return [{
                    'total': self.last_valid_info['total_memory'],
                    'used': self.last_valid_info['used_memory'],
                    'free': self.last_valid_info['free_memory'],
                    'utilization': (self.last_valid_info['used_memory'] / self.last_valid_info['total_memory'] * 100) 
                            if self.last_valid_info['total_memory'] > 0 else 0
                }]
            return []
        
        memory_info = []
        try:
            if self.nvml_initialized:
                for handle in self.handles:
                    try:
                        memory = nvmlDeviceGetMemoryInfo(handle)
                        info = {
                            'total': memory.total // (1024*1024),
                            'used': memory.used // (1024*1024),
                            'free': memory.free // (1024*1024),
                            'utilization': (memory.used / memory.total * 100) if memory.total > 0 else 0
                        }
                        memory_info.append(info)
                    except Exception as e:
                        logging.warning(f"Ошибка при получении информации о памяти GPU: {str(e)}")
            else:
                self.gpus = GPUtil.getGPUs()
                for gpu in self.gpus:
                    try:
                        total = int(gpu.memoryTotal) if gpu.memoryTotal is not None else 0
                        used = int(gpu.memoryUsed) if gpu.memoryUsed is not None else 0
                        free = int(gpu.memoryFree) if gpu.memoryFree is not None else 0
                        
                        # Проверяем корректность значений
                        if total > 0:
                            if used > total:
                                used = total
                            if free > total:
                                free = total - used
                        
                        info = {
                            'total': total,
                            'used': used,
                            'free': free,
                            'utilization': (used / total * 100) if total > 0 else 0
                        }
                        memory_info.append(info)
                    except Exception as e:
                        logging.warning(f"Ошибка при получении информации о памяти GPU: {str(e)}")
        except Exception as e:
            logging.warning(f"Ошибка при обновлении информации о памяти GPU: {str(e)}")
        
        return memory_info
    
    def get_gpu_temperature(self) -> List[float]:
        """
        Получение температуры всех GPU
        
        Returns:
            List[float]: Список значений температуры в градусах Цельсия
        """
        try:
            temps = []
            if self.nvml_initialized:
                for handle in self.handles:
                    try:
                        # Пробуем получить температуру через NVML
                        temp = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
                        if temp is not None and temp > 0:
                            temps.append(float(temp))
                        else:
                            # Если не удалось, пробуем другие методы NVML
                            try:
                                temp = nvmlDeviceGetTemperatureThreshold(handle, NVML_TEMPERATURE_THRESHOLD_SHUTDOWN)
                                if temp is not None and temp > 0:
                                    temps.append(float(temp))
                                else:
                                    raise ValueError("Invalid temperature value")
                            except:
                                # Если и это не удалось, используем GPUtil
                                gpu_idx = len(temps)  # Индекс текущего GPU
                                if gpu_idx < len(self.gpus):
                                    gpu = self.gpus[gpu_idx]
                                    if gpu.temperature is not None and gpu.temperature > 0:
                                        temps.append(float(gpu.temperature))
                                    else:
                                        temps.append(0.0)
                                else:
                                    temps.append(0.0)
                    except Exception as e:
                        logging.warning(f"Ошибка при получении температуры GPU через NVML: {str(e)}")
                        # Пробуем получить через GPUtil
                        gpu_idx = len(temps)  # Индекс текущего GPU
                        if gpu_idx < len(self.gpus):
                            gpu = self.gpus[gpu_idx]
                            if gpu.temperature is not None and gpu.temperature > 0:
                                temps.append(float(gpu.temperature))
                            else:
                                temps.append(0.0)
                        else:
                            temps.append(0.0)
            else:
                # Получаем температуру через GPUtil
                try:
                    gpus = GPUtil.getGPUs()
                    for gpu in gpus:
                        if gpu.temperature is not None and gpu.temperature > 0:
                            temps.append(float(gpu.temperature))
                        else:
                            temps.append(0.0)
                except Exception as e:
                    logging.warning(f"Ошибка при получении температуры через GPUtil: {str(e)}")
                    temps.append(0.0)
            
            # Если не удалось получить температуру ни одним способом
            if not temps:
                # Пробуем получить через WMI на Windows
                if os.name == 'nt':
                    try:
                        import wmi
                        w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
                        temperature_infos = w.Sensor()
                        for sensor in temperature_infos:
                            if sensor.SensorType == 'Temperature' and 'GPU' in sensor.Name:
                                temps.append(float(sensor.Value))
                    except:
                        pass
            
            return temps if temps else [0.0]
            
        except Exception as e:
            logging.warning(f"Ошибка при получении температуры GPU: {str(e)}")
            return [0.0]
    
    def calculate_gpu_score(self) -> float:
        """
        Простой бенчмарк GPU через проверку загрузки
        
        Returns:
            float: Оценка производительности
        """
        try:
            total_score = 0
            if self.nvml_initialized:
                for handle in self.handles:
                    try:
                        utilization = nvmlDeviceGetUtilizationRates(handle)
                        memory = nvmlDeviceGetMemoryInfo(handle)
                        score = (100 - utilization.gpu) * (memory.total / (1024*1024*1024))
                        total_score += score
                    except:
                        continue
            else:
                for gpu in GPUtil.getGPUs():
                    if gpu.memoryTotal is not None and gpu.load is not None:
                        score = (100 - gpu.load * 100) * (gpu.memoryTotal / 1024)
                        total_score += score
            return total_score
        except Exception as e:
            logging.warning(f"Ошибка при расчете производительности GPU: {str(e)}")
            return 0 