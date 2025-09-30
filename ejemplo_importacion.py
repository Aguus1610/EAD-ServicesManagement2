"""
Script para crear un archivo Excel de ejemplo para probar la importación
"""
import pandas as pd
from datetime import datetime, timedelta
import random

# Crear datos de ejemplo
def create_sample_excel():
    # Datos de ejemplo para diferentes clientes
    clientes_data = {
        'TRANSPORTES MARTINEZ': [
            {
                'EQUIPO': 'SCANIA R450 2018',
                'FECHA': '15/01/2024',
                'REPUESTOS': 'Filtro de aceite, Aceite motor 15W40 - $25000',
                'MANO DE OBRA': 'Cambio de aceite y filtros - $15000'
            },
            {
                'EQUIPO': 'SCANIA R450 2018',
                'FECHA': '20/03/2024',
                'REPUESTOS': 'Pastillas de freno delanteras - $45000',
                'MANO DE OBRA': 'Cambio de pastillas y revisión sistema - $20000'
            },
            {
                'EQUIPO': 'VOLVO FH16 2020',
                'FECHA': '10/02/2024',
                'REPUESTOS': 'Filtro de aire, Aceite hidráulico - $18000',
                'MANO DE OBRA': 'Service preventivo completo - $25000'
            },
            {
                'EQUIPO': 'VOLVO FH16 2020',
                'FECHA': '15/04/2024',
                'REPUESTOS': 'Correa de distribución, Tensor - $35000',
                'MANO DE OBRA': 'Cambio de distribución - $40000'
            }
        ],
        'CONSTRUCCIONES LOPEZ': [
            {
                'EQUIPO': 'CATERPILLAR 320D',
                'FECHA': '05/01/2024',
                'REPUESTOS': 'Filtros hidráulicos x3, Aceite hidráulico - $55000',
                'MANO DE OBRA': 'Service 500 horas - $30000'
            },
            {
                'EQUIPO': 'CATERPILLAR 320D',
                'FECHA': '20/02/2024',
                'REPUESTOS': 'Cadenas de oruga, Pines - $120000',
                'MANO DE OBRA': 'Cambio de cadenas completo - $80000'
            },
            {
                'EQUIPO': 'JOHN DEERE 6120',
                'FECHA': '12/01/2024',
                'REPUESTOS': 'Filtro combustible, Aceite motor - $22000',
                'MANO DE OBRA': 'Service preventivo - $18000'
            },
            {
                'EQUIPO': 'JOHN DEERE 6120',
                'FECHA': '25/03/2024',
                'REPUESTOS': 'Neumáticos traseros x2 - $85000',
                'MANO DE OBRA': 'Cambio de neumáticos y alineación - $25000'
            }
        ],
        'AGROPECUARIA SAN MARTIN': [
            {
                'EQUIPO': 'MASSEY FERGUSON 5650',
                'FECHA': '08/01/2024',
                'REPUESTOS': 'Filtro de aire, Aceite motor, Filtro aceite - $28000',
                'MANO DE OBRA': 'Service 200 horas - $20000'
            },
            {
                'EQUIPO': 'MASSEY FERGUSON 5650',
                'FECHA': '15/02/2024',
                'REPUESTOS': 'Embrague completo - $95000',
                'MANO DE OBRA': 'Cambio de embrague - $60000'
            },
            {
                'EQUIPO': 'NEW HOLLAND T7060',
                'FECHA': '22/01/2024',
                'REPUESTOS': 'Filtros varios, Aceites - $32000',
                'MANO DE OBRA': 'Service completo - $25000'
            },
            {
                'EQUIPO': 'DEUTZ FAHR 6160',
                'FECHA': '30/01/2024',
                'REPUESTOS': 'Bomba hidráulica - $75000',
                'MANO DE OBRA': 'Reparación sistema hidráulico - $45000'
            }
        ]
    }
    
    # Crear archivo Excel con múltiples hojas
    with pd.ExcelWriter('datos_ejemplo.xlsx', engine='openpyxl') as writer:
        for cliente, trabajos in clientes_data.items():
            df = pd.DataFrame(trabajos)
            df.to_excel(writer, sheet_name=cliente, index=False)
    
    print("Archivo 'datos_ejemplo.xlsx' creado exitosamente!")
    print(f"Hojas creadas: {list(clientes_data.keys())}")
    print(f"Total de trabajos: {sum(len(trabajos) for trabajos in clientes_data.values())}")

if __name__ == "__main__":
    create_sample_excel()
