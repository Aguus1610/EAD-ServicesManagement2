"""
Utilidades de validación y seguridad para EAD Oleohidráulica
"""
import re
from datetime import datetime, date
from typing import Dict, List, Optional, Union, Any


class ValidationError(Exception):
    """Excepción personalizada para errores de validación"""
    pass


class FieldValidator:
    """Validador de campos con múltiples reglas"""
    
    def __init__(self, field_name: str):
        self.field_name = field_name
        self.errors = []
    
    def required(self, value: Any) -> 'FieldValidator':
        """Validar que el campo sea requerido"""
        if not value or (isinstance(value, str) and not value.strip()):
            self.errors.append(f"{self.field_name} es requerido")
        return self
    
    def min_length(self, value: str, min_len: int) -> 'FieldValidator':
        """Validar longitud mínima"""
        if value and len(str(value).strip()) < min_len:
            self.errors.append(f"{self.field_name} debe tener al menos {min_len} caracteres")
        return self
    
    def max_length(self, value: str, max_len: int) -> 'FieldValidator':
        """Validar longitud máxima"""
        if value and len(str(value).strip()) > max_len:
            self.errors.append(f"{self.field_name} no puede exceder {max_len} caracteres")
        return self
    
    def numeric(self, value: Union[str, int, float]) -> 'FieldValidator':
        """Validar que sea numérico"""
        if value is not None:
            try:
                float(str(value))
            except (ValueError, TypeError):
                self.errors.append(f"{self.field_name} debe ser un número válido")
        return self
    
    def positive(self, value: Union[str, int, float]) -> 'FieldValidator':
        """Validar que sea positivo"""
        if value is not None:
            try:
                num = float(str(value))
                if num < 0:
                    self.errors.append(f"{self.field_name} debe ser un número positivo")
            except (ValueError, TypeError):
                pass  # El error numérico ya se captura en numeric()
        return self
    
    def integer(self, value: Union[str, int]) -> 'FieldValidator':
        """Validar que sea entero"""
        if value is not None:
            try:
                int(str(value))
            except (ValueError, TypeError):
                self.errors.append(f"{self.field_name} debe ser un número entero")
        return self
    
    def year_range(self, value: Union[str, int], min_year: int = 1900, max_year: Optional[int] = None) -> 'FieldValidator':
        """Validar rango de años"""
        if max_year is None:
            max_year = datetime.now().year + 5
        
        if value is not None:
            try:
                year = int(str(value))
                if year < min_year or year > max_year:
                    self.errors.append(f"{self.field_name} debe estar entre {min_year} y {max_year}")
            except (ValueError, TypeError):
                pass  # El error numérico ya se captura en integer()
        return self
    
    def date_format(self, value: str, format_str: str = '%Y-%m-%d') -> 'FieldValidator':
        """Validar formato de fecha"""
        if value:
            try:
                datetime.strptime(str(value), format_str)
            except ValueError:
                self.errors.append(f"{self.field_name} debe tener formato válido de fecha")
        return self
    
    def regex(self, value: str, pattern: str, message: str = None) -> 'FieldValidator':
        """Validar con expresión regular"""
        if value:
            if not re.match(pattern, str(value)):
                msg = message or f"{self.field_name} tiene formato inválido"
                self.errors.append(msg)
        return self
    
    def email(self, value: str) -> 'FieldValidator':
        """Validar formato de email"""
        if value:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return self.regex(value, email_pattern, f"{self.field_name} debe ser un email válido")
        return self
    
    def alphanumeric(self, value: str, allow_spaces: bool = True) -> 'FieldValidator':
        """Validar que sea alfanumérico"""
        if value:
            pattern = r'^[a-zA-Z0-9\s]+$' if allow_spaces else r'^[a-zA-Z0-9]+$'
            return self.regex(value, pattern, f"{self.field_name} solo puede contener letras y números")
        return self
    
    def no_sql_injection(self, value: str) -> 'FieldValidator':
        """Validar contra inyección SQL básica"""
        if value:
            dangerous_patterns = [
                r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
                r'(--|;|/\*|\*/)',
                r"('|\"|`)",
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, str(value), re.IGNORECASE):
                    self.errors.append(f"{self.field_name} contiene caracteres no permitidos")
                    break
        return self
    
    def no_xss(self, value: str) -> 'FieldValidator':
        """Validar contra XSS básico"""
        if value:
            dangerous_patterns = [
                r'<script[^>]*>.*?</script>',
                r'javascript:',
                r'on\w+\s*=',
                r'<iframe[^>]*>.*?</iframe>',
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, str(value), re.IGNORECASE):
                    self.errors.append(f"{self.field_name} contiene contenido no permitido")
                    break
        return self
    
    def get_errors(self) -> List[str]:
        """Obtener lista de errores"""
        return self.errors
    
    def is_valid(self) -> bool:
        """Verificar si es válido"""
        return len(self.errors) == 0


