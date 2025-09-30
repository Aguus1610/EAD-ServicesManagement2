"""
Script de inicialización para Render
Prepara la aplicación para el entorno de producción
"""
import os
import sys
import sqlite3
from pathlib import Path

def create_directories():
    """Crear directorios necesarios"""
    directories = [
        '/tmp/uploads',
        '/opt/render/project/src/static',
        '/opt/render/project/src/templates'
    ]
    
    for directory in directories:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            print(f"✅ Directorio creado/verificado: {directory}")
        except Exception as e:
            print(f"⚠️ No se pudo crear directorio {directory}: {e}")

def init_database():
    """Inicializar base de datos si no existe"""
    db_path = os.environ.get('DATABASE_PATH', '/opt/render/project/src/equipos.db')
    
    try:
        # Crear directorio de la base de datos si no existe
        db_dir = os.path.dirname(db_path)
        Path(db_dir).mkdir(parents=True, exist_ok=True)
        
        # Verificar si la base de datos existe
        if not os.path.exists(db_path):
            print(f"📄 Creando base de datos en: {db_path}")
            
            # Importar y ejecutar la inicialización de la app
            sys.path.append('/opt/render/project/src')
            from app_web import init_db
            init_db()
            
            print("✅ Base de datos inicializada correctamente")
        else:
            print(f"✅ Base de datos ya existe en: {db_path}")
            
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")
        # No fallar completamente, la app puede crear la DB automáticamente
        pass

def check_environment():
    """Verificar variables de entorno necesarias"""
    required_vars = [
        'SECRET_KEY',
        'FLASK_ENV',
        'DATABASE_PATH',
        'UPLOAD_FOLDER'
    ]
    
    print("🔍 Verificando variables de entorno:")
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            # No mostrar el SECRET_KEY completo por seguridad
            display_value = value if var != 'SECRET_KEY' else f"{value[:8]}..."
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ⚠️ {var}: No definida")

def main():
    """Función principal de inicialización"""
    print("🚀 Inicializando EAD Oleohidráulica para Render...")
    
    # Verificar entorno
    check_environment()
    
    # Crear directorios
    create_directories()
    
    # Inicializar base de datos
    init_database()
    
    print("✅ Inicialización completada!")

if __name__ == "__main__":
    main()
