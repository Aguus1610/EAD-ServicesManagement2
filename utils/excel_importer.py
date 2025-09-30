"""
Módulo de importación de datos desde Excel para EAD Oleohidráulica
"""
import pandas as pd
import openpyxl
from datetime import datetime, date
import logging
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class WorkEntry:
    """Entrada de trabajo individual"""
    fecha: date
    descripcion: str
    presupuesto: float


@dataclass
class EquipmentData:
    """Datos de equipo con sus trabajos"""
    nombre: str
    propietario: str
    trabajos: List[WorkEntry]


class ExcelImporter:
    """Importador de datos desde Excel"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.imported_data = []
    
    def parse_excel_file(self, file_path: str) -> List[EquipmentData]:
        """
        Parsear archivo Excel según la estructura especificada:
        - Cada hoja = un cliente (propietario)
        - Columnas: EQUIPO, FECHA, REPUESTOS, MANO DE OBRA
        """
        try:
            # Cargar el archivo Excel
            excel_file = pd.ExcelFile(file_path)
            all_equipment_data = []
            
            logger.info(f"Procesando archivo Excel: {file_path}")
            logger.info(f"Hojas encontradas: {excel_file.sheet_names}")
            
            for sheet_name in excel_file.sheet_names:
                try:
                    # Cada hoja representa un cliente/propietario
                    propietario = sheet_name.strip()
                    logger.info(f"Procesando hoja: {propietario}")
                    
                    # Leer la hoja
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    # Procesar datos de la hoja
                    equipment_data = self._process_sheet_data(df, propietario)
                    all_equipment_data.extend(equipment_data)
                    
                except Exception as e:
                    error_msg = f"Error procesando hoja '{sheet_name}': {str(e)}"
                    logger.error(error_msg)
                    self.errors.append(error_msg)
            
            return all_equipment_data
            
        except Exception as e:
            error_msg = f"Error leyendo archivo Excel: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return []
    
    def _process_sheet_data(self, df: pd.DataFrame, propietario: str) -> List[EquipmentData]:
        """Procesar datos de una hoja específica con detección inteligente"""
        equipment_dict = {}
        
        logger.info(f"Procesando hoja '{propietario}' - Forma original: {df.shape}")
        logger.info(f"Columnas originales: {list(df.columns)}")
        
        # Intentar detectar automáticamente el área de datos
        df_cleaned = self._detect_data_area(df, propietario)
        
        if df_cleaned.empty:
            self.warnings.append(f"No se encontraron datos válidos en la hoja '{propietario}'")
            return []
        
        # Mapear columnas con detección inteligente
        column_mapping = self._intelligent_column_mapping(df_cleaned, propietario)
        
        if not column_mapping:
            self.errors.append(f"No se pudieron identificar las columnas necesarias en '{propietario}'")
            return []
        
        logger.info(f"Mapeo de columnas para '{propietario}': {column_mapping}")
        
        # Procesar cada fila
        for index, row in df_cleaned.iterrows():
            try:
                # Obtener datos usando el mapeo
                equipo_name = self._clean_string(row.get(column_mapping.get('EQUIPO'), ''))
                if not equipo_name or equipo_name.lower() in ['equipo', 'equipos', 'maquina', 'maquinas']:
                    continue
                
                # Parsear fecha - SOLO de la columna de fecha
                fecha_raw = row.get(column_mapping.get('FECHA'))
                fecha = self._parse_date(fecha_raw)
                
                # Si no hay fecha válida, usar fecha por defecto (hoy)
                if not fecha:
                    logger.warning(f"Fila {index + 1} en '{propietario}': Fecha inválida '{fecha_raw}', usando fecha actual")
                    from datetime import date
                    fecha = date.today()
                
                # Combinar repuestos y mano de obra en descripción
                repuestos = self._clean_string(row.get(column_mapping.get('REPUESTOS', ''), ''))
                mano_obra = self._clean_string(row.get(column_mapping.get('MANO_DE_OBRA', ''), ''))
                
                descripcion_parts = []
                if repuestos:
                    descripcion_parts.append(f"Repuestos: {repuestos}")
                if mano_obra:
                    descripcion_parts.append(f"Mano de obra: {mano_obra}")
                
                descripcion = " | ".join(descripcion_parts) if descripcion_parts else "Trabajo registrado"
                
                # Calcular presupuesto (intentar extraer números)
                presupuesto = self._extract_budget(repuestos, mano_obra)
                
                # Crear entrada de trabajo
                work_entry = WorkEntry(
                    fecha=fecha,
                    descripcion=descripcion,
                    presupuesto=presupuesto
                )
                
                # Agrupar por equipo
                if equipo_name not in equipment_dict:
                    equipment_dict[equipo_name] = EquipmentData(
                        nombre=equipo_name,
                        propietario=propietario,
                        trabajos=[]
                    )
                
                equipment_dict[equipo_name].trabajos.append(work_entry)
                
            except Exception as e:
                error_msg = f"Error procesando fila {index + 1} en '{propietario}': {str(e)}"
                logger.warning(error_msg)
                self.warnings.append(error_msg)
        
        logger.info(f"Equipos encontrados en '{propietario}': {len(equipment_dict)}")
        return list(equipment_dict.values())
    
    def _detect_data_area(self, df: pd.DataFrame, propietario: str) -> pd.DataFrame:
        """Detectar automáticamente el área de datos en la hoja"""
        try:
            # Buscar la fila que contiene los encabezados
            header_row = None
            
            # Buscar en las primeras 10 filas
            for i in range(min(10, len(df))):
                row_values = [str(val).strip().upper() for val in df.iloc[i].values if pd.notna(val)]
                
                # Verificar si esta fila contiene palabras clave de encabezados
                header_keywords = ['EQUIPO', 'FECHA', 'REPUESTO', 'MANO', 'OBRA', 'TRABAJO', 'SERVICIO', 'MATERIAL']
                matches = sum(1 for keyword in header_keywords if any(keyword in val for val in row_values))
                
                if matches >= 2:  # Al menos 2 palabras clave encontradas
                    header_row = i
                    logger.info(f"Encabezados detectados en fila {i + 1} de '{propietario}'")
                    break
            
            if header_row is None:
                # Si no se encuentra encabezado, asumir que la primera fila son los encabezados
                logger.warning(f"No se detectaron encabezados claros en '{propietario}', usando primera fila")
                header_row = 0
            
            # Crear nuevo DataFrame desde la fila de encabezados
            new_df = df.iloc[header_row:].copy()
            new_df.columns = new_df.iloc[0]  # Usar primera fila como encabezados
            new_df = new_df.iloc[1:].reset_index(drop=True)  # Remover fila de encabezados
            
            # Limpiar nombres de columnas
            new_df.columns = [str(col).strip() if pd.notna(col) else f"Col_{i}" for i, col in enumerate(new_df.columns)]
            
            # Filtrar filas vacías
            new_df = new_df.dropna(how='all')
            
            # Filtrar columnas completamente vacías
            new_df = new_df.dropna(axis=1, how='all')
            
            logger.info(f"Área de datos detectada en '{propietario}': {new_df.shape} (desde fila {header_row + 1})")
            logger.info(f"Columnas detectadas: {list(new_df.columns)}")
            
            return new_df
            
        except Exception as e:
            logger.error(f"Error detectando área de datos en '{propietario}': {e}")
            return df  # Retornar DataFrame original si falla
    
    def _intelligent_column_mapping(self, df: pd.DataFrame, propietario: str) -> Dict[str, str]:
        """Mapeo inteligente de columnas basado en contenido y nombres"""
        
        # Patrones de búsqueda más flexibles
        patterns = {
            'EQUIPO': [
                # Nombres exactos
                r'^EQUIPO[S]?$', r'^MAQUINA[S]?$', r'^NOMBRE$', r'^VEHICULO[S]?$',
                # Contenido parcial
                r'EQUIPO', r'MAQUINA', r'VEHICULO', r'UNIDAD', r'MODELO',
                # Patrones específicos
                r'TIPO.*EQUIPO', r'NOMBRE.*EQUIPO'
            ],
            'FECHA': [
                # Nombres exactos
                r'^FECHA[S]?$', r'^DATE$', r'^DIA[S]?$', r'^CUANDO$',
                # Contenido parcial
                r'FECHA', r'DATE', r'DIA', r'MOMENTO', r'TIEMPO',
                # Patrones específicos
                r'FECHA.*TRABAJO', r'FECHA.*SERVICIO'
            ],
            'REPUESTOS': [
                # Nombres exactos
                r'^REPUESTO[S]?$', r'^MATERIAL[ES]?$', r'^PARTE[S]?$', r'^PIEZA[S]?$',
                # Contenido parcial
                r'REPUESTO', r'MATERIAL', r'PARTE', r'PIEZA', r'COMPONENTE',
                # Patrones específicos
                r'COSTO.*REPUESTO', r'PRECIO.*MATERIAL'
            ],
            'MANO_DE_OBRA': [
                # Nombres exactos
                r'^MANO.*OBRA$', r'^TRABAJO[S]?$', r'^LABOR[ES]?$', r'^SERVICIO[S]?$',
                # Contenido parcial
                r'MANO.*OBRA', r'TRABAJO', r'LABOR', r'SERVICIO', r'TAREA',
                # Patrones específicos
                r'COSTO.*MANO', r'PRECIO.*TRABAJO', r'HORA[S]?.*TRABAJO'
            ]
        }
        
        column_mapping = {}
        
        for target_col, pattern_list in patterns.items():
            best_match = None
            best_score = 0
            
            for col_name in df.columns:
                col_upper = str(col_name).upper().strip()
                
                # Calcular score de coincidencia
                score = 0
                for pattern in pattern_list:
                    if re.search(pattern, col_upper):
                        # Dar más peso a coincidencias exactas
                        if re.match(pattern, col_upper):
                            score += 10
                        else:
                            score += 5
                        break
                
                # Bonus por posición (columnas típicas están en cierto orden)
                col_index = list(df.columns).index(col_name)
                if target_col == 'EQUIPO' and col_index <= 2:
                    score += 2
                elif target_col == 'FECHA' and 1 <= col_index <= 3:
                    score += 2
                elif target_col in ['REPUESTOS', 'MANO_DE_OBRA'] and col_index >= 2:
                    score += 1
                
                # Verificar contenido de la columna para validar
                if score > 0:
                    content_score = self._analyze_column_content(df[col_name], target_col)
                    score += content_score
                
                if score > best_score:
                    best_score = score
                    best_match = col_name
            
            if best_match and best_score >= 5:  # Umbral mínimo de confianza
                column_mapping[target_col] = best_match
                logger.info(f"'{propietario}': {target_col} -> '{best_match}' (score: {best_score})")
        
        # Verificar que tenemos al menos EQUIPO
        if 'EQUIPO' not in column_mapping:
            logger.warning(f"'{propietario}': Columna EQUIPO no encontrada")
            
            # Intentar mapeo por posición como último recurso
            if len(df.columns) >= 1:
                column_mapping['EQUIPO'] = df.columns[0]
                logger.info(f"'{propietario}': EQUIPO mapeado por posición -> '{df.columns[0]}'")
        
        # Para FECHA, ser más flexible - si no hay fecha, usaremos fecha actual
        if 'FECHA' not in column_mapping:
            logger.warning(f"'{propietario}': Columna FECHA no encontrada, se usará fecha actual para todos los registros")
            # Buscar columna que parezca fecha
            for i, col in enumerate(df.columns[1:], 1):
                if self._analyze_column_content(df[col], 'FECHA') > 0:
                    column_mapping['FECHA'] = col
                    logger.info(f"'{propietario}': FECHA mapeado por contenido -> '{col}'")
                    break
            
            # Si no se encuentra, usar segunda columna si existe
            if 'FECHA' not in column_mapping and len(df.columns) > 1:
                column_mapping['FECHA'] = df.columns[1]
                logger.info(f"'{propietario}': FECHA mapeado por posición -> '{df.columns[1]}'")
        
        # Mapear REPUESTOS y MANO_DE_OBRA si no están mapeados
        if 'REPUESTOS' not in column_mapping and len(df.columns) > 2:
            column_mapping['REPUESTOS'] = df.columns[2] if len(df.columns) > 2 else df.columns[-2]
            logger.info(f"'{propietario}': REPUESTOS mapeado por posición -> '{column_mapping['REPUESTOS']}'")
        
        if 'MANO_DE_OBRA' not in column_mapping and len(df.columns) > 3:
            column_mapping['MANO_DE_OBRA'] = df.columns[3] if len(df.columns) > 3 else df.columns[-1]
            logger.info(f"'{propietario}': MANO_DE_OBRA mapeado por posición -> '{column_mapping['MANO_DE_OBRA']}'")
        
        return column_mapping
    
    def _analyze_column_content(self, series: pd.Series, expected_type: str) -> int:
        """Analizar contenido de columna para validar el tipo esperado"""
        score = 0
        sample_size = min(10, len(series))
        
        if sample_size == 0:
            return 0
        
        sample = series.dropna().head(sample_size)
        
        if expected_type == 'FECHA':
            # Verificar si contiene fechas
            date_count = 0
            for value in sample:
                if self._parse_date(value):
                    date_count += 1
            
            if date_count > sample_size * 0.5:  # Más del 50% son fechas válidas
                score += 5
            elif date_count > 0:
                score += 2
        
        elif expected_type == 'EQUIPO':
            # Verificar si contiene nombres de equipos/máquinas
            equipment_keywords = ['scania', 'volvo', 'caterpillar', 'john deere', 'massey', 'new holland', 
                                'deutz', 'case', 'komatsu', 'hitachi', 'liebherr', 'mercedes', 'iveco']
            
            for value in sample:
                value_str = str(value).lower()
                if any(keyword in value_str for keyword in equipment_keywords):
                    score += 3
                elif len(value_str) > 5 and any(char.isdigit() for char in value_str):
                    score += 1  # Probablemente modelo con números
        
        elif expected_type in ['REPUESTOS', 'MANO_DE_OBRA']:
            # Verificar si contiene descripciones de trabajo/repuestos
            work_keywords = ['filtro', 'aceite', 'cambio', 'reparacion', 'service', 'mantenimiento',
                           'revision', 'ajuste', 'limpieza', 'lubricacion', 'pastilla', 'correa']
            
            for value in sample:
                value_str = str(value).lower()
                if any(keyword in value_str for keyword in work_keywords):
                    score += 2
                elif '$' in value_str or 'peso' in value_str:
                    score += 1  # Contiene precios
        
        return score
    
    def _try_map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Método legacy - mantenido por compatibilidad"""
        column_mapping = {
            'EQUIPO': ['EQUIPO', 'EQUIPOS', 'MAQUINA', 'MAQUINAS', 'NOMBRE'],
            'FECHA': ['FECHA', 'DATE', 'DIA', 'CUANDO'],
            'REPUESTOS': ['REPUESTOS', 'REPUESTO', 'MATERIALES', 'MATERIAL', 'PARTS'],
            'MANO DE OBRA': ['MANO DE OBRA', 'MANO_DE_OBRA', 'TRABAJO', 'LABOR', 'SERVICIO']
        }
        
        new_columns = {}
        for target_col, possible_names in column_mapping.items():
            for col in df.columns:
                if any(name in col.upper() for name in possible_names):
                    new_columns[col] = target_col
                    break
        
        if new_columns:
            df = df.rename(columns=new_columns)
            logger.info(f"Columnas mapeadas: {new_columns}")
        
        return df
    
    def _clean_string(self, value) -> str:
        """Limpiar y normalizar string"""
        if pd.isna(value):
            return ""
        return str(value).strip()
    
    def _parse_date(self, date_value) -> Optional[date]:
        """Parsear fecha desde diferentes formatos"""
        if pd.isna(date_value):
            return None
        
        # Si ya es datetime
        if isinstance(date_value, (datetime, date)):
            return date_value.date() if isinstance(date_value, datetime) else date_value
        
        # Intentar parsear string
        date_str = str(date_value).strip()
        if not date_str:
            return None
        
        # Mapear meses en español a inglés para parsing
        month_mapping = {
            'ENE': 'Jan', 'FEB': 'Feb', 'MAR': 'Mar', 'ABR': 'Apr',
            'MAY': 'May', 'JUN': 'Jun', 'JUL': 'Jul', 'AGO': 'Aug',
            'SEP': 'Sep', 'OCT': 'Oct', 'NOV': 'Nov', 'DIC': 'Dec',
            'ENERO': 'January', 'FEBRERO': 'February', 'MARZO': 'March',
            'ABRIL': 'April', 'MAYO': 'May', 'JUNIO': 'June',
            'JULIO': 'July', 'AGOSTO': 'August', 'SEPTIEMBRE': 'September',
            'OCTUBRE': 'October', 'NOVIEMBRE': 'November', 'DICIEMBRE': 'December'
        }
        
        # Convertir meses españoles a ingleses
        date_str_en = date_str.upper()
        for esp, eng in month_mapping.items():
            date_str_en = date_str_en.replace(esp, eng)
        
        # Formatos comunes
        date_formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d',
            '%d/%m/%y', '%d-%m-%y', '%y-%m-%d',
            '%d.%m.%Y', '%d.%m.%y', '%Y/%m/%d',
            '%d-%b-%Y', '%d-%B-%Y'  # Para formatos como 22-ENE-2024
        ]
        
        # Intentar con fecha original
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        # Intentar con fecha convertida al inglés
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str_en, fmt).date()
            except ValueError:
                continue
        
        # Intentar con pandas
        try:
            return pd.to_datetime(date_str).date()
        except:
            logger.warning(f"No se pudo parsear fecha: {date_str}")
            return None
    
    def _extract_budget(self, repuestos: str, mano_obra: str) -> float:
        """Extraer presupuesto de las descripciones"""
        text = f"{repuestos} {mano_obra}".lower()
        
        # Buscar números que parezcan precios
        price_patterns = [
            r'\$\s*(\d+(?:[.,]\d+)?)',  # $1000 o $1.000,50
            r'(\d+(?:[.,]\d+)?)\s*\$',  # 1000$ 
            r'(\d+(?:[.,]\d+)?)\s*pesos',  # 1000 pesos
            r'total[:\s]*(\d+(?:[.,]\d+)?)',  # total: 1000
            r'costo[:\s]*(\d+(?:[.,]\d+)?)',  # costo: 1000
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    # Tomar el primer número encontrado
                    price_str = matches[0].replace(',', '.')
                    return float(price_str)
                except ValueError:
                    continue
        
        return 0.0
    
    def get_import_summary(self) -> Dict:
        """Obtener resumen de la importación"""
        return {
            'errors': self.errors,
            'warnings': self.warnings,
            'total_equipment': len(self.imported_data),
            'total_jobs': sum(len(eq.trabajos) for eq in self.imported_data)
        }


class DatabaseImporter:
    """Importador de datos a la base de datos"""
    
    def __init__(self, equipment_model, job_model, cliente_model=None):
        self.Equipment = equipment_model
        self.Job = job_model
        self.Cliente = cliente_model
        self.imported_equipment = []
        self.imported_jobs = []
        self.imported_clientes = []
        self.errors = []
    
    def import_equipment_data(self, equipment_data_list: List[EquipmentData]) -> Dict:
        """Importar datos de equipos a la base de datos"""
        logger.info(f"Iniciando importación de {len(equipment_data_list)} equipos")
        
        for equipment_data in equipment_data_list:
            try:
                # Crear o buscar equipo
                equipment = self._create_or_update_equipment(equipment_data)
                
                # Importar trabajos del equipo
                jobs_imported = self._import_equipment_jobs(equipment, equipment_data.trabajos)
                
                self.imported_equipment.append(equipment)
                self.imported_jobs.extend(jobs_imported)
                
            except Exception as e:
                error_msg = f"Error importando equipo '{equipment_data.nombre}': {str(e)}"
                logger.error(error_msg)
                self.errors.append(error_msg)
        
        return {
            'equipment_imported': len(self.imported_equipment),
            'jobs_imported': len(self.imported_jobs),
            'clientes_imported': len(self.imported_clientes),
            'errors': self.errors
        }
    
    def _create_or_update_equipment(self, equipment_data: EquipmentData):
        """Crear o actualizar equipo"""
        # Parsear nombre del equipo para extraer marca, modelo, etc.
        parsed_info = self._parse_equipment_name(equipment_data.nombre)
        
        # Crear o buscar cliente si el modelo está disponible
        cliente = None
        if self.Cliente and equipment_data.propietario:
            cliente = self._create_or_get_cliente(equipment_data.propietario)
        
        # Buscar si ya existe por nombre similar
        existing = None
        try:
            existing = self.Equipment.select().where(
                (self.Equipment.marca == parsed_info['marca']) &
                (self.Equipment.modelo == parsed_info['modelo']) &
                (self.Equipment.propietario == equipment_data.propietario)
            ).first()
        except:
            pass
        
        if existing:
            # Si existe el equipo pero no tiene cliente asignado, asignarlo
            if cliente and not existing.cliente:
                existing.cliente = cliente
                existing.save()
                logger.info(f"Cliente asignado a equipo existente: {existing.marca} {existing.modelo}")
            logger.info(f"Equipo existente encontrado: {existing.marca} {existing.modelo}")
            return existing
        
        # Crear nuevo equipo
        equipment_data_dict = {
            'marca': parsed_info['marca'],
            'modelo': parsed_info['modelo'],
            'anio': parsed_info['anio'],
            'n_serie': parsed_info['n_serie'],
            'propietario': equipment_data.propietario,
            'notes': f"Importado desde Excel - Nombre original: {equipment_data.nombre}"
        }
        
        # Agregar cliente si está disponible
        if cliente:
            equipment_data_dict['cliente'] = cliente
        
        equipment = self.Equipment.create(**equipment_data_dict)
        
        logger.info(f"Nuevo equipo creado: {equipment.marca} {equipment.modelo}")
        return equipment
    
    def _create_or_get_cliente(self, propietario_nombre: str):
        """Crear o obtener cliente basado en el nombre del propietario"""
        if not self.Cliente or not propietario_nombre:
            return None
        
        propietario_nombre = propietario_nombre.strip()
        
        try:
            # Buscar cliente existente
            cliente = self.Cliente.select().where(self.Cliente.nombre == propietario_nombre).first()
            
            if cliente:
                logger.info(f"Cliente existente encontrado: {propietario_nombre}")
                return cliente
            
            # Crear nuevo cliente
            from datetime import datetime
            cliente = self.Cliente.create(
                nombre=propietario_nombre,
                tipo_cliente='Particular',  # Por defecto
                fecha_registro=datetime.now().date(),
                activo=True,
                notas=f"Cliente creado automáticamente durante importación de Excel"
            )
            
            self.imported_clientes.append(cliente)
            logger.info(f"Nuevo cliente creado: {propietario_nombre}")
            return cliente
            
        except Exception as e:
            logger.error(f"Error creando cliente '{propietario_nombre}': {e}")
            return None
    
    def _parse_equipment_name(self, nombre: str) -> Dict:
        """Parsear nombre del equipo para extraer información"""
        nombre = nombre.strip()
        
        # Patrones comunes para extraer marca y modelo
        patterns = [
            r'^([A-Za-z]+)\s+([A-Za-z0-9\-]+)',  # MARCA MODELO
            r'^([A-Za-z]+)[\s\-]([A-Za-z0-9\-]+)',  # MARCA-MODELO
        ]
        
        marca = "Sin especificar"
        modelo = nombre  # Por defecto, usar el nombre completo como modelo
        
        for pattern in patterns:
            match = re.match(pattern, nombre)
            if match:
                marca = match.group(1).strip()
                modelo = match.group(2).strip()
                break
        
        # Intentar extraer año (4 dígitos)
        year_match = re.search(r'\b(19|20)\d{2}\b', nombre)
        anio = int(year_match.group()) if year_match else datetime.now().year
        
        # Generar número de serie único
        n_serie = f"IMP-{hash(nombre) % 100000:05d}"
        
        return {
            'marca': marca,
            'modelo': modelo,
            'anio': anio,
            'n_serie': n_serie
        }
    
    def _import_equipment_jobs(self, equipment, work_entries: List[WorkEntry]) -> List:
        """Importar trabajos de un equipo"""
        imported_jobs = []
        
        for work_entry in work_entries:
            try:
                # Verificar si ya existe un trabajo similar
                existing_job = self.Job.select().where(
                    (self.Job.equipment == equipment) &
                    (self.Job.date_done == work_entry.fecha) &
                    (self.Job.description.contains(work_entry.descripcion[:50]))
                ).first()
                
                if existing_job:
                    logger.info(f"Trabajo existente encontrado para {equipment.marca} {equipment.modelo} en {work_entry.fecha}")
                    continue
                
                # Crear nuevo trabajo
                job = self.Job.create(
                    equipment=equipment,
                    date_done=work_entry.fecha,
                    description=work_entry.descripcion,
                    budget=work_entry.presupuesto,
                    notes="Importado desde Excel"
                )
                
                imported_jobs.append(job)
                logger.info(f"Trabajo importado: {equipment.marca} {equipment.modelo} - {work_entry.fecha}")
                
            except Exception as e:
                error_msg = f"Error importando trabajo para {equipment.marca} {equipment.modelo}: {str(e)}"
                logger.error(error_msg)
                self.errors.append(error_msg)
        
        return imported_jobs


def clear_all_data(equipment_model, job_model, cliente_model=None) -> Dict:
    """Limpiar todos los datos de la base de datos manteniendo la estructura"""
    try:
        # Contar registros antes de eliminar
        jobs_count = job_model.select().count()
        equipment_count = equipment_model.select().count()
        clientes_count = 0
        
        if cliente_model:
            clientes_count = cliente_model.select().count()
        
        # Eliminar todos los trabajos primero (por las foreign keys)
        job_model.delete().execute()
        
        # Eliminar todos los equipos
        equipment_model.delete().execute()
        
        # Eliminar todos los clientes si se proporciona el modelo
        if cliente_model:
            cliente_model.delete().execute()
        
        message_parts = [f'{equipment_count} equipos', f'{jobs_count} trabajos']
        if cliente_model:
            message_parts.append(f'{clientes_count} clientes')
        
        message = f'Se eliminaron {", ".join(message_parts)}'
        logger.info(f"Base de datos limpiada: {message}")
        
        return {
            'success': True,
            'equipment_deleted': equipment_count,
            'jobs_deleted': jobs_count,
            'clientes_deleted': clientes_count,
            'message': message
        }
        
    except Exception as e:
        error_msg = f"Error limpiando base de datos: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }


# Función de utilidad para validar archivo Excel
def validate_excel_file(file_path: str) -> Dict:
    """Validar estructura del archivo Excel con detección inteligente"""
    try:
        excel_file = pd.ExcelFile(file_path)
        
        validation_result = {
            'valid': True,
            'sheets': [],
            'warnings': [],
            'errors': [],
            'summary': {
                'total_sheets': len(excel_file.sheet_names),
                'valid_sheets': 0,
                'estimated_records': 0
            }
        }
        
        if not excel_file.sheet_names:
            validation_result['valid'] = False
            validation_result['errors'].append("El archivo no contiene hojas")
            return validation_result
        
        # Crear instancia temporal del importador para usar sus métodos
        temp_importer = ExcelImporter()
        
        for sheet_name in excel_file.sheet_names:
            try:
                # Leer toda la hoja para análisis completo
                df_full = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Detectar área de datos
                df_cleaned = temp_importer._detect_data_area(df_full, sheet_name)
                
                # Intentar mapeo de columnas
                column_mapping = temp_importer._intelligent_column_mapping(df_cleaned, sheet_name)
                
                sheet_info = {
                    'name': sheet_name,
                    'original_shape': df_full.shape,
                    'data_area_shape': df_cleaned.shape,
                    'original_columns': list(df_full.columns),
                    'detected_columns': list(df_cleaned.columns),
                    'column_mapping': column_mapping,
                    'valid': False,
                    'confidence': 0,
                    'estimated_records': 0,
                    'issues': []
                }
                
                # Evaluar calidad del mapeo
                required_cols = ['EQUIPO', 'FECHA']
                found_required = [col for col in required_cols if col in column_mapping]
                
                confidence = 0
                if len(found_required) == len(required_cols):
                    confidence += 50
                    sheet_info['valid'] = True
                    validation_result['summary']['valid_sheets'] += 1
                    
                    # Estimar registros válidos
                    if not df_cleaned.empty:
                        # Contar filas con datos en columnas críticas
                        equipo_col = column_mapping.get('EQUIPO')
                        fecha_col = column_mapping.get('FECHA')
                        
                        valid_records = 0
                        for _, row in df_cleaned.iterrows():
                            equipo_val = temp_importer._clean_string(row.get(equipo_col, ''))
                            fecha_val = temp_importer._parse_date(row.get(fecha_col))
                            
                            if equipo_val and fecha_val and equipo_val.lower() not in ['equipo', 'equipos']:
                                valid_records += 1
                        
                        sheet_info['estimated_records'] = valid_records
                        validation_result['summary']['estimated_records'] += valid_records
                        
                        if valid_records > 0:
                            confidence += 30
                else:
                    missing = [col for col in required_cols if col not in column_mapping]
                    sheet_info['issues'].append(f"Columnas críticas no detectadas: {missing}")
                
                # Evaluar calidad de columnas opcionales
                optional_cols = ['REPUESTOS', 'MANO_DE_OBRA']
                found_optional = [col for col in optional_cols if col in column_mapping]
                confidence += len(found_optional) * 10
                
                # Evaluar estructura de datos
                if not df_cleaned.empty:
                    confidence += 10
                    
                    # Verificar si hay datos que parecen válidos
                    sample_size = min(5, len(df_cleaned))
                    if sample_size > 0:
                        sample = df_cleaned.head(sample_size)
                        
                        # Verificar equipos
                        if 'EQUIPO' in column_mapping:
                            equipo_col = column_mapping['EQUIPO']
                            valid_equipos = sum(1 for val in sample[equipo_col] 
                                              if temp_importer._clean_string(val) and 
                                              temp_importer._clean_string(val).lower() not in ['equipo', 'equipos'])
                            if valid_equipos > 0:
                                confidence += 10
                        
                        # Verificar fechas
                        if 'FECHA' in column_mapping:
                            fecha_col = column_mapping['FECHA']
                            valid_fechas = sum(1 for val in sample[fecha_col] 
                                             if temp_importer._parse_date(val))
                            if valid_fechas > 0:
                                confidence += 10
                
                sheet_info['confidence'] = min(100, confidence)
                
                # Generar advertencias específicas
                if sheet_info['confidence'] < 70:
                    if sheet_info['confidence'] < 30:
                        sheet_info['issues'].append("Estructura de datos muy incierta")
                    else:
                        sheet_info['issues'].append("Estructura de datos parcialmente reconocida")
                
                if sheet_info['estimated_records'] == 0 and sheet_info['valid']:
                    sheet_info['issues'].append("No se encontraron registros válidos")
                
                validation_result['sheets'].append(sheet_info)
                
            except Exception as e:
                validation_result['warnings'].append(f"Error analizando hoja '{sheet_name}': {str(e)}")
                sheet_info = {
                    'name': sheet_name,
                    'valid': False,
                    'confidence': 0,
                    'issues': [f"Error de lectura: {str(e)}"]
                }
                validation_result['sheets'].append(sheet_info)
        
        # Evaluación general
        if validation_result['summary']['valid_sheets'] == 0:
            validation_result['valid'] = False
            validation_result['errors'].append("No se encontraron hojas con estructura válida")
        elif validation_result['summary']['estimated_records'] == 0:
            validation_result['valid'] = False
            validation_result['errors'].append("No se encontraron registros válidos para importar")
        
        return validation_result
        
    except Exception as e:
        return {
            'valid': False,
            'errors': [f"Error validando archivo: {str(e)}"],
            'sheets': [],
            'warnings': [],
            'summary': {'total_sheets': 0, 'valid_sheets': 0, 'estimated_records': 0}
        }
