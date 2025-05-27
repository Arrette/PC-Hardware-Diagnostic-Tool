from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
import sys
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Основная функция запуска приложения"""
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logging.error(f"Ошибка при запуске приложения: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 