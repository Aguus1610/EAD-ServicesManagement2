"""
Script de diagnóstico detallado para la importación de Excel
"""
import pandas as pd
import openpyxl
from utils.excel_importer import ExcelImporter, validate_excel_file
import logging

# Configurar logging detallado
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

def diagnosticar_archivo_excel(archivo):
    print("="*80)
    print(f"DIAGNOSTICO DETALLADO DE: {archivo}")
    print("="*80)
    
    try:
        # 1. Análisis básico con pandas
        print("\n1. ANÁLISIS BÁSICO CON PANDAS:")
        excel_file = pd.ExcelFile(archivo)
        print(f"   Hojas encontradas: {excel_file.sheet_names}")
        
        total_filas_brutas = 0
        
        for sheet_name in excel_file.sheet_names:
            print(f"\n   Hoja: '{sheet_name}'")
            
            # Leer toda la hoja sin procesar
            df_raw = pd.read_excel(archivo, sheet_name=sheet_name)
            print(f"      - Dimensiones brutas: {df_raw.shape}")
            print(f"      - Columnas: {list(df_raw.columns)}")
            
            # Contar filas no vacías
            filas_no_vacias = df_raw.dropna(how='all').shape[0]
            print(f"      - Filas no vacias: {filas_no_vacias}")
            total_filas_brutas += filas_no_vacias
            
            # Mostrar primeras filas
            print(f"      - Primeras 3 filas:")
            for i, row in df_raw.head(3).iterrows():
                print(f"        Fila {i+1}: {dict(row)}")
        
        print(f"\n   TOTAL FILAS NO VACIAS EN TODO EL ARCHIVO: {total_filas_brutas}")
        
        # 2. Análisis con el validador
        print("\n2. ANÁLISIS CON VALIDADOR:")
        validation = validate_excel_file(archivo)
        print(f"   ✅ Válido: {validation['valid']}")
        print(f"   📈 Resumen: {validation['summary']}")
        
        for sheet in validation['sheets']:
            print(f"\n   📄 Hoja: '{sheet['name']}'")
            print(f"      • Válida: {sheet['valid']}")
            print(f"      • Confianza: {sheet['confidence']}%")
            print(f"      • Registros estimados: {sheet['estimated_records']}")
            print(f"      • Mapeo: {sheet['column_mapping']}")
            if sheet.get('issues'):
                print(f"      • Problemas: {sheet['issues']}")
        
        # 3. Análisis con el importador
        print("\n3. ANÁLISIS CON IMPORTADOR:")
        importer = ExcelImporter()
        equipment_data = importer.parse_excel_file(archivo)
        
        total_equipos = len(equipment_data)
        total_trabajos = sum(len(eq.trabajos) for eq in equipment_data)
        
        print(f"   🚛 Equipos procesados: {total_equipos}")
        print(f"   🔧 Trabajos procesados: {total_trabajos}")
        
        # Detalles por cliente
        for eq_data in equipment_data:
            print(f"\n   👤 Cliente: {eq_data.propietario}")
            print(f"      🚛 Equipo: {eq_data.nombre}")
            print(f"      🔧 Trabajos: {len(eq_data.trabajos)}")
            
            # Mostrar algunos trabajos
            for i, trabajo in enumerate(eq_data.trabajos[:3]):
                print(f"         {i+1}. {trabajo.fecha} - {trabajo.descripcion[:50]}...")
        
        # 4. Errores y advertencias
        if importer.errors:
            print(f"\n❌ ERRORES ({len(importer.errors)}):")
            for i, error in enumerate(importer.errors, 1):
                print(f"   {i}. {error}")
        
        if importer.warnings:
            print(f"\n⚠️ ADVERTENCIAS ({len(importer.warnings)}):")
            for i, warning in enumerate(importer.warnings, 1):
                print(f"   {i}. {warning}")
        
        # 5. Análisis detallado por hoja
        print("\n4. ANÁLISIS DETALLADO POR HOJA:")
        for sheet_name in excel_file.sheet_names:
            print(f"\n   📄 PROCESANDO HOJA: '{sheet_name}'")
            
            # Leer hoja completa
            df_full = pd.read_excel(archivo, sheet_name=sheet_name)
            print(f"      • Filas totales: {len(df_full)}")
            
            # Usar el detector de área de datos
            df_cleaned = importer._detect_data_area(df_full, sheet_name)
            print(f"      • Área de datos detectada: {df_cleaned.shape}")
            print(f"      • Columnas detectadas: {list(df_cleaned.columns)}")
            
            # Mapeo de columnas
            column_mapping = importer._intelligent_column_mapping(df_cleaned, sheet_name)
            print(f"      • Mapeo de columnas: {column_mapping}")
            
            # Analizar cada fila
            filas_validas = 0
            filas_descartadas = 0
            
            for index, row in df_cleaned.iterrows():
                equipo_name = importer._clean_string(row.get(column_mapping.get('EQUIPO'), ''))
                fecha_raw = row.get(column_mapping.get('FECHA'))
                fecha = importer._parse_date(fecha_raw)
                
                if equipo_name and fecha and equipo_name.lower() not in ['equipo', 'equipos', 'maquina', 'maquinas']:
                    filas_validas += 1
                else:
                    filas_descartadas += 1
                    print(f"         ❌ Fila {index+1} descartada:")
                    print(f"            • Equipo: '{equipo_name}'")
                    print(f"            • Fecha raw: '{fecha_raw}'")
                    print(f"            • Fecha parseada: {fecha}")
            
            print(f"      • Filas válidas: {filas_validas}")
            print(f"      • Filas descartadas: {filas_descartadas}")
        
        print("\n" + "="*80)
        print("📋 RESUMEN FINAL:")
        print(f"   • Filas brutas totales: {total_filas_brutas}")
        print(f"   • Equipos procesados: {total_equipos}")
        print(f"   • Trabajos procesados: {total_trabajos}")
        print(f"   • Registros estimados por validador: {validation['summary']['estimated_records']}")
        print("="*80)
        
    except Exception as e:
        print(f"❌ ERROR EN DIAGNÓSTICO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Diagnosticar el archivo de ejemplo
    diagnosticar_archivo_excel('datos_realistas.xlsx')
    
    # Si hay otro archivo, también diagnosticarlo
    import os
    archivos_excel = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    
    for archivo in archivos_excel:
        if archivo != 'datos_realistas.xlsx':
            print(f"\n\n🔍 También encontré: {archivo}")
            respuesta = input("¿Quieres diagnosticarlo también? (s/n): ")
            if respuesta.lower() == 's':
                diagnosticar_archivo_excel(archivo)
