"""
Script para probar el parser mejorado de Excel
"""
from utils.excel_importer import ExcelImporter, validate_excel_file
import logging

# Configurar logging para ver los detalles
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_parser():
    print("Probando parser mejorado de Excel...")
    print("=" * 50)
    
    # Probar validación
    print("\n1. VALIDANDO ARCHIVO...")
    validation = validate_excel_file('datos_realistas.xlsx')
    
    print(f"Archivo valido: {validation['valid']}")
    print(f"Resumen: {validation['summary']}")
    
    for sheet in validation['sheets']:
        print(f"\nHoja: {sheet['name']}")
        print(f"   - Valida: {sheet['valid']}")
        print(f"   - Confianza: {sheet['confidence']}%")
        print(f"   - Registros estimados: {sheet['estimated_records']}")
        print(f"   - Mapeo: {sheet['column_mapping']}")
        if sheet['issues']:
            print(f"   - Problemas: {sheet['issues']}")
    
    # Probar importación
    print("\n\n2. PROBANDO IMPORTACION...")
    importer = ExcelImporter()
    equipment_data = importer.parse_excel_file('datos_realistas.xlsx')
    
    print(f"\nEquipos encontrados: {len(equipment_data)}")
    
    for eq in equipment_data:
        print(f"\n{eq.nombre} (Propietario: {eq.propietario})")
        print(f"   Trabajos: {len(eq.trabajos)}")
        for trabajo in eq.trabajos[:2]:  # Mostrar solo los primeros 2
            print(f"      - {trabajo.fecha}: {trabajo.descripcion[:60]}...")
            print(f"        Presupuesto: ${trabajo.presupuesto}")
    
    # Mostrar errores y advertencias
    if importer.errors:
        print(f"\nErrores: {len(importer.errors)}")
        for error in importer.errors:
            print(f"   - {error}")
    
    if importer.warnings:
        print(f"\nAdvertencias: {len(importer.warnings)}")
        for warning in importer.warnings:
            print(f"   - {warning}")

if __name__ == "__main__":
    test_parser()
