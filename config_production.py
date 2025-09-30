"""
Configuración específica para producción en Render
"""
import os
from datetime import timedelta

class ProductionConfig:
    """Configuración para entorno de producción"""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'fallback-secret-key-change-in-production'
    DEBUG = False
    TESTING = False
    
    # Base de datos
    DATABASE_PATH = os.environ.get('DATABASE_PATH', '/opt/render/project/src/equipos.db')
    
    # Uploads
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    
    # Cache
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))
    
    # Seguridad
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # CORS (si es necesario)
    CORS_ORIGINS = ['https://ead-oleohidraulica.onrender.com']
    
    # Logging
    LOG_LEVEL = 'INFO'
    
    @staticmethod
    def init_app(app):
        """Inicializar configuración específica de producción"""
        
        # Crear directorio de uploads si no existe
        upload_folder = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder, exist_ok=True)
        
        # Configurar logging para producción
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not app.debug and not app.testing:
            # Log a archivo si es posible, sino a stdout
            try:
                file_handler = RotatingFileHandler(
                    '/tmp/ead-app.log', 
                    maxBytes=10240000, 
                    backupCount=10
                )
                file_handler.setFormatter(logging.Formatter(
                    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
                ))
                file_handler.setLevel(logging.INFO)
                app.logger.addHandler(file_handler)
            except:
                # Si no se puede escribir archivo, usar stdout
                import sys
                stream_handler = logging.StreamHandler(sys.stdout)
                stream_handler.setLevel(logging.INFO)
                app.logger.addHandler(stream_handler)
            
            app.logger.setLevel(logging.INFO)
            app.logger.info('EAD Oleohidráulica startup - Production Mode')

# Configuración para diferentes entornos
config = {
    'production': ProductionConfig,
    'default': ProductionConfig
}
