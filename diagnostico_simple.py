"""
Diagnóstico simple para importación de Excel
"""
import pandas as pd
from utils.excel_importer import ExcelImporter, validate_excel_file
import os

def diagnosticar_simple(archivo):
    print("="*60)
    print(f"DIAGNOSTICO DE: {archivo}")
    print("="*60)
    
    try:
        # 1. Análisis básico
        excel_file = pd.ExcelFile(archivo)
        print(f"\nHojas encontradas: {excel_file.sheet_names}")
        
        total_filas_raw = 0
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(archivo, sheet_name=sheet_name)
            filas_no_vacias = df.dropna(how='all').shape[0]
            total_filas_raw += filas_no_vacias
            print(f"  {sheet_name}: {df.shape[0]} filas totales, {filas_no_vacias} no vacias")
        
        print(f"\nTOTAL FILAS NO VACIAS: {total_filas_raw}")
        
        # 2. Validación
        validation = validate_excel_file(archivo)
        print(f"\nVALIDACION:")
        print(f"  Valido: {validation['valid']}")
        print(f"  Registros estimados: {validation['summary']['estimated_records']}")
        
        # 3. Importación real
        importer = ExcelImporter()
        equipment_data = importer.parse_excel_file(archivo)
        
        total_trabajos = sum(len(eq.trabajos) for eq in equipment_data)
        print(f"\nIMPORTACION:")
        print(f"  Equipos: {len(equipment_data)}")
        print(f"  Trabajos: {total_trabajos}")
        
        # Detalles por cliente
        for eq_data in equipment_data:
            print(f"    {eq_data.propietario} - {eq_data.nombre}: {len(eq_data.trabajos)} trabajos")
        
        # Errores
        if importer.errors:
            print(f"\nERRORES ({len(importer.errors)}):")
            for error in importer.errors[:5]:  # Solo primeros 5
                print(f"  - {error}")
        
        if importer.warnings:
            print(f"\nADVERTENCIAS ({len(importer.warnings)}):")
            for warning in importer.warnings[:5]:  # Solo primeras 5
                print(f"  - {warning}")
        
        print(f"\nRESUMEN:")
        print(f"  Filas brutas: {total_filas_raw}")
        print(f"  Trabajos procesados: {total_trabajos}")
        print(f"  Diferencia: {total_filas_raw - total_trabajos}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Buscar archivos Excel
    archivos = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    
    if not archivos:
        print("No se encontraron archivos Excel")
    else:
        for archivo in archivos:
            diagnosticar_simple(archivo)
            print("\n")
