import psutil
import numpy as np
from typing import Dict
import os
import time
import array
import logging

class RAMMonitor:
    """Класс для мониторинга и анализа оперативной памяти"""
    
    def __init__(self):
        """Инициализация монитора RAM"""
        self.virtual_memory = psutil.virtual_memory()
        self.swap_memory = psutil.swap_memory()
        self.last_measurement = None
    
    def get_ram_info(self) -> Dict:
        """
        Получение информации об оперативной памяти
        
        Returns:
            Dict: Словарь с информацией о RAM
        """
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            'total': vm.total,
            'available': vm.available,
            'used': vm.used,
            'free': vm.free,
            'percent': vm.percent,
            'swap_total': swap.total,
            'swap_used': swap.used,
            'swap_free': swap.free,
            'swap_percent': swap.percent
        }
    
    def get_ram_usage(self) -> float:
        """
        Получение текущего процента использования RAM
        
        Returns:
            float: Процент использования RAM
        """
        try:
            return psutil.virtual_memory().percent
        except Exception as e:
            logging.warning(f"Ошибка при получении использования RAM: {str(e)}")
            return 0.0
    
    def get_detailed_ram_info(self) -> Dict:
        """
        Получение детальной информации о RAM и SWAP
        
        Returns:
            Dict: Словарь с информацией о RAM и SWAP
        """
        try:
            ram = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            ram_info = {
                'total_gb': ram.total / (1024 ** 3),
                'available_gb': ram.available / (1024 ** 3),
                'used_gb': ram.used / (1024 ** 3),
                'free_gb': ram.free / (1024 ** 3),
                'percent': ram.percent,
                'cached': getattr(ram, 'cached', 0) / (1024 ** 3),
                'buffers': getattr(ram, 'buffers', 0) / (1024 ** 3)
            }
            
            swap_info = {
                'total_gb': swap.total / (1024 ** 3),
                'used_gb': swap.used / (1024 ** 3),
                'free_gb': swap.free / (1024 ** 3),
                'percent': swap.percent
            }
            
            return {
                'ram': ram_info,
                'swap': swap_info
            }
        except Exception as e:
            logging.warning(f"Ошибка при получении детальной информации о RAM: {str(e)}")
            return {
                'ram': {
                    'total_gb': 0, 'available_gb': 0, 'used_gb': 0,
                    'free_gb': 0, 'percent': 0, 'cached': 0, 'buffers': 0
                },
                'swap': {
                    'total_gb': 0, 'used_gb': 0, 'free_gb': 0, 'percent': 0
                }
            }
    
    def calculate_ram_speed(self, size_mb: int = 100) -> Dict:
        """
        Тест скорости RAM через операции чтения/записи
        
        Args:
            size_mb (int): Размер тестируемого блока памяти в МБ
        
        Returns:
            Dict: Словарь с результатами теста
        """
        try:
            # Создаем массив для теста
            size_bytes = size_mb * 1024 * 1024
            data = np.zeros(size_bytes // 8, dtype=np.float64)
            
            # Тест записи
            write_times = []
            for _ in range(3):
                start_time = psutil.cpu_times().user
                data.fill(3.14)
                end_time = psutil.cpu_times().user
                write_times.append(end_time - start_time)
            
            # Тест чтения
            read_times = []
            for _ in range(3):
                start_time = psutil.cpu_times().user
                _ = np.sum(data)
                end_time = psutil.cpu_times().user
                read_times.append(end_time - start_time)
            
            # Вычисляем скорости
            write_speed = size_mb / np.mean(write_times)
            read_speed = size_mb / np.mean(read_times)
            total_speed = (write_speed + read_speed) / 2
            
            return {
                'write_speed': write_speed,
                'read_speed': read_speed,
                'total_speed': total_speed
            }
        except Exception as e:
            logging.warning(f"Ошибка при тестировании скорости RAM: {str(e)}")
            return {
                'write_speed': 0,
                'read_speed': 0,
                'total_speed': 0
            } 