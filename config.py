"""
Configuración de la aplicación EAD Oleohidráulica
"""
import os
from datetime import timedelta
from pathlib import Path


class Config:
    """Configuración base"""
    
    # Configuración básica de Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production-2025-ead'
    
    # Base de datos
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'agenda_taller.db'
    DATABASE_URL = os.environ.get('DATABASE_URL') or f'sqlite:///{DATABASE_PATH}'
    
    # Configuración de seguridad
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hora
    
    # Configuración de sesiones
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configuración de archivos
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    
    # Configuración de logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or 'app.log'
    
    # Configuración de paginación
    EQUIPOS_PER_PAGE = int(os.environ.get('EQUIPOS_PER_PAGE') or 20)
    TRABAJOS_PER_PAGE = int(os.environ.get('TRABAJOS_PER_PAGE') or 50)
    
    # Configuración de cache
    CACHE_TYPE = os.environ.get('CACHE_TYPE') or 'simple'
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT') or 300)
    
    # Configuración de notificaciones
    ENABLE_EMAIL_NOTIFICATIONS = os.environ.get('ENABLE_EMAIL_NOTIFICATIONS', 'False').lower() == 'true'
    SMTP_SERVER = os.environ.get('SMTP_SERVER')
    SMTP_PORT = int(os.environ.get('SMTP_PORT') or 587)
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'True').lower() == 'true'
    
    # Configuración de backup
    BACKUP_FOLDER = os.environ.get('BACKUP_FOLDER') or 'backups'
    AUTO_BACKUP_ENABLED = os.environ.get('AUTO_BACKUP_ENABLED', 'True').lower() == 'true'
    AUTO_BACKUP_INTERVAL_HOURS = int(os.environ.get('AUTO_BACKUP_INTERVAL_HOURS') or 24)
    
    # Configuración de la aplicación
    APP_NAME = 'EAD Oleohidráulica - Sistema de Gestión'
    APP_VERSION = '1.1.0'
    COMPANY_NAME = 'ENZO A. DEUX'
    
    # Configuración de API
    API_RATE_LIMIT = os.environ.get('API_RATE_LIMIT') or '100 per hour'
    
    @staticmethod
    def init_app(app):
        """Inicializar configuración específica de la aplicación"""
        # Crear directorios necesarios
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.BACKUP_FOLDER, exist_ok=True)


class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    TESTING = False
    
    # Configuración de base de datos para desarrollo
    DATABASE_PATH = 'dev_agenda_taller.db'
    
    # Logging más detallado en desarrollo
    LOG_LEVEL = 'DEBUG'
    
    # Desactivar HTTPS en desarrollo
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """Configuración para testing"""
    TESTING = True
    DEBUG = True
    
    # Base de datos en memoria para tests
    DATABASE_PATH = ':memory:'
    DATABASE_URL = 'sqlite:///:memory:'
    
    # Desactivar CSRF en tests
    WTF_CSRF_ENABLED = False
    
    # Configuración de logging para tests
    LOG_LEVEL = 'WARNING'


class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    TESTING = False
    
    # Configuración de seguridad estricta en producción
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_ENABLED = True
    
    # Logging más restrictivo en producción
    LOG_LEVEL = 'WARNING'
    
    # Rate limiting más estricto
    API_RATE_LIMIT = '50 per hour'
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Configuración específica de producción
        import logging
        from logging.handlers import RotatingFileHandler
        
        # Configurar logging con rotación de archivos
        if not app.debug and not app.testing:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            
            file_handler = RotatingFileHandler(
                'logs/ead_app.log', 
                maxBytes=10240000,  # 10MB
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            
            app.logger.setLevel(logging.INFO)
            app.logger.info('EAD Oleohidráulica startup')


# Configuraciones disponibles
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Obtener configuración basada en variable de entorno"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])


# Utilidades de configuración
class ConfigValidator:
    """Validador de configuración"""
    
    @staticmethod
    def validate_required_env_vars():
        """Validar variables de entorno requeridas en producción"""
        if os.environ.get('FLASK_ENV') == 'production':
            required_vars = [
                'SECRET_KEY',
                'DATABASE_URL'
            ]
            
            missing_vars = []
            for var in required_vars:
                if not os.environ.get(var):
                    missing_vars.append(var)
            
            if missing_vars:
                raise ValueError(
                    f"Variables de entorno requeridas no encontradas: {', '.join(missing_vars)}"
                )
    
    @staticmethod
    def validate_database_connection(database_url):
        """Validar conexión a base de datos"""
        try:
            if database_url.startswith('sqlite://'):
                db_path = database_url.replace('sqlite:///', '')
                if db_path != ':memory:':
                    # Verificar que el directorio existe
                    db_dir = os.path.dirname(db_path)
                    if db_dir and not os.path.exists(db_dir):
                        os.makedirs(db_dir, exist_ok=True)
            return True
        except Exception as e:
            raise ValueError(f"Error validando conexión a base de datos: {e}")
    
    @staticmethod
    def validate_smtp_config():
        """Validar configuración SMTP si está habilitada"""
        if Config.ENABLE_EMAIL_NOTIFICATIONS:
            required_smtp_vars = ['SMTP_SERVER', 'SMTP_USERNAME', 'SMTP_PASSWORD']
            missing_vars = []
            
            for var in required_smtp_vars:
                if not os.environ.get(var):
                    missing_vars.append(var)
            
            if missing_vars:
                raise ValueError(
                    f"Configuración SMTP incompleta. Variables faltantes: {', '.join(missing_vars)}"
                )


# Configuración de constantes de la aplicación
class AppConstants:
    """Constantes de la aplicación"""
    
    # Límites de validación
    MAX_EQUIPMENT_NAME_LENGTH = 100
    MAX_SERIAL_NUMBER_LENGTH = 50
    MAX_DESCRIPTION_LENGTH = 2000
    MAX_NOTES_LENGTH = 1000
    
    # Rangos de años válidos
    MIN_EQUIPMENT_YEAR = 1900
    MAX_EQUIPMENT_YEAR = 2030
    
    # Configuración de archivos
    ALLOWED_EXPORT_FORMATS = ['csv', 'xlsx', 'pdf']
    MAX_EXPORT_RECORDS = 10000
    
    # Configuración de servicios
    DEFAULT_SERVICE_INTERVAL_DAYS = 90
    MAX_SERVICE_INTERVAL_DAYS = 365 * 5  # 5 años
    
    # Configuración de búsqueda
    MIN_SEARCH_LENGTH = 2
    MAX_SEARCH_RESULTS = 100
    
    # Configuración de paginación
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # Códigos de estado HTTP personalizados
    HTTP_VALIDATION_ERROR = 422
    HTTP_BUSINESS_LOGIC_ERROR = 409
