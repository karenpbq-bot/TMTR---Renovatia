"""
Módulo de Integración con Google Sheets para Consultorio Psicológico
===================================================================
Este módulo permite sincronizar y almacenar automáticamente la información
del consultorio (Usuarios, Citas, Historias Clínicas y Sesiones de Evolución)
directamente en un libro de cálculo de Google Drive usando gspread y Google Sheets API v4.
"""

import os
import json

# Nombre predeterminado del libro de Google Sheets
GOOGLE_SHEET_NAME = os.environ.get('GOOGLE_SHEET_NAME', 'Consultorio_Psicologico_BD')

def obtener_cliente_gspread():
    """
    Inicializa la conexión autenticada con la API de Google Sheets usando Service Account.
    Requiere que el archivo 'credentials.json' de Google Cloud esté presente en el proyecto.
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        print("⚠️ Las librerías 'gspread' o 'google-auth' no están instaladas.")
        return None

    creds_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'credentials.json')

    if not os.path.exists(creds_path):
        print(f"ℹ️ Archivo de credenciales de Google ({creds_path}) no encontrado.")
        print("Siga las instrucciones en la guía para colocar su archivo credentials.json.")
        return None

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    try:
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"❌ Error al autenticar con Google Sheets: {e}")
        return None

def registrar_fila_en_sheet(nombre_pestana, datos_fila):
    """
    Agrega una nueva fila de datos en una pestaña específica del libro de Google Sheets.
    
    Ejemplo de uso:
    registrar_fila_en_sheet('Citas', ['Cita #10', 'Ana Gómez', 'Dr. Carlos Mendoza', '2026-08-25 10:00', 'Programada'])
    """
    client = obtener_cliente_gspread()
    if not client:
        return False

    try:
        sheet = client.open(GOOGLE_SHEET_NAME)
        
        # Intentar obtener la pestaña, si no existe la crea con encabezados
        try:
            worksheet = sheet.worksheet(nombre_pestana)
        except Exception:
            worksheet = sheet.add_worksheet(title=nombre_pestana, rows="1000", cols="20")
            print(f"✅ Pestaña '{nombre_pestana}' creada en Google Sheets.")

        worksheet.append_row(datos_fila)
        print(f"📊 Registro sincronizado exitosamente en Google Sheets [{nombre_pestana}]")
        return True
    except Exception as e:
        print(f"❌ Error al guardar en Google Sheets: {e}")
        return False