class FormValidator:
    """Validador completo de formularios"""
    
    def __init__(self):
        self.errors = {}
    
    def validate_field(self, field_name: str, value: Any) -> FieldValidator:
        """Crear validador para un campo específico"""
        validator = FieldValidator(field_name)
        self.errors[field_name] = validator
        return validator
    
    def get_errors(self) -> Dict[str, List[str]]:
        """Obtener todos los errores agrupados por campo"""
        return {
            field: validator.get_errors() 
            for field, validator in self.errors.items() 
            if not validator.is_valid()
        }
    
    def get_all_errors(self) -> List[str]:
        """Obtener todos los errores como lista plana"""
        all_errors = []
        for validator in self.errors.values():
            all_errors.extend(validator.get_errors())
        return all_errors
    
    def is_valid(self) -> bool:
        """Verificar si todo el formulario es válido"""
        return all(validator.is_valid() for validator in self.errors.values())
    
    def raise_if_invalid(self):
        """Lanzar excepción si hay errores"""
        if not self.is_valid():
            errors = self.get_all_errors()
            raise ValidationError("; ".join(errors))


# Validadores específicos para el dominio del negocio
class EquipmentValidator:
    """Validador específico para equipos"""
    
    @staticmethod
    def validate(data: Dict[str, Any]) -> FormValidator:
        validator = FormValidator()
        
        # Marca - requerida, longitud mínima, sin caracteres peligrosos
        validator.validate_field("Marca", data.get('marca')) \
            .required(data.get('marca')) \
            .min_length(data.get('marca', ''), 2) \
            .max_length(data.get('marca', ''), 50) \
            .no_sql_injection(data.get('marca', '')) \
            .no_xss(data.get('marca', ''))
        
        # Modelo - requerido, longitud mínima
        validator.validate_field("Modelo", data.get('modelo')) \
            .required(data.get('modelo')) \
            .min_length(data.get('modelo', ''), 2) \
            .max_length(data.get('modelo', ''), 50) \
            .no_sql_injection(data.get('modelo', '')) \
            .no_xss(data.get('modelo', ''))
        
        # Año - requerido, entero, rango válido
        validator.validate_field("Año", data.get('anio')) \
            .required(data.get('anio')) \
            .integer(data.get('anio')) \
            .year_range(data.get('anio'))
        
        # Número de serie - requerido, longitud mínima
        validator.validate_field("Número de Serie", data.get('n_serie')) \
            .required(data.get('n_serie')) \
            .min_length(data.get('n_serie', ''), 3) \
            .max_length(data.get('n_serie', ''), 100) \
            .no_sql_injection(data.get('n_serie', '')) \
            .no_xss(data.get('n_serie', ''))
        
        # Campos opcionales
        if data.get('propietario'):
            validator.validate_field("Propietario", data.get('propietario')) \
                .max_length(data.get('propietario', ''), 100) \
                .no_sql_injection(data.get('propietario', '')) \
                .no_xss(data.get('propietario', ''))
        
        if data.get('vehiculo'):
            validator.validate_field("Vehículo", data.get('vehiculo')) \
                .max_length(data.get('vehiculo', ''), 100) \
                .no_sql_injection(data.get('vehiculo', '')) \
                .no_xss(data.get('vehiculo', ''))
        
        if data.get('dominio'):
            validator.validate_field("Dominio", data.get('dominio')) \
                .max_length(data.get('dominio', ''), 20) \
                .alphanumeric(data.get('dominio', '')) \
                .no_sql_injection(data.get('dominio', '')) \
                .no_xss(data.get('dominio', ''))
        
        if data.get('notes'):
            validator.validate_field("Notas", data.get('notes')) \
                .max_length(data.get('notes', ''), 1000) \
                .no_sql_injection(data.get('notes', '')) \
                .no_xss(data.get('notes', ''))
        
        return validator


