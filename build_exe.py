import PyInstaller.__main__
import os
import shutil

# Получаем абсолютный путь к текущей директории
current_dir = os.path.dirname(os.path.abspath(__file__))
app_path = os.path.join(current_dir, 'app.py')

# Очищаем предыдущие сборки
dist_dir = os.path.join(current_dir, 'dist')
build_dir = os.path.join(current_dir, 'build')
spec_file = os.path.join(current_dir, 'app.spec')

if os.path.exists(dist_dir):
    shutil.rmtree(dist_dir)
if os.path.exists(build_dir):
    shutil.rmtree(build_dir)
if os.path.exists(spec_file):
    os.remove(spec_file)

# Параметры для PyInstaller
PyInstaller.__main__.run([
    '--name=ZayavkiOIRIT',
    '--onefile',  # Создать один exe файл
    '--windowed',  # Без консольного окна (убрать, если нужно видеть логи в консоли)
    '--add-data=config.json;.',  # Добавить config.json (разделитель ; для Windows, : для Linux/Mac)
    '--add-data=templates;templates',  # Добавить папку templates
    '--hidden-import=flask',
    '--hidden-import=flask_login',
    '--hidden-import=flask_sqlalchemy',
    '--hidden-import=flask_migrate',
    '--hidden-import=ldap3',
    '--hidden-import=smtplib',
    '--hidden-import=email',
    app_path,
])

print("\nСборка завершена!")
print(f"EXE файл находится в папке: {os.path.join(dist_dir, 'ZayavkiOIRIT.exe')}")
print("\nПримечание:")
print("- Для Windows используется разделитель ';' в --add-data")
print("- Если собираете на Linux/Mac для запуска на Windows, используйте cross-compilation или соберите непосредственно на Windows")
print("- Убедитесь, что все зависимости установлены: pip install -r requirements.txt")
print("- Перед запуском на сервере проверьте права доступа и пути к файлам конфигурации")
