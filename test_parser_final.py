"""
Probar el parser final
"""
from utils.excel_parser_final import ExcelParserFinal, validate_excel_file_final
import os

def test_parser_final():
    print("="*80)
    print("PROBANDO PARSER FINAL")
    print("="*80)
    
    # Buscar archivos Excel
    archivos = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    
    for archivo in archivos:
        if 'Equipos' in archivo:  # Solo el archivo principal
            print(f"\nPROCESANDO: {archivo}")
            print("-" * 60)
            
            # Usar el parser final
            parser = ExcelParserFinal()
            equipment_data = parser.parse_excel_file(archivo)
            
            total_trabajos = sum(len(eq.trabajos) for eq in equipment_data)
            
            print(f"Equipos encontrados: {len(equipment_data)}")
            print(f"Trabajos totales: {total_trabajos}")
            
            # Agrupar por propietario
            propietarios = {}
            for eq in equipment_data:
                if eq.propietario not in propietarios:
                    propietarios[eq.propietario] = {'equipos': 0, 'trabajos': 0}
                propietarios[eq.propietario]['equipos'] += 1
                propietarios[eq.propietario]['trabajos'] += len(eq.trabajos)
            
            print(f"\nRESUMEN POR PROPIETARIO:")
            for prop, stats in propietarios.items():
                print(f"  {prop}: {stats['equipos']} equipos, {stats['trabajos']} trabajos")
            
            # Mostrar algunos ejemplos detallados
            print(f"\nEJEMPLOS DETALLADOS:")
            for i, eq in enumerate(equipment_data[:5]):  # Primeros 5
                print(f"\n  {i+1}. {eq.propietario} - {eq.nombre}:")
                print(f"     Trabajos: {len(eq.trabajos)}")
                for j, trabajo in enumerate(eq.trabajos[:2]):  # Primeros 2 trabajos
                    desc_short = trabajo.descripcion[:100] + "..." if len(trabajo.descripcion) > 100 else trabajo.descripcion
                    print(f"       {j+1}. {trabajo.fecha} - {desc_short}")
                    if trabajo.presupuesto > 0:
                        print(f"          Presupuesto: ${trabajo.presupuesto}")
            
            # Errores y advertencias
            if parser.errors:
                print(f"\nERRORES ({len(parser.errors)}):")
                for error in parser.errors[:3]:
                    print(f"  - {error}")
            
            if parser.warnings:
                print(f"\nADVERTENCIAS ({len(parser.warnings)}):")
                for warning in parser.warnings[:3]:
                    print(f"  - {warning}")
            
            break

if __name__ == "__main__":
    test_parser_final()
