"""
AgendaTaller Web - Aplicación web responsive para gestión de trabajos y mantenimientos
Tecnologías: Flask, Bootstrap 5, Chart.js, SQLite
Autor: AgendaTaller
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash
from flask_caching import Cache
from datetime import datetime, timedelta
import json
import csv
import io
import os
import logging
import traceback
from peewee import SqliteDatabase, Model, CharField, DateField, TextField, IntegerField, FloatField, ForeignKeyField, fn
from utils.validators import ValidationError, validate_equipment_data, validate_job_data
from utils.excel_importer import ExcelImporter, DatabaseImporter, clear_all_data, validate_excel_file
from utils.excel_importer_v2 import ExcelImporterV2, validate_excel_file_v2
from utils.excel_parser_final import ExcelParserFinal, validate_excel_file_final
import os
from werkzeug.utils import secure_filename
import requests
from datetime import datetime, timedelta
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de Flask
from config import get_config, ConfigValidator
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Validar configuración
try:
    # En producción, crear DATABASE_URL si no existe pero DATABASE_PATH sí
    if os.environ.get('FLASK_ENV') == 'production' and not os.environ.get('DATABASE_URL'):
        database_path = os.environ.get('DATABASE_PATH', '/opt/render/project/src/equipos.db')
        os.environ['DATABASE_URL'] = f'sqlite:///{database_path}'
        logger.info(f"DATABASE_URL generada automáticamente: {os.environ['DATABASE_URL']}")
    
    ConfigValidator.validate_required_env_vars()
    ConfigValidator.validate_database_connection(os.environ.get('DATABASE_URL', 'sqlite:///agenda_taller.db'))
except ValueError as e:
    logger.error(f"Error de configuración: {e}")
    # En desarrollo, continuar con advertencia
    if os.environ.get('FLASK_ENV') != 'production':
        logger.warning("Continuando en modo desarrollo con configuración por defecto")
    else:
        # En producción, intentar configuración por defecto como último recurso
        if not os.environ.get('DATABASE_URL'):
            default_db_path = '/opt/render/project/src/equipos.db'
            os.environ['DATABASE_URL'] = f'sqlite:///{default_db_path}'
            logger.warning(f"Usando DATABASE_URL por defecto: {os.environ['DATABASE_URL']}")
        if not os.environ.get('SECRET_KEY'):
            import secrets
            os.environ['SECRET_KEY'] = secrets.token_urlsafe(32)
            logger.warning("SECRET_KEY generada automáticamente")
        # Intentar continuar
        logger.warning("Continuando con configuración generada automáticamente")

app = Flask(__name__)
config_class = get_config()
app.config.from_object(config_class)
config_class.init_app(app)

# Inicializar sistema de caché
cache = Cache(app)

# Manejador de errores global
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Error interno del servidor: {error}")
    logger.error(traceback.format_exc())
    return render_template('error.html', 
                         error_code=500,
                         error_message="Error interno del servidor"), 500

@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"Página no encontrada: {request.url}")
    return render_template('error.html',
                         error_code=404,
                         error_message="Página no encontrada"), 404

# Ruta para favicon
@app.route('/favicon.ico')
def favicon():
    return send_file('static/img/EAD negro (snf).png', mimetype='image/png')

# Base de datos
DB_FILENAME = 'agenda_taller.db'
db = SqliteDatabase(DB_FILENAME)

# ---------------------------- MODELOS ----------------------------
class BaseModel(Model):
    class Meta:
        database = db

class Equipment(BaseModel):
    marca = CharField()
    modelo = CharField()
    anio = IntegerField()
    n_serie = CharField()
    propietario = CharField(null=True)
    vehiculo = CharField(null=True)
    dominio = CharField(null=True)
    notes = TextField(null=True)

class Job(BaseModel):
    equipment = ForeignKeyField(Equipment, backref='jobs', on_delete='CASCADE')
    date_done = DateField()
    description = TextField()
    budget = FloatField(default=0.0)
    next_service_days = IntegerField(null=True)
    next_service_date = DateField(null=True)
    notes = TextField(null=True)

def init_db():
    """Inicializar base de datos"""
    db.connect()
    db.create_tables([Equipment, Job])

# ---------------------------- FUNCIONES DE CACHÉ ----------------------------

@cache.memoize(timeout=600)  # Cache por 10 minutos
def get_cached_equipment_count():
    """Obtener conteo de equipos con caché"""
    return Equipment.select().count()

@cache.memoize(timeout=600)  # Cache por 10 minutos  
def get_cached_jobs_count():
    """Obtener conteo de trabajos con caché"""
    return Job.select().count()

@cache.memoize(timeout=300)  # Cache por 5 minutos
def get_cached_upcoming_services():
    """Obtener servicios próximos con caché"""
    today = datetime.now().date()
    upcoming_services = []
    total_upcoming = 0
    services_vencidos = 0
    
    try:
        for eq in Equipment.select():
            last_job = Job.select().where(Job.equipment == eq).order_by(Job.date_done.desc()).first()
            if last_job and last_job.next_service_date:
                days_left = (last_job.next_service_date - today).days
                
                # Contar todos los servicios próximos (30 días o menos)
                if days_left <= 30:
                    total_upcoming += 1
                
                # Contar servicios vencidos
                if days_left < 0:
                    services_vencidos += 1
                    
                upcoming_services.append({
                    'equipment': f"{eq.marca} {eq.modelo} ({eq.anio})",
                    'propietario': eq.propietario,
                    'date': last_job.next_service_date.strftime('%d/%m/%Y'),
                    'days_left': days_left,
                    'budget': last_job.budget,
                    'status': 'danger' if days_left < 0 else 'warning' if days_left < 7 else 'success'
                })
        
        upcoming_services.sort(key=lambda x: x['days_left'])
        
        return {
            'upcoming_services': upcoming_services,
            'total_upcoming': total_upcoming,
            'services_vencidos': services_vencidos
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo servicios próximos: {e}")
        return {
            'upcoming_services': [],
            'total_upcoming': 0,
            'services_vencidos': 0
        }

@cache.memoize(timeout=1800)  # Cache por 30 minutos
def get_cached_equipment_autocomplete():
    """Obtener datos para autocompletado con caché"""
    try:
        marcas = list(set([eq.marca for eq in Equipment.select()]))
        modelos = list(set([eq.modelo for eq in Equipment.select()]))
        propietarios = list(set([eq.propietario for eq in Equipment.select() if eq.propietario]))
        return {
            'marcas': marcas,
            'modelos': modelos,
            'propietarios': propietarios
        }
    except Exception as e:
        logger.error(f"Error obteniendo datos de autocompletado: {e}")
        return {
            'marcas': [],
            'modelos': [],
            'propietarios': []
        }

def clear_cache_on_equipment_change():
    """Limpiar caché relacionado con equipos"""
    cache.delete_memoized(get_cached_equipment_count)
    cache.delete_memoized(get_cached_equipment_autocomplete)
    cache.delete_memoized(get_cached_upcoming_services)
    cache.delete('view//')  # Limpiar caché del dashboard

def clear_cache_on_job_change():
    """Limpiar caché relacionado con trabajos"""
    cache.delete_memoized(get_cached_jobs_count)
    cache.delete_memoized(get_cached_upcoming_services)
    cache.delete('view//')  # Limpiar caché del dashboard

# ---------------------------- RUTAS PRINCIPALES ----------------------------

@app.route('/')
@cache.cached(timeout=300)  # Cache por 5 minutos
def index():
    """Página principal - Dashboard con caché optimizado"""
    try:
        # Obtener estadísticas básicas con caché
        total_equipment = get_cached_equipment_count()
        total_jobs = get_cached_jobs_count()
        
        # Próximos servicios
        upcoming_services_data = get_cached_upcoming_services()
        
        return render_template('dashboard.html',
                             total_equipment=total_equipment,
                             total_jobs=total_jobs,
                             total_upcoming=upcoming_services_data['total_upcoming'],
                             services_vencidos=upcoming_services_data['services_vencidos'],
                             upcoming_services=upcoming_services_data['upcoming_services'][:10])
    
    except Exception as e:
        logger.error(f"Error en dashboard: {e}")
        logger.error(traceback.format_exc())
        flash('Error cargando el dashboard. Inténtelo nuevamente.', 'error')
        return render_template('dashboard.html',
                             total_equipment=0,
                             total_jobs=0,
                             total_upcoming=0,
                             services_vencidos=0,
                             upcoming_services=[])

# ---------------------------- RUTAS DE EQUIPOS ----------------------------

@app.route('/equipos')
def equipos_list():
    """Lista de equipos con búsqueda"""
    search = request.args.get('search', '')
    equipos = Equipment.select().order_by(Equipment.marca, Equipment.modelo)
    
    if search:
        equipos = equipos.where(
            (Equipment.marca.contains(search)) |
            (Equipment.modelo.contains(search)) |
            (Equipment.n_serie.contains(search)) |
            (Equipment.propietario.contains(search)) |
            (Equipment.dominio.contains(search))
        )
    
    equipos_list = []
    for eq in equipos:
        job_count = Job.select().where(Job.equipment == eq).count()
        total_spent = Job.select(fn.SUM(Job.budget)).where(Job.equipment == eq).scalar() or 0
        
        equipos_list.append({
            'id': eq.id,
            'marca': eq.marca,
            'modelo': eq.modelo,
            'anio': eq.anio,
            'n_serie': eq.n_serie,
            'propietario': eq.propietario or '-',
            'vehiculo': eq.vehiculo or '-',
            'dominio': eq.dominio or '-',
            'job_count': job_count,
            'total_spent': total_spent
        })
    
    return render_template('equipos.html', equipos=equipos_list, search=search)

@app.route('/equipo/<int:equipo_id>')
def equipo_detail(equipo_id):
    """Detalle de equipo con trabajos"""
    equipo = Equipment.get_by_id(equipo_id)
    trabajos = Job.select().where(Job.equipment == equipo).order_by(Job.date_done.desc())
    
    trabajos_list = []
    total_gastado = 0
    
    for job in trabajos:
        trabajos_list.append({
            'id': job.id,
            'date': job.date_done.strftime('%d/%m/%Y'),
            'description': job.description,
            'budget': job.budget,
            'next_service': job.next_service_date.strftime('%d/%m/%Y') if job.next_service_date else '-',
            'notes': job.notes or ''
        })
        total_gastado += job.budget
    
    promedio = total_gastado / len(trabajos_list) if trabajos_list else 0
    
    return render_template('equipo_detail.html',
                         equipo=equipo,
                         trabajos=trabajos_list,
                         total_gastado=total_gastado,
                         promedio=promedio)

@app.route('/equipo/nuevo', methods=['GET', 'POST'])
def equipo_new():
    """Crear nuevo equipo con validaciones mejoradas"""
    if request.method == 'POST':
        try:
            # Obtener y validar datos del formulario
            form_data = {
                'marca': request.form.get('marca', '').strip(),
                'modelo': request.form.get('modelo', '').strip(),
                'anio': request.form.get('anio', '').strip(),
                'n_serie': request.form.get('n_serie', '').strip(),
                'propietario': request.form.get('propietario', '').strip(),
                'vehiculo': request.form.get('vehiculo', '').strip(),
                'dominio': request.form.get('dominio', '').strip(),
                'notes': request.form.get('notes', '').strip()
            }
            
            # Validar datos
            validated_data = validate_equipment_data(form_data)
            
            # Verificar que el número de serie no exista
            existing = Equipment.select().where(Equipment.n_serie == validated_data['n_serie']).first()
            if existing:
                flash('Ya existe un equipo con ese número de serie', 'error')
                raise ValidationError('Número de serie duplicado')
            
            # Crear equipo
            Equipment.create(
                marca=validated_data['marca'],
                modelo=validated_data['modelo'],
                anio=int(validated_data['anio']),
                n_serie=validated_data['n_serie'],
                propietario=validated_data['propietario'] or None,
                vehiculo=validated_data['vehiculo'] or None,
                dominio=validated_data['dominio'] or None,
                notes=validated_data['notes'] or None
            )
            
            # Limpiar caché después de crear equipo
            clear_cache_on_equipment_change()
            
            flash(f'Equipo {validated_data["marca"]} {validated_data["modelo"]} creado exitosamente', 'success')
            return redirect(url_for('equipos_list'))
            
        except ValidationError as e:
            flash(f'Error de validación: {str(e)}', 'error')
            logger.warning(f"Error de validación en equipo nuevo: {e}")
        except Exception as e:
            flash('Error interno al crear el equipo. Inténtelo nuevamente.', 'error')
            logger.error(f"Error creando equipo: {e}")
            logger.error(traceback.format_exc())
    
    # Obtener valores únicos para autocompletado con caché
    autocomplete_data = get_cached_equipment_autocomplete()
    
    return render_template('equipo_form.html', 
                         equipo=None,
                         marcas=json.dumps(autocomplete_data['marcas']),
                         modelos=json.dumps(autocomplete_data['modelos']),
                         propietarios=json.dumps(autocomplete_data['propietarios']))

@app.route('/equipo/<int:equipo_id>/editar', methods=['GET', 'POST'])
def equipo_edit(equipo_id):
    """Editar equipo existente con validaciones mejoradas"""
    try:
        equipo = Equipment.get_by_id(equipo_id)
    except Equipment.DoesNotExist:
        flash('Equipo no encontrado', 'error')
        return redirect(url_for('equipos_list'))
    
    if request.method == 'POST':
        try:
            # Obtener y validar datos del formulario
            form_data = {
                'marca': request.form.get('marca', '').strip(),
                'modelo': request.form.get('modelo', '').strip(),
                'anio': request.form.get('anio', '').strip(),
                'n_serie': request.form.get('n_serie', '').strip(),
                'propietario': request.form.get('propietario', '').strip(),
                'vehiculo': request.form.get('vehiculo', '').strip(),
                'dominio': request.form.get('dominio', '').strip(),
                'notes': request.form.get('notes', '').strip()
            }
            
            # Validar datos
            validated_data = validate_equipment_data(form_data)
            
            # Verificar que el número de serie no exista en otro equipo
            existing = Equipment.select().where(
                (Equipment.n_serie == validated_data['n_serie']) & 
                (Equipment.id != equipo_id)
            ).first()
            if existing:
                flash('Ya existe otro equipo con ese número de serie', 'error')
                raise ValidationError('Número de serie duplicado')
            
            # Actualizar equipo
            equipo.marca = validated_data['marca']
            equipo.modelo = validated_data['modelo']
            equipo.anio = int(validated_data['anio'])
            equipo.n_serie = validated_data['n_serie']
            equipo.propietario = validated_data['propietario'] or None
            equipo.vehiculo = validated_data['vehiculo'] or None
            equipo.dominio = validated_data['dominio'] or None
            equipo.notes = validated_data['notes'] or None
            equipo.save()
            
            flash(f'Equipo {validated_data["marca"]} {validated_data["modelo"]} actualizado exitosamente', 'success')
            return redirect(url_for('equipo_detail', equipo_id=equipo_id))
            
        except ValidationError as e:
            flash(f'Error de validación: {str(e)}', 'error')
            logger.warning(f"Error de validación editando equipo {equipo_id}: {e}")
        except Exception as e:
            flash('Error interno al actualizar el equipo. Inténtelo nuevamente.', 'error')
            logger.error(f"Error editando equipo {equipo_id}: {e}")
            logger.error(traceback.format_exc())
    
    # Obtener valores únicos para autocompletado
    try:
        marcas = list(set([eq.marca for eq in Equipment.select()]))
        modelos = list(set([eq.modelo for eq in Equipment.select()]))
        propietarios = list(set([eq.propietario for eq in Equipment.select() if eq.propietario]))
    except Exception as e:
        logger.error(f"Error obteniendo datos para autocompletado: {e}")
        marcas = []
        modelos = []
        propietarios = []
    
    return render_template('equipo_form.html',
                         equipo=equipo,
                         marcas=json.dumps(marcas),
                         modelos=json.dumps(modelos),
                         propietarios=json.dumps(propietarios))

@app.route('/equipo/<int:equipo_id>/eliminar', methods=['POST'])
def equipo_delete(equipo_id):
    """Eliminar equipo"""
    try:
        equipo = Equipment.get_by_id(equipo_id)
        # Eliminar equipo y trabajos asociados de forma recursiva
        equipo.delete_instance(recursive=True)
        return redirect(url_for('equipos_list'))
    except Exception as e:
        logger.error(f"Error eliminando equipo {equipo_id}: {e}")
        logger.error(traceback.format_exc())
        return redirect(url_for('equipos_list'))

# ---------------------------- RUTAS DE TRABAJOS ----------------------------

@app.route('/trabajos')
def trabajos_list():
    """Lista de todos los trabajos con filtros"""
    # Obtener parámetros de filtro
    search = request.args.get('search', '')
    equipo_id = request.args.get('equipo_id', '')
    fecha_desde = request.args.get('fecha_desde', '')
    fecha_hasta = request.args.get('fecha_hasta', '')
    
    # Query base
    trabajos = Job.select().join(Equipment).order_by(Job.date_done.desc())
    
    # Aplicar filtros
    if search:
        trabajos = trabajos.where(Job.description.contains(search))
    if equipo_id:
        trabajos = trabajos.where(Job.equipment == equipo_id)
    if fecha_desde:
        trabajos = trabajos.where(Job.date_done >= datetime.strptime(fecha_desde, '%Y-%m-%d').date())
    if fecha_hasta:
        trabajos = trabajos.where(Job.date_done <= datetime.strptime(fecha_hasta, '%Y-%m-%d').date())
    
    # Preparar datos para la vista
    trabajos_list = []
    total_trabajos = 0
    total_presupuesto = 0
    
    for job in trabajos:
        eq = job.equipment
        trabajos_list.append({
            'id': job.id,
            'date': job.date_done.strftime('%d/%m/%Y'),
            'equipo': f"{eq.marca} {eq.modelo} ({eq.anio})",
            'equipo_id': eq.id,
            'propietario': eq.propietario or '-',
            'description': job.description,
            'budget': job.budget,
            'next_service': job.next_service_date.strftime('%d/%m/%Y') if job.next_service_date else '-',
            'days_until': (job.next_service_date - datetime.now().date()).days if job.next_service_date else None,
            'notes': job.notes or ''
        })
        total_trabajos += 1
        total_presupuesto += job.budget
    
    # Obtener lista de equipos para el filtro
    equipos_filter = []
    for eq in Equipment.select().order_by(Equipment.marca, Equipment.modelo):
        equipos_filter.append({
            'id': eq.id,
            'nombre': f"{eq.marca} {eq.modelo} ({eq.anio})"
        })
    
    return render_template('trabajos.html', 
                         trabajos=trabajos_list,
                         total_trabajos=total_trabajos,
                         total_presupuesto=total_presupuesto,
                         equipos_filter=equipos_filter,
                         search=search,
                         equipo_id=equipo_id,
                         fecha_desde=fecha_desde,
                         fecha_hasta=fecha_hasta)

@app.route('/trabajo/nuevo', methods=['GET', 'POST'])
def trabajo_new_global():
    """Crear nuevo trabajo desde la sección global"""
    if request.method == 'POST':
        equipo_id = request.form['equipo_id']
        equipo = Equipment.get_by_id(equipo_id)
        date_done = datetime.strptime(request.form['date_done'], '%Y-%m-%d').date()
        next_days = int(request.form['next_service_days']) if request.form.get('next_service_days') else None
        next_date = date_done + timedelta(days=next_days) if next_days else None
        
        Job.create(
            equipment=equipo,
            date_done=date_done,
            description=request.form['description'],
            budget=float(request.form.get('budget', 0)),
            next_service_days=next_days,
            next_service_date=next_date,
            notes=request.form.get('notes') or None
        )
        return redirect(url_for('trabajos_list'))
    
    # Obtener lista de equipos
    equipos = []
    for eq in Equipment.select().order_by(Equipment.marca, Equipment.modelo):
        equipos.append({
            'id': eq.id,
            'nombre': f"{eq.marca} {eq.modelo} ({eq.anio}) - {eq.n_serie}"
        })
    
    return render_template('trabajo_form_global.html', equipos=equipos)

@app.route('/trabajo/nuevo/<int:equipo_id>', methods=['GET', 'POST'])
def trabajo_new(equipo_id):
    """Crear nuevo trabajo con validaciones mejoradas"""
    try:
        equipo = Equipment.get_by_id(equipo_id)
    except Equipment.DoesNotExist:
        flash('Equipo no encontrado', 'error')
        return redirect(url_for('equipos_list'))
    
    if request.method == 'POST':
        try:
            # Obtener y validar datos del formulario
            form_data = {
                'date_done': request.form.get('date_done', '').strip(),
                'description': request.form.get('description', '').strip(),
                'budget': request.form.get('budget', '0').strip(),
                'next_service_days': request.form.get('next_service_days', '').strip(),
                'notes': request.form.get('notes', '').strip()
            }
            
            # Validar datos
            validated_data = validate_job_data(form_data)
            
            # Procesar fecha y calcular próximo servicio
            date_done = datetime.strptime(validated_data['date_done'], '%Y-%m-%d').date()
            
            # Validar que la fecha no sea futura
            if date_done > datetime.now().date():
                flash('La fecha del trabajo no puede ser futura', 'error')
                raise ValidationError('Fecha futura no permitida')
            
            next_days = int(validated_data['next_service_days']) if validated_data.get('next_service_days') else None
            next_date = date_done + timedelta(days=next_days) if next_days else None
            budget = float(validated_data['budget']) if validated_data.get('budget') else 0.0
            
            # Crear trabajo
            Job.create(
                equipment=equipo,
                date_done=date_done,
                description=validated_data['description'],
                budget=budget,
                next_service_days=next_days,
                next_service_date=next_date,
                notes=validated_data['notes'] or None
            )
            
            flash(f'Trabajo registrado exitosamente para {equipo.marca} {equipo.modelo}', 'success')
            return redirect(url_for('equipo_detail', equipo_id=equipo_id))
            
        except ValidationError as e:
            flash(f'Error de validación: {str(e)}', 'error')
            logger.warning(f"Error de validación en trabajo nuevo para equipo {equipo_id}: {e}")
        except ValueError as e:
            flash('Error en el formato de fecha o números. Verifique los datos ingresados.', 'error')
            logger.warning(f"Error de formato en trabajo nuevo: {e}")
        except Exception as e:
            flash('Error interno al crear el trabajo. Inténtelo nuevamente.', 'error')
            logger.error(f"Error creando trabajo para equipo {equipo_id}: {e}")
            logger.error(traceback.format_exc())
    
    return render_template('trabajo_form.html', equipo=equipo, trabajo=None)

@app.route('/trabajo/<int:trabajo_id>/editar', methods=['GET', 'POST'])
def trabajo_edit(trabajo_id):
    """Editar trabajo existente"""
    trabajo = Job.get_by_id(trabajo_id)
    
    if request.method == 'POST':
        trabajo.date_done = datetime.strptime(request.form['date_done'], '%Y-%m-%d').date()
        trabajo.description = request.form['description']
        trabajo.budget = float(request.form.get('budget', 0))
        
        next_days = int(request.form['next_service_days']) if request.form.get('next_service_days') else None
        trabajo.next_service_days = next_days
        trabajo.next_service_date = trabajo.date_done + timedelta(days=next_days) if next_days else None
        trabajo.notes = request.form.get('notes') or None
        trabajo.save()
        
        return redirect(url_for('equipo_detail', equipo_id=trabajo.equipment.id))
    
    return render_template('trabajo_form.html', equipo=trabajo.equipment, trabajo=trabajo)

@app.route('/trabajo/<int:trabajo_id>/eliminar', methods=['POST'])
def trabajo_delete(trabajo_id):
    """Eliminar trabajo"""
    try:
        trabajo = Job.get_by_id(trabajo_id)
        equipo_id = trabajo.equipment.id
        trabajo.delete_instance()
        
        # Determinar desde dónde se llamó para redirigir correctamente
        referer = request.headers.get('Referer', '')
        if '/trabajos' in referer:
            # Si viene de la página de trabajos, redirigir ahí
            return redirect(url_for('trabajos_list'))
        else:
            # Si viene del detalle del equipo, redirigir ahí
            return redirect(url_for('equipo_detail', equipo_id=equipo_id))
    except Exception as e:
        logger.error(f"Error eliminando trabajo {trabajo_id}: {e}")
        logger.error(traceback.format_exc())
        # En caso de error, redirigir a trabajos con mensaje de error
        return redirect(url_for('trabajos_list'))

# ---------------------------- RUTAS DE ESTADÍSTICAS ----------------------------

@app.route('/estadisticas')
def estadisticas():
    """Vista de estadísticas con gráficos"""
    # Estadísticas generales
    total_equipment = Equipment.select().count()
    total_jobs = Job.select().count()
    total_budget = Job.select(fn.SUM(Job.budget)).scalar() or 0
    avg_budget = total_budget / total_jobs if total_jobs > 0 else 0
    
    # Top equipos por gastos
    top_equipos = []
    for eq in Equipment.select():
        job_count = Job.select().where(Job.equipment == eq).count()
        if job_count > 0:
            total = Job.select(fn.SUM(Job.budget)).where(Job.equipment == eq).scalar() or 0
            top_equipos.append({
                'name': f"{eq.marca} {eq.modelo}",
                'jobs': job_count,
                'total': total
            })
    
    top_equipos.sort(key=lambda x: x['total'], reverse=True)
    top_equipos = top_equipos[:10]
    
    # Gastos por mes (últimos 12 meses)
    gastos_mes = []
    for i in range(11, -1, -1):
        fecha = datetime.now() - timedelta(days=i*30)
        mes_inicio = fecha.replace(day=1)
        if i == 0:
            mes_fin = datetime.now().date()
        else:
            siguiente_mes = mes_inicio + timedelta(days=32)
            mes_fin = siguiente_mes.replace(day=1) - timedelta(days=1)
        
        total_mes = Job.select(fn.SUM(Job.budget)).where(
            (Job.date_done >= mes_inicio.date()) & 
            (Job.date_done <= mes_fin)
        ).scalar() or 0
        
        gastos_mes.append({
            'month': fecha.strftime('%b %Y'),
            'total': float(total_mes)
        })
    
    # Distribución por marca
    marcas_dist = []
    for marca in Equipment.select(Equipment.marca).distinct():
        count = Equipment.select().where(Equipment.marca == marca.marca).count()
        marcas_dist.append({
            'marca': marca.marca,
            'count': count
        })
    
    return render_template('estadisticas.html',
                         total_equipment=total_equipment,
                         total_jobs=total_jobs,
                         total_budget=total_budget,
                         avg_budget=avg_budget,
                         top_equipos=json.dumps(top_equipos),
                         gastos_mes=json.dumps(gastos_mes),
                         marcas_dist=json.dumps(marcas_dist))

# ---------------------------- API ENDPOINTS ----------------------------

@app.route('/api/modelos/<marca>')
def api_modelos(marca):
    """API: Obtener modelos por marca"""
    modelos = list(set([
        eq.modelo for eq in Equipment.select() 
        if eq.marca == marca
    ]))
    return jsonify(modelos)

@app.route('/api/export/equipos')
def export_equipos():
    """Exportar equipos a CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Marca', 'Modelo', 'Año', 'N° Serie', 'Propietario', 'Vehículo', 'Dominio', 'Notas'])
    
    for eq in Equipment.select():
        writer.writerow([
            eq.id, eq.marca, eq.modelo, eq.anio, eq.n_serie,
            eq.propietario or '', eq.vehiculo or '', eq.dominio or '', eq.notes or ''
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'equipos_{datetime.now().strftime("%Y%m%d")}.csv'
    )

@app.route('/api/export/trabajos')
def export_trabajos():
    """Exportar trabajos a CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Fecha', 'Equipo', 'Marca', 'Modelo', 'Año', 'Propietario', 'Descripción', 'Presupuesto', 'Próximo Service', 'Días para Service', 'Notas'])
    
    for job in Job.select().join(Equipment).order_by(Job.date_done.desc()):
        eq = job.equipment
        writer.writerow([
            job.id,
            job.date_done.strftime('%d/%m/%Y'),
            f"{eq.marca} {eq.modelo}",
            eq.marca,
            eq.modelo,
            eq.anio,
            eq.propietario or '',
            job.description,
            job.budget,
            job.next_service_date.strftime('%d/%m/%Y') if job.next_service_date else '',
            job.next_service_days or '',
            job.notes or ''
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'trabajos_{datetime.now().strftime("%Y%m%d")}.csv'
    )

@app.route('/api/backup')
def backup_database():
    """Descarga una copia de seguridad de la base de datos"""
    try:
        # Verificar que el archivo existe
        if not os.path.exists(DB_FILENAME):
            return jsonify({'error': 'Base de datos no encontrada'}), 404
        
        # Enviar el archivo de base de datos
        return send_file(
            DB_FILENAME,
            mimetype='application/x-sqlite3',
            as_attachment=True,
            download_name=f'backup_ead_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------------------- RUTAS DE CLIENTES ----------------------------

@app.route('/clientes')
def clientes_list():
    """Lista de clientes/propietarios"""
    try:
        search = request.args.get('search', '').strip()
        
        # Obtener todos los propietarios únicos con estadísticas
        clientes_data = []
        
        if search:
            # Buscar equipos que coincidan con el propietario
            equipos_query = Equipment.select().where(
                Equipment.propietario.contains(search)
            )
        else:
            equipos_query = Equipment.select()
        
        # Agrupar por propietario
        propietarios_dict = {}
        
        for equipo in equipos_query:
            propietario = equipo.propietario or 'Sin especificar'
            
            if propietario not in propietarios_dict:
                propietarios_dict[propietario] = {
                    'nombre': propietario,
                    'equipos': [],
                    'total_equipos': 0,
                    'total_trabajos': 0,
                    'total_gastado': 0,
                    'ultimo_trabajo': None
                }
            
            # Agregar equipo
            propietarios_dict[propietario]['equipos'].append(equipo)
            propietarios_dict[propietario]['total_equipos'] += 1
            
            # Calcular trabajos y gastos
            trabajos = Job.select().where(Job.equipment == equipo)
            trabajos_count = trabajos.count()
            total_gastado = sum(trabajo.budget for trabajo in trabajos)
            
            propietarios_dict[propietario]['total_trabajos'] += trabajos_count
            propietarios_dict[propietario]['total_gastado'] += total_gastado
            
            # Último trabajo
            ultimo_trabajo = trabajos.order_by(Job.date_done.desc()).first()
            if ultimo_trabajo:
                if (not propietarios_dict[propietario]['ultimo_trabajo'] or 
                    ultimo_trabajo.date_done > propietarios_dict[propietario]['ultimo_trabajo']):
                    propietarios_dict[propietario]['ultimo_trabajo'] = ultimo_trabajo.date_done
        
        clientes_data = list(propietarios_dict.values())
        clientes_data.sort(key=lambda x: x['total_gastado'], reverse=True)
        
        return render_template('clientes.html', 
                             clientes=clientes_data,
                             search=search,
                             total_clientes=len(clientes_data))
    
    except Exception as e:
        logger.error(f"Error en lista de clientes: {e}")
        logger.error(traceback.format_exc())
        flash('Error cargando clientes', 'error')
        return render_template('clientes.html', clientes=[], search='', total_clientes=0)

@app.route('/cliente/<nombre>')
def cliente_detail(nombre):
    """Detalle de un cliente específico"""
    try:
        # Obtener equipos del cliente
        equipos = Equipment.select().where(Equipment.propietario == nombre)
        
        if not equipos.exists():
            flash('Cliente no encontrado', 'error')
            return redirect(url_for('clientes_list'))
        
        # Estadísticas del cliente
        total_equipos = equipos.count()
        
        # Obtener todos los trabajos de los equipos del cliente
        trabajos_query = Job.select().join(Equipment).where(Equipment.propietario == nombre)
        total_trabajos = trabajos_query.count()
        total_gastado = sum(trabajo.budget for trabajo in trabajos_query)
        
        # Trabajos recientes
        trabajos_recientes = trabajos_query.order_by(Job.date_done.desc()).limit(10)
        
        # Gastos por mes (últimos 6 meses)
        gastos_mensuales = []
        for i in range(5, -1, -1):
            fecha = datetime.now() - timedelta(days=i*30)
            mes_inicio = fecha.replace(day=1)
            if i == 0:
                mes_fin = datetime.now().date()
            else:
                siguiente_mes = mes_inicio + timedelta(days=32)
                mes_fin = siguiente_mes.replace(day=1) - timedelta(days=1)
            
            total_mes = sum(
                trabajo.budget for trabajo in trabajos_query 
                if mes_inicio.date() <= trabajo.date_done <= mes_fin
            )
            
            gastos_mensuales.append({
                'month': fecha.strftime('%b %Y'),
                'total': float(total_mes)
            })
        
        # Equipos con más gastos
        equipos_gastos = []
        for equipo in equipos:
            trabajos_equipo = Job.select().where(Job.equipment == equipo)
            total_equipo = sum(trabajo.budget for trabajo in trabajos_equipo)
            equipos_gastos.append({
                'equipo': equipo,
                'total_gastado': total_equipo,
                'total_trabajos': trabajos_equipo.count()
            })
        
        equipos_gastos.sort(key=lambda x: x['total_gastado'], reverse=True)
        
        return render_template('cliente_detail.html',
                             cliente_nombre=nombre,
                             equipos=list(equipos),
                             total_equipos=total_equipos,
                             total_trabajos=total_trabajos,
                             total_gastado=total_gastado,
                             trabajos_recientes=list(trabajos_recientes),
                             gastos_mensuales=gastos_mensuales,
                             equipos_gastos=equipos_gastos)
    
    except Exception as e:
        logger.error(f"Error en detalle de cliente: {e}")
        logger.error(traceback.format_exc())
        flash('Error cargando detalle del cliente', 'error')
        return redirect(url_for('clientes_list'))

@app.route('/cliente/<nombre>/editar', methods=['GET', 'POST'])
def cliente_edit(nombre):
    """Editar nombre de cliente (actualiza todos sus equipos)"""
    try:
        if request.method == 'POST':
            nuevo_nombre = request.form.get('nuevo_nombre', '').strip()
            
            if not nuevo_nombre:
                flash('El nombre del cliente es requerido', 'error')
                return redirect(url_for('cliente_edit', nombre=nombre))
            
            if nuevo_nombre == nombre:
                flash('El nombre no ha cambiado', 'info')
                return redirect(url_for('cliente_detail', nombre=nombre))
            
            # Verificar que no exista otro cliente con ese nombre
            if Equipment.select().where(Equipment.propietario == nuevo_nombre).exists():
                flash('Ya existe un cliente con ese nombre', 'error')
                return redirect(url_for('cliente_edit', nombre=nombre))
            
            # Actualizar todos los equipos del cliente
            equipos_actualizados = Equipment.update(propietario=nuevo_nombre).where(
                Equipment.propietario == nombre
            ).execute()
            
            # Limpiar caché
            clear_cache_on_equipment_change()
            
            flash(f'Cliente actualizado exitosamente. {equipos_actualizados} equipos actualizados.', 'success')
            return redirect(url_for('cliente_detail', nombre=nuevo_nombre))
        
        # GET - Mostrar formulario
        equipos = Equipment.select().where(Equipment.propietario == nombre)
        if not equipos.exists():
            flash('Cliente no encontrado', 'error')
            return redirect(url_for('clientes_list'))
        
        return render_template('cliente_edit.html', 
                             cliente_nombre=nombre,
                             total_equipos=equipos.count())
    
    except Exception as e:
        logger.error(f"Error editando cliente: {e}")
        logger.error(traceback.format_exc())
        flash('Error procesando la solicitud', 'error')
        return redirect(url_for('clientes_list'))

# ---------------------------- RUTAS DE GESTIÓN DE DATOS ----------------------------

@app.route('/admin')
def admin_panel():
    """Panel de administración de datos"""
    try:
        # Estadísticas actuales
        total_equipment = Equipment.select().count()
        total_jobs = Job.select().count()
        
        # Buscar archivos Excel en el directorio
        excel_files = []
        for file in os.listdir('.'):
            if file.endswith(('.xlsx', '.xls')):
                excel_files.append({
                    'name': file,
                    'size': os.path.getsize(file),
                    'modified': datetime.fromtimestamp(os.path.getmtime(file))
                })
        
        return render_template('admin_panel.html',
                             total_equipment=total_equipment,
                             total_jobs=total_jobs,
                             excel_files=excel_files)
    
    except Exception as e:
        logger.error(f"Error en panel de administración: {e}")
        flash('Error cargando panel de administración', 'error')
        return redirect(url_for('index'))

@app.route('/admin/validate-excel/<filename>')
def validate_excel(filename):
    """Validar estructura de archivo Excel"""
    try:
        file_path = os.path.join('.', secure_filename(filename))
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Archivo no encontrado'}), 404
        
        validation_result = validate_excel_file_final(file_path)
        return jsonify(validation_result)
    
    except Exception as e:
        logger.error(f"Error validando Excel: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/import-excel/<filename>', methods=['POST'])
def import_excel_data(filename):
    """Importar datos desde archivo Excel"""
    try:
        file_path = os.path.join('.', secure_filename(filename))
        
        if not os.path.exists(file_path):
            flash('Archivo no encontrado', 'error')
            return redirect(url_for('admin_panel'))
        
        # Validar archivo primero con el parser final
        validation = validate_excel_file_final(file_path)
        if not validation['valid']:
            flash(f'Archivo inválido: {"; ".join(validation.get("errors", ["Error desconocido"]))}', 'error')
            return redirect(url_for('admin_panel'))
        
        # Usar los datos ya parseados de la validación
        equipment_data_list = validation.get('equipment_data', [])
        
        if not equipment_data_list:
            flash('No se encontraron datos válidos en el archivo', 'warning')
            return redirect(url_for('admin_panel'))
        
        # Importar a base de datos
        db_importer = DatabaseImporter(Equipment, Job)
        import_result = db_importer.import_equipment_data(equipment_data_list)
        
        # Limpiar caché después de importar
        clear_cache_on_equipment_change()
        clear_cache_on_job_change()
        
        # Mostrar resultados
        if import_result['errors']:
            flash(f'Importación completada con errores. Equipos: {import_result["equipment_imported"]}, Trabajos: {import_result["jobs_imported"]}', 'warning')
            for error in import_result['errors'][:5]:  # Mostrar solo los primeros 5 errores
                flash(error, 'error')
        else:
            flash(f'Importación exitosa: {import_result["equipment_imported"]} equipos y {import_result["jobs_imported"]} trabajos importados', 'success')
        
        return redirect(url_for('admin_panel'))
    
    except Exception as e:
        logger.error(f"Error importando Excel: {e}")
        logger.error(traceback.format_exc())
        flash(f'Error durante la importación: {str(e)}', 'error')
        return redirect(url_for('admin_panel'))

@app.route('/admin/clear-data', methods=['POST'])
def clear_all_data_route():
    """Limpiar todos los datos de la base de datos"""
    try:
        # Verificar confirmación
        confirmation = request.form.get('confirmation', '').strip().upper()
        if confirmation != 'CONFIRMAR':
            flash('Debe escribir "CONFIRMAR" para proceder', 'error')
            return redirect(url_for('admin_panel'))
        
        # Limpiar datos
        result = clear_all_data(Equipment, Job)
        
        if result['success']:
            # Limpiar caché
            cache.clear()
            
            flash(result['message'], 'success')
            logger.info(f"Base de datos limpiada: {result}")
        else:
            flash(f'Error limpiando datos: {result["error"]}', 'error')
        
        return redirect(url_for('admin_panel'))
    
    except Exception as e:
        logger.error(f"Error limpiando datos: {e}")
        logger.error(traceback.format_exc())
        flash(f'Error interno: {str(e)}', 'error')
        return redirect(url_for('admin_panel'))

@app.route('/admin/upload-excel', methods=['POST'])
def upload_excel():
    """Subir archivo Excel para importación"""
    try:
        if 'excel_file' not in request.files:
            flash('No se seleccionó archivo', 'error')
            return redirect(url_for('admin_panel'))
        
        file = request.files['excel_file']
        if file.filename == '':
            flash('No se seleccionó archivo', 'error')
            return redirect(url_for('admin_panel'))
        
        if file and file.filename.endswith(('.xlsx', '.xls')):
            filename = secure_filename(file.filename)
            file_path = os.path.join('.', filename)
            file.save(file_path)
            
            flash(f'Archivo {filename} subido exitosamente', 'success')
            return redirect(url_for('admin_panel'))
        else:
            flash('Solo se permiten archivos Excel (.xlsx, .xls)', 'error')
            return redirect(url_for('admin_panel'))
    
    except Exception as e:
        logger.error(f"Error subiendo archivo: {e}")
        flash(f'Error subiendo archivo: {str(e)}', 'error')
        return redirect(url_for('admin_panel'))

# ---------------------------- APIS DE INFORMACIÓN ----------------------------

@app.route('/api/dolar')
@cache.cached(timeout=300)  # Cache por 5 minutos
def get_dolar_cotization():
    """Obtener cotización del dólar desde APIs públicas"""
    try:
        # Intentar múltiples fuentes para mayor confiabilidad
        cotizacion_data = {
            'success': False,
            'precio_venta': 0,
            'precio_compra': 0,
            'fecha_actualizacion': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'fuente': 'No disponible',
            'error': None
        }
        
        # Fuente 1: DolarAPI (más confiable)
        try:
            response = requests.get('https://dolarapi.com/v1/dolares/oficial', timeout=5)
            if response.status_code == 200:
                data = response.json()
                cotizacion_data.update({
                    'success': True,
                    'precio_venta': float(data.get('venta', 0)),
                    'precio_compra': float(data.get('compra', 0)),
                    'fecha_actualizacion': data.get('fechaActualizacion', datetime.now().strftime('%d/%m/%Y %H:%M')),
                    'fuente': 'Banco Nación (DolarAPI)'
                })
                return jsonify(cotizacion_data)
        except Exception as e:
            logger.warning(f"Error con DolarAPI: {e}")
        
        # Fuente 2: Bluelytics como backup
        try:
            response = requests.get('https://api.bluelytics.com.ar/v2/latest', timeout=5)
            if response.status_code == 200:
                data = response.json()
                oficial = data.get('oficial', {})
                cotizacion_data.update({
                    'success': True,
                    'precio_venta': float(oficial.get('value_sell', 0)),
                    'precio_compra': float(oficial.get('value_buy', 0)),
                    'fecha_actualizacion': datetime.now().strftime('%d/%m/%Y %H:%M'),
                    'fuente': 'Bluelytics'
                })
                return jsonify(cotizacion_data)
        except Exception as e:
            logger.warning(f"Error con Bluelytics: {e}")
        
        # Si todas las fuentes fallan
        cotizacion_data['error'] = 'No se pudo obtener la cotización'
        return jsonify(cotizacion_data), 503
        
    except Exception as e:
        logger.error(f"Error general obteniendo cotización: {e}")
        return jsonify({
            'success': False,
            'error': 'Error interno del servidor',
            'precio_venta': 0,
            'precio_compra': 0,
            'fecha_actualizacion': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'fuente': 'Error'
        }), 500

@app.route('/api/tiempo')
def get_current_time():
    """Obtener fecha y hora actual del servidor"""
    try:
        now = datetime.now()
        
        # Nombres de días y meses en español
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        
        return jsonify({
            'success': True,
            'hora': now.strftime('%H:%M:%S'),
            'fecha_corta': now.strftime('%d/%m/%Y'),
            'fecha_completa': f"{dias_semana[now.weekday()]}, {now.day} de {meses[now.month-1]} de {now.year}",
            'timestamp': now.timestamp(),
            'timezone': 'America/Argentina/Buenos_Aires'
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo tiempo: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ---------------------------- INICIALIZACIÓN ----------------------------

if __name__ == '__main__':
    init_db()
    # Para desarrollo local
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
    
    # Para producción en Render, se usará gunicorn
