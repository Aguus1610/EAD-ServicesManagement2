"""
Probar el nuevo parser v2
"""
from utils.excel_importer_v2 import ExcelImporterV2, validate_excel_file_v2
import os

def test_parser_v2():
    print("="*60)
    print("PROBANDO PARSER V2")
    print("="*60)
    
    # Buscar archivos Excel
    archivos = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    
    for archivo in archivos:
        print(f"\nPROCESANDO: {archivo}")
        print("-" * 40)
        
        # Usar el nuevo parser
        importer = ExcelImporterV2()
        equipment_data = importer.parse_excel_file(archivo)
        
        total_trabajos = sum(len(eq.trabajos) for eq in equipment_data)
        
        print(f"Equipos encontrados: {len(equipment_data)}")
        print(f"Trabajos totales: {total_trabajos}")
        
        # Mostrar algunos ejemplos
        for i, eq in enumerate(equipment_data[:5]):  # Primeros 5
            print(f"\n  {eq.propietario} - {eq.nombre}:")
            print(f"    Trabajos: {len(eq.trabajos)}")
            for j, trabajo in enumerate(eq.trabajos[:2]):  # Primeros 2 trabajos
                desc_short = trabajo.descripcion[:80] + "..." if len(trabajo.descripcion) > 80 else trabajo.descripcion
                print(f"      {j+1}. {trabajo.fecha} - {desc_short}")
                if trabajo.costo > 0:
                    print(f"         Costo: ${trabajo.costo}")
        
        if len(equipment_data) > 5:
            print(f"  ... y {len(equipment_data) - 5} equipos más")
        
        # Errores y advertencias
        if importer.errors:
            print(f"\nERRORES ({len(importer.errors)}):")
            for error in importer.errors[:3]:
                print(f"  - {error}")
        
        if importer.warnings:
            print(f"\nADVERTENCIAS ({len(importer.warnings)}):")
            for warning in importer.warnings[:3]:
                print(f"  - {warning}")

if __name__ == "__main__":
    test_parser_v2()
