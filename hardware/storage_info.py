import psutil
import os
from typing import Dict, List
import time
import subprocess
import json
import platform

class StorageMonitor:
    """Класс для мониторинга и анализа накопителей"""
    
    def __init__(self):
        """Инициализация монитора накопителей"""
        self.partitions = psutil.disk_partitions()
    
    def get_drives_info(self) -> List[Dict]:
        """
        Получение информации о всех накопителях
        
        Returns:
            List[Dict]: Список словарей с информацией о каждом накопителе
        """
        drives_info = []
        for partition in self.partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                info = {
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'total_gb': usage.total / (1024 ** 3),
                    'used_gb': usage.used / (1024 ** 3),
                    'free_gb': usage.free / (1024 ** 3),
                    'percent': usage.percent
                }
                drives_info.append(info)
            except (PermissionError, FileNotFoundError):
                continue
        return drives_info
    
    def get_disk_io(self) -> Dict:
        """
        Получение информации о дисковом вводе/выводе
        
        Returns:
            Dict: Словарь с информацией о IO
        """
        io_counters = psutil.disk_io_counters(perdisk=True)
        io_info = {}
        
        for disk, counters in io_counters.items():
            io_info[disk] = {
                'read_bytes': counters.read_bytes,
                'write_bytes': counters.write_bytes,
                'read_count': counters.read_count,
                'write_count': counters.write_count,
                'read_time': counters.read_time,
                'write_time': counters.write_time
            }
        return io_info
    
    def get_smart_info(self) -> Dict:
        """
        Получение SMART-информации о накопителях
        Требует установленный smartmontools
        
        Returns:
            Dict: Словарь с SMART-информацией
        """
        if platform.system() != "Windows":
            return {"error": "SMART info is currently supported only on Windows"}
        
        smart_info = {}
        try:
            # Получаем список физических дисков
            disks = []
            for partition in self.partitions:
                if partition.device and partition.device not in disks:
                    disks.append(partition.device[:2])  # Берем только букву диска
            
            for disk in disks:
                try:
                    # Запускаем smartctl для получения информации
                    result = subprocess.run(
                        ['smartctl', '-a', '-j', disk],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    smart_info[disk] = json.loads(result.stdout)
                except (subprocess.CalledProcessError, json.JSONDecodeError):
                    smart_info[disk] = {"error": "Failed to get SMART info"}
        except Exception as e:
            return {"error": f"Failed to get SMART info: {str(e)}"}
        
        return smart_info
    
    def calculate_disk_speed(self, test_size_mb: int = 100) -> Dict:
        """
        Тест скорости дисков через последовательную запись/чтение
        
        Args:
            test_size_mb: Размер тестового файла в МБ
            
        Returns:
            Dict: Словарь с результатами теста
        """
        results = {}
        test_file = "disk_speed_test.tmp"
        
        for partition in self.partitions:
            try:
                test_path = os.path.join(partition.mountpoint, test_file)
                
                # Тест записи
                start_time = time.time()
                with open(test_path, 'wb') as f:
                    f.write(os.urandom(test_size_mb * 1024 * 1024))
                write_time = time.time() - start_time
                write_speed = test_size_mb / write_time  # MB/s
                
                # Тест чтения
                start_time = time.time()
                with open(test_path, 'rb') as f:
                    f.read()
                read_time = time.time() - start_time
                read_speed = test_size_mb / read_time  # MB/s
                
                # Удаляем тестовый файл
                os.remove(test_path)
                
                results[partition.device] = {
                    'write_speed': write_speed,
                    'read_speed': read_speed,
                    'total_speed': (write_speed + read_speed) / 2
                }
            except (PermissionError, FileNotFoundError):
                continue
            
        return results 