class JobValidator:
    """Validador específico para trabajos"""
    
    @staticmethod
    def validate(data: Dict[str, Any]) -> FormValidator:
        validator = FormValidator()
        
        # Fecha del trabajo - requerida, formato válido
        validator.validate_field("Fecha del trabajo", data.get('date_done')) \
            .required(data.get('date_done')) \
            .date_format(data.get('date_done', ''))
        
        # Descripción - requerida, longitud mínima
        validator.validate_field("Descripción", data.get('description')) \
            .required(data.get('description')) \
            .min_length(data.get('description', ''), 10) \
            .max_length(data.get('description', ''), 2000) \
            .no_sql_injection(data.get('description', '')) \
            .no_xss(data.get('description', ''))
        
        # Presupuesto - opcional, debe ser numérico positivo
        if data.get('budget'):
            validator.validate_field("Presupuesto", data.get('budget')) \
                .numeric(data.get('budget')) \
                .positive(data.get('budget'))
        
        # Días para próximo service - opcional, entero positivo
        if data.get('next_service_days'):
            validator.validate_field("Días para próximo service", data.get('next_service_days')) \
                .integer(data.get('next_service_days')) \
                .positive(data.get('next_service_days'))
        
        # Notas - opcional
        if data.get('notes'):
            validator.validate_field("Notas", data.get('notes')) \
                .max_length(data.get('notes', ''), 1000) \
                .no_sql_injection(data.get('notes', '')) \
                .no_xss(data.get('notes', ''))
        
        return validator


# Utilidades de sanitización
class Sanitizer:
    """Utilidades para limpiar y sanitizar datos de entrada"""
    
    @staticmethod
    def clean_string(value: str) -> str:
        """Limpiar string básico"""
        if not value:
            return ""
        
        # Eliminar espacios extra
        cleaned = str(value).strip()
        
        # Eliminar caracteres de control
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
        
        # Normalizar espacios múltiples
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned
    
    @staticmethod
    def clean_html(value: str) -> str:
        """Limpiar HTML básico (escape de caracteres)"""
        if not value:
            return ""
        
        # Escapar caracteres HTML básicos
        html_escapes = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
        }
        
        cleaned = str(value)
        for char, escape in html_escapes.items():
            cleaned = cleaned.replace(char, escape)
        
        return cleaned
    
    @staticmethod
    def clean_sql(value: str) -> str:
        """Limpiar para prevenir inyección SQL básica"""
        if not value:
            return ""
        
        # Escapar comillas simples duplicándolas
        cleaned = str(value).replace("'", "''")
        
        return cleaned
    
    @staticmethod
    def sanitize_form_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitizar todos los campos de un formulario"""
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = Sanitizer.clean_string(value)
            else:
                sanitized[key] = value
        
        return sanitized


# Funciones de utilidad
def validate_equipment_data(data: Dict[str, Any], sanitize: bool = True) -> Dict[str, Any]:
    """
    Validar y opcionalmente sanitizar datos de equipo
    
    Args:
        data: Diccionario con datos del equipo
        sanitize: Si True, sanitiza los datos antes de validar
    
    Returns:
        Diccionario con datos sanitizados
    
    Raises:
        ValidationError: Si los datos no son válidos
    """
    if sanitize:
        data = Sanitizer.sanitize_form_data(data)
    
    validator = EquipmentValidator.validate(data)
    validator.raise_if_invalid()
    
    return data


def validate_job_data(data: Dict[str, Any], sanitize: bool = True) -> Dict[str, Any]:
    """
    Validar y opcionalmente sanitizar datos de trabajo
    
    Args:
        data: Diccionario con datos del trabajo
        sanitize: Si True, sanitiza los datos antes de validar
    
    Returns:
        Diccionario con datos sanitizados
    
    Raises:
        ValidationError: Si los datos no son válidos
    """
    if sanitize:
        data = Sanitizer.sanitize_form_data(data)
    
    validator = JobValidator.validate(data)
    validator.raise_if_invalid()
    
    return data
