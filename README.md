# 🔧 EAD Oleohidráulica - Sistema de Gestión de Servicios

Sistema web completo para la gestión de equipos, trabajos y servicios de mantenimiento oleohidráulico.

## 🚀 Características Principales

### 📊 Dashboard Interactivo
- **Widget de tiempo real** con reloj, fecha y cotización del dólar oficial
- **Estadísticas en tiempo real** de equipos y trabajos
- **Próximos servicios** con filtros y acciones rápidas
- **Navegación clickeable** en tarjetas y elementos

### 🚛 Gestión de Equipos
- **Registro completo** de equipos con validación
- **Historial de mantenimientos** detallado
- **Navegación intuitiva** con elementos clickables
- **Búsqueda y filtros** avanzados

### 🔧 Gestión de Trabajos
- **Registro de trabajos** con fecha y descripción
- **Cálculo automático** de presupuestos
- **Estados de servicio** (pendiente, en progreso, completado)
- **Alertas de vencimiento** automáticas

### 👥 Gestión de Clientes
- **Lista de clientes** extraída automáticamente
- **Estadísticas por cliente** (equipos, trabajos, gastos)
- **Historial completo** de servicios
- **Edición de información** del cliente

### 📈 Importación de Excel
- **Parser ultra-robusto** que interpreta correctamente archivos Excel complejos
- **Estructura inteligente** que agrupa repuestos y mano de obra
- **Validación previa** con vista previa de datos
- **Importación masiva** con manejo de errores

### 🎨 Interfaz Moderna
- **Diseño responsive** para móvil y desktop
- **Bootstrap 5** con componentes modernos
- **Animaciones suaves** y efectos visuales
- **Tema corporativo** con colores EAD

## 🛠️ Tecnologías Utilizadas

### Backend
- **Flask 3.0** - Framework web Python
- **Peewee ORM** - Manejo de base de datos SQLite
- **Flask-Caching** - Sistema de caché
- **Flask-WTF** - Validación de formularios
- **Requests** - Consumo de APIs externas

### Frontend
- **Bootstrap 5** - Framework CSS responsive
- **Chart.js** - Gráficos interactivos
- **Bootstrap Icons** - Iconografía moderna
- **JavaScript ES6+** - Interactividad avanzada

### Procesamiento de Datos
- **openpyxl** - Lectura de archivos Excel
- **pandas** - Análisis y manipulación de datos
- **python-dotenv** - Gestión de configuración

## 📦 Instalación

### Requisitos Previos
- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
git clone https://github.com/Aguus1610/EAD-ServicesManagement2.git
cd EAD-ServicesManagement2
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno** (opcional)
```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

5. **Ejecutar la aplicación**
```bash
python app_web.py
```

6. **Acceder a la aplicación**
- Abrir navegador en `http://localhost:5000`

## 🔧 Configuración

### Variables de Entorno
Crear archivo `.env` en la raíz del proyecto:

```env
# Configuración de Flask
FLASK_ENV=development
SECRET_KEY=tu_clave_secreta_aqui

# Configuración de base de datos
DATABASE_PATH=equipos.db

# Configuración de caché
CACHE_TYPE=simple
CACHE_DEFAULT_TIMEOUT=300

# Configuración de uploads
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216
```

### Estructura de Archivos Excel
Para importar datos, el Excel debe tener esta estructura por hoja:

```
Hoja: NOMBRE_CLIENTE
Fila 3: EQUIPO | FECHA | REPUESTOS | MANO DE OBRA
Fila 4: Nombre Equipo | 2024-01-15 | Repuesto 1 | Trabajo realizado
Fila 5: (vacío) | (vacío) | Repuesto 2 | Más trabajo
...
```

## 🎯 Funcionalidades Avanzadas

### Widget de Información en Tiempo Real
- **Reloj sincronizado** con el servidor
- **Cotización del dólar** desde APIs oficiales (DolarAPI, Bluelytics)
- **Actualización automática** cada segundo (reloj) y 5 minutos (dólar)
- **Estados visuales** con indicadores de conexión

### Sistema de Caché Inteligente
- **Caché de rutas** para mejorar rendimiento
- **Invalidación automática** cuando se modifican datos
- **Configuración flexible** por entorno

### Validación Robusta
- **Validación server-side** de todos los formularios
- **Mensajes de error** claros y específicos
- **Prevención de datos duplicados**

### Parser Excel Ultra-Robusto
- **Detección automática** de estructura de datos
- **Agrupación inteligente** de múltiples filas por trabajo
- **Manejo de fechas** en múltiples formatos
- **Extracción automática** de costos

## 📱 Responsive Design

La aplicación está completamente optimizada para:
- **📱 Móviles** - Interfaz táctil optimizada
- **💻 Tablets** - Layout adaptativo
- **🖥️ Desktop** - Experiencia completa

## 🔒 Seguridad

- **Validación de entrada** en todos los formularios
- **Sanitización de datos** antes de almacenar
- **Manejo seguro** de archivos subidos
- **Configuración por entornos** (desarrollo/producción)

## 🚀 Despliegue

### Desarrollo Local
```bash
python app_web.py
```

### Producción con Gunicorn
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app_web:app
```

### Docker (opcional)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app_web:app"]
```

## 📊 APIs Disponibles

### Información en Tiempo Real
- `GET /api/tiempo` - Fecha y hora del servidor
- `GET /api/dolar` - Cotización del dólar oficial

### Gestión de Datos
- `POST /admin/upload-excel` - Subir archivo Excel
- `GET /admin/validate-excel/<filename>` - Validar Excel
- `POST /admin/import-excel/<filename>` - Importar datos
- `POST /admin/clear-data` - Limpiar base de datos

## 🤝 Contribuir

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📝 Changelog

### v2.0.0 (2025-01-01)
- ✨ **Widget de tiempo real** con reloj y cotización del dólar
- 🔧 **Parser Excel ultra-robusto** que procesa correctamente archivos complejos
- 👥 **Sistema de gestión de clientes** completo
- 🎨 **Interfaz completamente renovada** con Bootstrap 5
- ⚡ **Sistema de caché inteligente** para mejor rendimiento
- 📱 **Diseño responsive** optimizado para todos los dispositivos
- 🔒 **Validación robusta** en todos los formularios
- 🚀 **Navegación clickeable** en tarjetas y elementos

### v1.0.0 (2024-12-01)
- 🎉 Versión inicial del sistema
- 📊 Dashboard básico
- 🚛 Gestión de equipos
- 🔧 Gestión de trabajos

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 👨‍💻 Autor

**Agustín** - [Aguus1610](https://github.com/Aguus1610)

## 🙏 Agradecimientos

- Bootstrap team por el excelente framework CSS
- Flask community por la documentación
- Chart.js por los gráficos interactivos
- DolarAPI y Bluelytics por las APIs de cotización

---

⭐ **¡Dale una estrella al proyecto si te resulta útil!**
