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
        print(f"📁 Directorio de BD creado/verificado: {db_dir}")
        
        # Siempre intentar crear/verificar las tablas
        print(f"📄 Inicializando base de datos en: {db_path}")
        
        # Configurar variables de entorno necesarias antes de importar
        if not os.environ.get('DATABASE_URL'):
            os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
        if not os.environ.get('SECRET_KEY'):
            os.environ['SECRET_KEY'] = 'render-init-key-temp'
        if not os.environ.get('FLASK_ENV'):
            os.environ['FLASK_ENV'] = 'production'
            
        # Importar y ejecutar la inicialización
        sys.path.insert(0, '/opt/render/project/src')
        
        # Importar los modelos y la función de inicialización
        from app_web import Equipment, Job, db, init_db
        
        # Conectar y crear tablas
        print("🔗 Conectando a la base de datos...")
        db.connect()
        
        print("🏗️ Creando tablas...")
        db.create_tables([Equipment, Job], safe=True)
        
        print("✅ Base de datos inicializada correctamente")
        
        # Verificar que las tablas existen
        tables = db.get_tables()
        print(f"📊 Tablas creadas: {tables}")
        
        db.close()
        
    except ImportError as e:
        print(f"⚠️ Error de importación: {e}")
        # Crear base de datos básica manualmente
        create_basic_database(db_path)
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")
        print(f"🔧 Intentando crear base de datos básica...")
        create_basic_database(db_path)

def create_basic_database(db_path):
    """Crear base de datos básica con SQL directo"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Crear tabla equipment
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equipment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                serial_number VARCHAR(50),
                brand VARCHAR(50),
                model VARCHAR(50),
                year INTEGER,
                equipment_type VARCHAR(50),
                owner VARCHAR(100),
                location VARCHAR(100),
                status VARCHAR(20) DEFAULT 'Activo',
                purchase_date DATE,
                warranty_expiry DATE,
                last_service_date DATE,
                next_service_date DATE,
                notes TEXT
            )
        ''')
        
        # Crear tabla job
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id INTEGER NOT NULL,
                fecha DATE NOT NULL,
                descripcion TEXT NOT NULL,
                presupuesto DECIMAL(10,2),
                estado VARCHAR(20) DEFAULT 'Pendiente',
                tecnico VARCHAR(100),
                prioridad VARCHAR(20) DEFAULT 'Media',
                fecha_completado DATE,
                notas TEXT,
                FOREIGN KEY (equipment_id) REFERENCES equipment (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        print("✅ Base de datos básica creada con SQL directo")
        
    except Exception as e:
        print(f"❌ Error creando base de datos básica: {e}")

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
