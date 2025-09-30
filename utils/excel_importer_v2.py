"""
Parser de Excel mejorado v2 - Agrupa múltiples filas por equipo y fecha
"""
import pandas as pd
import openpyxl
from datetime import date, datetime
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class WorkEntry:
    fecha: date
    descripcion: str
    costo: float = 0.0

@dataclass
class EquipmentData:
    propietario: str
    nombre: str
    trabajos: List[WorkEntry]

class ExcelImporterV2:
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def parse_excel_file(self, file_path: str) -> List[EquipmentData]:
        """Parsear archivo Excel con agrupación inteligente"""
        try:
            excel_file = pd.ExcelFile(file_path)
            all_equipment = []
            
            for sheet_name in excel_file.sheet_names:
                if sheet_name.lower() in ['hoja5', 'sheet5']:  # Saltar hojas vacías conocidas
                    continue
                    
                logger.info(f"Procesando hoja: {sheet_name}")
                equipment_data = self._process_sheet(excel_file, sheet_name)
                all_equipment.extend(equipment_data)
            
            return all_equipment
            
        except Exception as e:
            logger.error(f"Error procesando archivo Excel: {e}")
            self.errors.append(f"Error general: {e}")
            return []
    
    def _process_sheet(self, excel_file: pd.ExcelFile, sheet_name: str) -> List[EquipmentData]:
        """Procesar una hoja específica"""
        try:
            # Leer toda la hoja
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            
            if df.empty:
                logger.warning(f"Hoja '{sheet_name}' está vacía")
                return []
            
            # Detectar estructura de la hoja
            structure = self._analyze_sheet_structure(df, sheet_name)
            
            if structure['type'] == 'grouped':
                return self._process_grouped_structure(df, sheet_name, structure)
            else:
                return self._process_tabular_structure(df, sheet_name, structure)
                
        except Exception as e:
            logger.error(f"Error procesando hoja '{sheet_name}': {e}")
            self.errors.append(f"Error en hoja '{sheet_name}': {e}")
            return []
    
    def _analyze_sheet_structure(self, df: pd.DataFrame, sheet_name: str) -> Dict[str, Any]:
        """Analizar la estructura de la hoja"""
        structure = {
            'type': 'tabular',  # 'tabular' o 'grouped'
            'equipment_col': None,
            'date_col': None,
            'description_cols': [],
            'date_rows': [],
            'equipment_changes': []
        }
        
        # Buscar columnas que parezcan equipos
        for i, col in enumerate(df.columns):
            col_str = str(col).upper()
            if any(keyword in col_str for keyword in ['EQUIPO', 'MAQUINA', 'VEHICULO']):
                structure['equipment_col'] = i
                break
        
        # Buscar columnas que parezcan fechas
        for i, col in enumerate(df.columns):
            col_str = str(col).upper()
            if 'FECHA' in col_str:
                structure['date_col'] = i
                break
        
        # Analizar contenido para detectar estructura agrupada
        if structure['equipment_col'] is not None:
            equipo_col = df.iloc[:, structure['equipment_col']]
            
            # Detectar cambios de equipo (filas donde cambia el nombre del equipo)
            last_equipment = None
            for idx, value in equipo_col.items():
                clean_value = self._clean_string(str(value))
                if clean_value and clean_value != last_equipment:
                    if clean_value.lower() not in ['equipo', 'equipos', 'nan']:
                        structure['equipment_changes'].append({
                            'row': idx,
                            'equipment': clean_value
                        })
                        last_equipment = clean_value
        
        # Detectar filas con fechas
        if structure['date_col'] is not None:
            date_col = df.iloc[:, structure['date_col']]
            for idx, value in date_col.items():
                parsed_date = self._parse_date(value)
                if parsed_date:
                    structure['date_rows'].append({
                        'row': idx,
                        'date': parsed_date,
                        'raw_value': value
                    })
        
        # Determinar tipo de estructura
        if len(structure['equipment_changes']) > 1 and len(structure['date_rows']) > len(structure['equipment_changes']):
            structure['type'] = 'grouped'
        
        logger.info(f"Estructura de '{sheet_name}': {structure['type']}")
        logger.info(f"  Equipos detectados: {len(structure['equipment_changes'])}")
        logger.info(f"  Fechas detectadas: {len(structure['date_rows'])}")
        
        return structure
    
    def _process_grouped_structure(self, df: pd.DataFrame, sheet_name: str, structure: Dict) -> List[EquipmentData]:
        """Procesar estructura agrupada (múltiples trabajos por equipo)"""
        equipment_list = []
        
        # Procesar cada equipo
        for i, equipment_change in enumerate(structure['equipment_changes']):
            equipment_name = equipment_change['equipment']
            start_row = equipment_change['row']
            
            # Determinar fin del grupo (siguiente equipo o fin de datos)
            if i + 1 < len(structure['equipment_changes']):
                end_row = structure['equipment_changes'][i + 1]['row']
            else:
                end_row = len(df)
            
            # Extraer trabajos para este equipo
            trabajos = self._extract_jobs_for_equipment(
                df, sheet_name, equipment_name, start_row, end_row, structure
            )
            
            if trabajos:
                equipment_data = EquipmentData(
                    propietario=sheet_name,
                    nombre=equipment_name,
                    trabajos=trabajos
                )
                equipment_list.append(equipment_data)
        
        return equipment_list
    
    def _process_tabular_structure(self, df: pd.DataFrame, sheet_name: str, structure: Dict) -> List[EquipmentData]:
        """Procesar estructura tabular (una fila por trabajo)"""
        equipment_dict = {}
        
        for idx, row in df.iterrows():
            try:
                # Obtener nombre del equipo
                if structure['equipment_col'] is not None:
                    equipment_name = self._clean_string(str(row.iloc[structure['equipment_col']]))
                else:
                    equipment_name = f"Equipo_{idx}"
                
                if not equipment_name or equipment_name.lower() in ['equipo', 'equipos', 'nan']:
                    continue
                
                # Obtener fecha
                if structure['date_col'] is not None:
                    fecha = self._parse_date(row.iloc[structure['date_col']])
                else:
                    fecha = date.today()
                
                if not fecha:
                    fecha = date.today()
                
                # Construir descripción
                descripcion_parts = []
                for col_idx, value in enumerate(row):
                    if col_idx not in [structure['equipment_col'], structure['date_col']]:
                        clean_value = self._clean_string(str(value))
                        if clean_value and clean_value.lower() not in ['nan', 'none']:
                            descripcion_parts.append(clean_value)
                
                descripcion = " | ".join(descripcion_parts) if descripcion_parts else "Trabajo sin descripción"
                
                # Extraer costo si es posible
                costo = self._extract_cost(descripcion)
                
                # Crear trabajo
                trabajo = WorkEntry(fecha=fecha, descripcion=descripcion, costo=costo)
                
                # Agrupar por equipo
                key = f"{sheet_name}_{equipment_name}"
                if key not in equipment_dict:
                    equipment_dict[key] = EquipmentData(
                        propietario=sheet_name,
                        nombre=equipment_name,
                        trabajos=[]
                    )
                
                equipment_dict[key].trabajos.append(trabajo)
                
            except Exception as e:
                logger.warning(f"Error procesando fila {idx} en '{sheet_name}': {e}")
                continue
        
        return list(equipment_dict.values())
    
    def _extract_jobs_for_equipment(self, df: pd.DataFrame, sheet_name: str, equipment_name: str, 
                                   start_row: int, end_row: int, structure: Dict) -> List[WorkEntry]:
        """Extraer trabajos para un equipo específico en un rango de filas"""
        trabajos = []
        current_date = None
        current_items = []
        
        # Procesar filas del equipo
        for idx in range(start_row, min(end_row, len(df))):
            row = df.iloc[idx]
            
            # Verificar si hay una nueva fecha
            if structure['date_col'] is not None:
                fecha_raw = row.iloc[structure['date_col']]
                parsed_date = self._parse_date(fecha_raw)
                
                if parsed_date:
                    # Si teníamos una fecha anterior, crear trabajo con items acumulados
                    if current_date and current_items:
                        descripcion = " | ".join(current_items)
                        costo = self._extract_cost(descripcion)
                        trabajo = WorkEntry(fecha=current_date, descripcion=descripcion, costo=costo)
                        trabajos.append(trabajo)
                    
                    # Iniciar nueva fecha
                    current_date = parsed_date
                    current_items = []
            
            # Recopilar items (repuestos y mano de obra)
            for col_idx, value in enumerate(row):
                if col_idx not in [structure['equipment_col'], structure['date_col']]:
                    clean_value = self._clean_string(str(value))
                    if clean_value and clean_value.lower() not in ['nan', 'none', 'fecha', 'repuestos', 'mano de obra']:
                        current_items.append(clean_value)
        
        # Agregar último trabajo si existe
        if current_date and current_items:
            descripcion = " | ".join(current_items)
            costo = self._extract_cost(descripcion)
            trabajo = WorkEntry(fecha=current_date, descripcion=descripcion, costo=costo)
            trabajos.append(trabajo)
        elif current_items:  # Si hay items pero no fecha, usar fecha actual
            descripcion = " | ".join(current_items)
            costo = self._extract_cost(descripcion)
            trabajo = WorkEntry(fecha=date.today(), descripcion=descripcion, costo=costo)
            trabajos.append(trabajo)
        
        return trabajos
    
    def _clean_string(self, text: str) -> str:
        """Limpiar y normalizar texto"""
        if pd.isna(text) or text is None:
            return ""
        
        text = str(text).strip()
        if text.lower() in ['nan', 'none', '']:
            return ""
        
        return text
    
    def _parse_date(self, date_value) -> Optional[date]:
        """Parsear fecha con múltiples formatos"""
        if pd.isna(date_value) or date_value is None:
            return None
        
        # Si ya es un objeto datetime
        if isinstance(date_value, (datetime, date)):
            return date_value.date() if isinstance(date_value, datetime) else date_value
        
        date_str = str(date_value).strip()
        if not date_str or date_str.lower() in ['nan', 'none', '']:
            return None
        
        # Formatos de fecha a probar
        date_formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d',
            '%d/%m/%y', '%d-%m-%y', '%y-%m-%d',
            '%d.%m.%Y', '%d.%m.%y',
            '%d/%m', '%d-%m',
            '%d//%m//%Y'  # Formato especial detectado
        ]
        
        # Mapeo de meses en español
        month_mapping = {
            'ENE': 'JAN', 'FEB': 'FEB', 'MAR': 'MAR', 'ABR': 'APR',
            'MAY': 'MAY', 'JUN': 'JUN', 'JUL': 'JUL', 'AGO': 'AUG',
            'SEP': 'SEP', 'OCT': 'OCT', 'NOV': 'NOV', 'DIC': 'DEC'
        }
        
        # Reemplazar meses en español
        for es_month, en_month in month_mapping.items():
            date_str = date_str.replace(es_month, en_month)
        
        # Intentar parsear con diferentes formatos
        for fmt in date_formats:
            try:
                parsed = datetime.strptime(date_str, fmt)
                # Si no tiene año, usar año actual
                if parsed.year == 1900:
                    parsed = parsed.replace(year=datetime.now().year)
                return parsed.date()
            except ValueError:
                continue
        
        # Intentar con pandas
        try:
            return pd.to_datetime(date_str, dayfirst=True).date()
        except:
            pass
        
        return None
    
    def _extract_cost(self, text: str) -> float:
        """Extraer costo del texto"""
        # Buscar patrones de dinero
        money_patterns = [
            r'\$\s*(\d+(?:[.,]\d+)*)',  # $1000 o $1,000.50
            r'(\d+(?:[.,]\d+)*)\s*\$',  # 1000$ o 1,000.50$
            r'(\d+(?:[.,]\d+)*)\s*pesos',  # 1000 pesos
        ]
        
        for pattern in money_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    # Tomar el primer match y convertir
                    amount_str = matches[0].replace(',', '').replace('.', '')
                    return float(amount_str)
                except ValueError:
                    continue
        
        return 0.0

# Función de compatibilidad
def validate_excel_file_v2(file_path: str) -> Dict[str, Any]:
    """Validar archivo Excel con el nuevo parser"""
    importer = ExcelImporterV2()
    equipment_data = importer.parse_excel_file(file_path)
    
    total_records = sum(len(eq.trabajos) for eq in equipment_data)
    
    return {
        'valid': len(equipment_data) > 0,
        'summary': {
            'total_equipment': len(equipment_data),
            'estimated_records': total_records,
            'sheets_processed': len(set(eq.propietario for eq in equipment_data))
        },
        'equipment_data': equipment_data,
        'errors': importer.errors,
        'warnings': importer.warnings
    }
