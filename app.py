import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import json

# --- Configuración de Página ---
st.set_page_config(page_title="AWAKE SUPPS POS", page_icon="🛒", layout="wide")

# --- CSS Personalizado para Interfaz Pro ---
st.markdown("""
<style>
    .cart-header { font-size: 1.5rem; font-weight: 600; margin-bottom: 1rem; color: #1E3A8A; }
    .total-text { font-size: 2rem; font-weight: 700; color: #10B981; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    div[data-testid="stSidebarNav"] { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- Autenticación de Google Sheets ---
@st.cache_resource
def init_connection():
    try:
        # Los secretos deben estar configurados en st.secrets["gcp_service_account"]
        # o st.secrets["connections"]["gsheets"]
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
        else:
            st.warning("⚠️ No se encontraron las credenciales 'gcp_service_account' en st.secrets.")
            return None
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

# --- Variables Globales ---
SHEET_ID = st.secrets.get("spreadsheet_id", "TU_SPREADSHEET_ID_AQUI")

@st.cache_data(ttl=60)  # Cache duration for 60 seconds
def load_inventory():
    client = init_connection()
    if not client:
        return pd.DataFrame()
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet("Inventario")
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error al cargar el Inventario: {e}")
        return pd.DataFrame()

def save_sale(sale_record):
    client = init_connection()
    if not client:
        return False
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet("Ventas")
        # Ensure the record is a list of values
        sheet.append_row(list(sale_record.values()))
        return True
    except Exception as e:
        st.error(f"Error al guardar la venta: {e}")
        return False

def update_inventory(product_id, qty_to_subtract=0, mode="subtract", product_name="", category="", unit_price=0):
    client = init_connection()
    if not client:
        return False
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet("Inventario")
        records = sheet.get_all_records()
        
        # Buscar el producto
        row_index = None
        for i, rec in enumerate(records):
            if str(rec["ID Producto"]) == str(product_id):
                row_index = i + 2  # +2 because index starts at 0, header is row 1
                current_stock = int(rec["Stock Disponible"])
                break
        
        if row_index:
            if mode == "subtract":
                new_stock = current_stock - qty_to_subtract
                if new_stock < 0:
                    st.error(f"Stock insuficiente para {product_id}.")
                    return False
            elif mode == "add":
                new_stock = current_stock + qty_to_subtract
                
            # Actualizar la celda de stock (asumiendo que es la columna 5, E)
            sheet.update_cell(row_index, 5, new_stock)
        else:
            if mode == "add":
                # Agregar nuevo producto
                new_row = [product_id, product_name, category, unit_price, qty_to_subtract]
                sheet.append_row(new_row)
            else:
                st.error("Producto no encontrado en el inventario.")
                return False
        
        load_inventory.clear() # Limpiar cache gspread
        return True
    except Exception as e:
        st.error(f"Error al actualizar el Inventario: {e}")
        return False


# --- INICIALIZAR ESTADO DE SESIÓN ---
if "cart" not in st.session_state:
    st.session_state.cart = []

def add_to_cart(prod_id, prod_name, price, qty):
    # Check if already in cart
    for item in st.session_state.cart:
        if item["ID Producto"] == prod_id:
            item["Cantidad"] += qty
            item["Subtotal"] = item["Cantidad"] * price
            return
    
    st.session_state.cart.append({
        "ID Producto": prod_id,
        "Producto": prod_name,
        "Precio": price,
        "Cantidad": qty,
        "Subtotal": price * qty
    })

def remove_from_cart(index):
    st.session_state.cart.pop(index)

def clear_cart():
    st.session_state.cart = []


# --- MENÚ LATERAL ---
st.sidebar.image("https://via.placeholder.com/150x50.png?text=AWAKE+SUPPS", use_container_width=True)
st.sidebar.title("Menú Principal")
menu = st.sidebar.radio("Navegación", ["💻 Punto de Venta (POS)", "📦 Carga de Mercancía"], label_visibility="collapsed")

df_inventory = load_inventory()

# ==========================================
# MÓDULO 1: PUNTO DE VENTA (POS)
# ==========================================
if menu == "💻 Punto de Venta (POS)":
    st.title("🛒 Punto de Venta - AWAKE SUPPS")
    
    # 1. Información del Cliente
    with st.container():
        st.subheader("📋 Datos de Venta")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            factura = st.text_input("Número de Factura")
        with col2:
            cedula = st.text_input("Cédula del Cliente")
        with col3:
            cliente = st.text_input("Nombre del Cliente")
        with col4:
            canal = st.selectbox("Canal de Venta", ["WhatsApp", "WooCommerce", "Dropi", "MercadoLibre", "Tienda Física", "Instagram"])
    
    st.divider()

    # 2. Buscador y Selección de Productos
    if not df_inventory.empty:
        col_prod, col_qty, col_add = st.columns([5, 2, 2])
        
        # Crear opciones para el selectbox
        df_disponible = df_inventory[df_inventory["Stock Disponible"] > 0]
        opciones_productos = df_disponible.apply(lambda row: f"{row['ID Producto']} - {row['Nombre del Producto']} (${row['Precio Unitario']} | Stock: {row['Stock Disponible']})", axis=1).tolist()
        
        with col_prod:
            seleccion = st.selectbox("Buscar Producto", [""] + opciones_productos, index=0)
        
        with col_qty:
            cantidad = st.number_input("Cantidad", min_value=1, step=1, value=1)
            
        with col_add:
            st.markdown("<br>", unsafe_allow_html=True) # Espaciador
            if st.button("➕ Agregar", type="primary"):
                if seleccion:
                    # Extraer ID, nombre y precio
                    id_prod = seleccion.split(" - ")[0]
                    # Buscar la fila correspondiente
                    producto_info = df_inventory[df_inventory["ID Producto"].astype(str) == id_prod].iloc[0]
                    
                    if cantidad <= producto_info["Stock Disponible"]:
                        add_to_cart(id_prod, producto_info["Nombre del Producto"], producto_info["Precio Unitario"], cantidad)
                        st.success(f"Añadido {cantidad}x {producto_info['Nombre del Producto']}")
                    else:
                        st.error(f"Stock insuficiente. Solo quedan {producto_info['Stock Disponible']}.")
                else:
                    st.warning("Seleccione un producto primero.")
    else:
        st.warning("No se pudo cargar el inventario. Verifique la conexión a Google Sheets.")

    st.divider()

    # 3. Carrito de Compras
    st.markdown('<p class="cart-header">🛍️ Carrito Actual</p>', unsafe_allow_html=True)
    
    if st.session_state.cart:
        # Mostrar el carrito como df, o usando columnas simulando una tabla
        cart_df = pd.DataFrame(st.session_state.cart)
        
        for i, item in enumerate(st.session_state.cart):
            c1, c2, c3, c4, c5 = st.columns([1, 4, 2, 2, 1])
            c1.write(item["ID Producto"])
            c2.write(item["Producto"])
            c3.write(f"{item['Cantidad']} unid.")
            c4.write(f"${item['Subtotal']:,.0f}")
            with c5:
                if st.button("🗑️", key=f"del_{i}"):
                    remove_from_cart(i)
                    st.rerun()
                    
        total_venta = sum([item["Subtotal"] for item in st.session_state.cart])
        st.markdown(f'<p class="total-text" style="text-align: right;">Total: ${total_venta:,.0f}</p>', unsafe_allow_html=True)
        
        # 4. Proceso de Pago
        col_pay, col_status = st.columns(2)
        with col_pay:
            metodo_pago = st.selectbox("Método de Pago", ["Nequi", "Davivienda", "Bancolombia", "Efectivo", "Tarjeta de Crédito"])
        with col_status:
            estado = st.selectbox("Estado", ["Entregado", "Despachado", "Pendiente", "Devolución"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💳 FINALIZAR VENTA", type="primary", use_container_width=True):
            if not factura or not cedula or not cliente:
                st.error("Por favor complete los datos del cliente (Factura, Cédula, Cliente).")
            else:
                # 1. Validar y descontar stock
                success = True
                for item in st.session_state.cart:
                    if not update_inventory(item["ID Producto"], item["Cantidad"], mode="subtract"):
                        success = False
                        break
                
                if success:
                    # 2. Registrar venta
                    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    productos_json = json.dumps([{"id": c["ID Producto"], "qty": c["Cantidad"], "sub": c["Subtotal"]} for c in st.session_state.cart])
                    
                    sale_record = {
                        "Fecha": fecha_actual,
                        "Factura": factura,
                        "Cédula": cedula,
                        "Cliente": cliente,
                        "Canal": canal,
                        "Productos": productos_json,
                        "Total": float(total_venta),
                        "Método de Pago": metodo_pago,
                        "Estado": estado
                    }
                    
                    if save_sale(sale_record):
                        st.success("✅ ¡Venta registrada exitosamente!")
                        st.balloons()
                        clear_cart()
                        # st.rerun() # Refresh view
                    else:
                        st.error("Hubo un problema al guardar la venta en la hoja.")
    else:
        st.info("El carrito está vacío.")

# ==========================================
# MÓDULO 2: CARGA DE MERCANCÍA
# ==========================================
elif menu == "📦 Carga de Mercancía":
    st.title("📦 Carga de Mercancía - Inventario")
    st.write("Agrega unidades a productos existentes o crea nuevos productos en el catálogo.")

    with st.container():
        st.subheader("Añadir Stock")
        col1, col2 = st.columns(2)
        
        # Seleccionar si es un producto existente o nuevo
        tipo_ingreso = st.radio("Tipo de Ingreso", ["Producto Existente", "Nuevo Producto"], horizontal=True)
        
        if tipo_ingreso == "Producto Existente":
            if not df_inventory.empty:
                opciones = df_inventory.apply(lambda row: f"{row['ID Producto']} - {row['Nombre del Producto']} (Stock actual: {row['Stock Disponible']})", axis=1).tolist()
                prod_seleccionado = st.selectbox("Seleccionar Producto", [""] + opciones)
                qty_add = st.number_input("Cantidad a Ingresar", min_value=1, step=1, value=10)
                
                if st.button("Actualizar Stock", type="primary"):
                    if prod_seleccionado:
                        id_prod = prod_seleccionado.split(" - ")[0]
                        if update_inventory(id_prod, qty_add, mode="add"):
                            st.success(f"✅ Se agregaron {qty_add} unidades al producto {id_prod}.")
                    else:
                        st.warning("Seleccione un producto valid.")
            else:
                st.warning("Inventario no disponible.")
                
        else: # Nuevo Producto
            new_id = st.text_input("ID Producto (Código)")
            new_name = st.text_input("Nombre del Producto")
            new_cat = st.text_input("Categoría")
            new_price = st.number_input("Precio Unitario ($)", min_value=0.0, step=100.0)
            new_qty = st.number_input("Stock Inicial", min_value=0, step=1)
            
            if st.button("Crear y Añadir Producto", type="primary"):
                if new_id and new_name:
                    if update_inventory(new_id, new_qty, mode="add", product_name=new_name, category=new_cat, unit_price=new_price):
                         st.success(f"✅ Producto {new_name} creado con éxito con {new_qty} unidades.")
                else:
                    st.error("ID y Nombre son obligatorios.")

    st.divider()
    
    st.subheader("Estado Físico del Inventario")
    if not df_inventory.empty:
        st.dataframe(
            df_inventory.style.format({"Precio Unitario": "${:,.0f}"}),
            use_container_width=True,
            hide_index=True
        )
