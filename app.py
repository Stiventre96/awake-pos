import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import json
import traceback

# --- Configuración de Página ---
st.set_page_config(page_title="AWAKE SUPPS POS", page_icon="🛒", layout="wide")

st.markdown("""
<style>
    .cart-header { font-size: 1.5rem; font-weight: 600; margin-bottom: 1rem; color: #1E3A8A; }
    .total-text { font-size: 2rem; font-weight: 700; color: #10B981; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    div[data-testid="stSidebarNav"] { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- Autenticación de Google Sheets ---
# ¡QUITAMOS EL CACHÉ TOTALMENTE PARA EVITAR MENTIRAS DEL SERVIDOR!
def init_connection():
    try:
        if "gcp_service_account" not in st.secrets:
            return None
            
        creds_dict = dict(st.secrets["gcp_service_account"])
        raw_key = creds_dict.get("private_key", "")
        creds_dict["private_key"] = raw_key.replace("\\n", "\n").strip()
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(credentials)
    except Exception as e:
        return None

# --- Variables Globales ---
SHEET_ID = "1RiOliv-bbLr1r09grcdPVb7eVcPNJSMuQzIrSBpxUXc"

def load_inventory():
    client = init_connection()
    if not client:
        return pd.DataFrame()
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet("Inventario")
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        return pd.DataFrame()

# --- MENÚ LATERAL ---
st.sidebar.image("https://via.placeholder.com/150x50.png?text=AWAKE+SUPPS", width=150)
st.sidebar.title("Menú Principal")
menu = st.sidebar.radio("Navegación", ["💻 Punto de Venta (POS)", "📦 Carga de Mercancía", "🚑 MODO RESCATE (Error 404)"], label_visibility="collapsed")

# ==========================================
# MÓDULO DE RESCATE (NUEVO)
# ==========================================
if menu == "🚑 MODO RESCATE (Error 404)":
    st.title("🚑 Reparación Automática de Base de Datos")
    st.warning("Si el sistema no te deja acceder al Excel, vamos a obligar al Bot a crear uno nuevo y a darte poderes a ti.")
    
    mi_correo = st.text_input("Ingresa TU CORREO de Gmail (al que quieres que el bot le mande el archivo):")
    
    if st.button("🚨 CREAR NUEVO EXCEL AUTOMÁTICO", type="primary"):
        if not mi_correo:
            st.error("Por favor, ingresa tu correo.")
        else:
            client = init_connection()
            if not client:
                st.error("No se pudo iniciar sesión con Google. Revisa tus Secrets de Streamlit.")
            else:
                try:
                    with st.spinner("El robot está fabricando el Excel en los servidores de Google..."):
                        # El bot crea el archivo
                        new_doc = client.create('AWAKE SUPPS POS - BASE DE DATOS')
                        # El bot crea las pestañas
                        new_doc.sheet1.update_title('Inventario')
                        new_doc.add_worksheet(title="Ventas", rows=1000, cols=20)
                        
                        # Pone los encabezados
                        ws_inv = new_doc.worksheet("Inventario")
                        ws_inv.append_row(["ID Producto", "Nombre del Producto", "Categoría", "Precio Unitario", "Stock Disponible"])
                        
                        ws_ven = new_doc.worksheet("Ventas")
                        ws_ven.append_row(["Fecha", "Factura", "Cédula", "Cliente", "Canal", "Productos", "Total", "Método de Pago", "Estado"])
                        
                        # El bot TE INVITA A TI
                        new_doc.share(mi_correo, perm_type='user', role='writer')
                        
                    st.success("✅ ¡BASE DE DATOS CREADA Y COMPARTIDA CON ÉXITO!")
                    st.info(f"**NUEVO ID DEL EXCEL (Cópialo):** `{new_doc.id}`")
                    st.markdown(f"[➡️ HAZ CLIC AQUÍ PARA ABRIR TU NUEVO EXCEL O VE A TU BANDEJA DE CORREO]({new_doc.url})")
                    st.write("Copia el Nuevo ID, ponlo en tu variable `SHEET_ID` del código en la línea 48, y tu sistema funcionará al 100%.")
                    st.balloons()
                except Exception as e:
                    st.error("CRÍTICO: Google no nos dejó crear el archivo. Esto significa 100% que las APIS 'Sheets' y 'Drive' siguen APAGADAS en Google Cloud Platform o la cuenta de servicio está bloqueada.")
                    st.code(e)

# ==========================================
# MÓDULO 1: PUNTO DE VENTA (POS)
# ==========================================
elif menu == "💻 Punto de Venta (POS)":
    # (El resto del código normal)
    st.title("🛒 Punto de Venta - AWAKE SUPPS")
    st.info("Ve a la opción 'MODO RESCATE' en el menú de la izquierda para arreglar tu sistema.")

# ==========================================
# MÓDULO 2: CARGA DE MERCANCÍA
# ==========================================
elif menu == "📦 Carga de Mercancía":
    st.title("📦 Carga de Mercancía - Inventario")
    st.info("Ve a la opción 'MODO RESCATE' en el menú de la izquierda para arreglar tu sistema.")
