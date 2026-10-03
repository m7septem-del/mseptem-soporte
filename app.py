import streamlit as st
import time
import os
import requests
import matplotlib.pyplot as plt
import psycopg2
from psycopg2.extras import RealDictCursor

# Configuración de la página premium estilo MSEPTEM
st.set_page_config(page_title="Sistema de Soporte Técnico", page_icon="🛠️", layout="wide")

# Inyección estricta de CSS para forzar el tema Obsidian & Gold corporativo
st.markdown("""
    <style>
        .stApp { background-color: #0D0D0D; }
        div[data-testid="stForm"], .stAlert {
            background-color: #1A1A1A !important;
            border: 1px solid #D4AF37 !important;
            border-radius: 12px !important;
        }
        h1, h2, h3, p, label, span { color: #FFFFFF !important; font-family: 'Courier New', monospace !important; }
        h1, h2 { color: #D4AF37 !important; }
        div[data-testid="stMetricValue"] { color: #D4AF37 !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("🛠️ Panel de Control - Soporte Técnico")
st.subheader("Gestión de Tickets y Enlace de Datos en Vivo con la App GEMINIS7 (Neon DB)")

# --- 🔌 CONEXIÓN CON NEON POSTGRESQL ---
def obtener_conexion():
    try:
        conn_str = st.secrets["postgres"]["connection_string"]
        conn = psycopg2.connect(conn_str)
        return conn
    except Exception as e:
        st.error(f"❌ Error al conectar con la base de datos Neon: {e}")
        return None

def inicializar_base_datos():
    conn = obtener_conexion()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tickets_sistema (
                        id TEXT PRIMARY KEY,
                        cliente TEXT NOT NULL,
                        asunto TEXT NOT NULL,
                        mensaje TEXT NOT NULL,
                        estado TEXT NOT NULL
                    );
                """)
                conn.commit()
        except Exception as e:
            st.error(f"Error al inicializar la tabla: {e}")
        finally:
            conn.close()

# Inicializar la tabla en Neon al arrancar
inicializar_base_datos()

# --- FUNCIONES DE BASE DE DATOS (NEON) ---
def cargar_datos_permanentes():
    conn = obtener_conexion()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id, cliente, asunto, mensaje, estado FROM tickets_sistema ORDER BY id DESC;")
            return cursor.fetchall()
    except Exception as e:
        st.error(f"Error al cargar tickets: {e}")
        return []
    finally:
        conn.close()

def guardar_ticket_bd(nuevo_ticket):
    conn = obtener_conexion()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO tickets_sistema (id, cliente, asunto, mensaje, estado) VALUES (%s, %s, %s, %s, %s);",
                    (nuevo_ticket['id'], nuevo_ticket['cliente'], nuevo_ticket['asunto'], nuevo_ticket['mensaje'], nuevo_ticket['estado'])
                )
                conn.commit()
        except Exception as e:
            st.error(f"Error al guardar ticket: {e}")
        finally:
            conn.close()

def actualizar_estado_bd(ticket_id, nuevo_estado):
    conn = obtener_conexion()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE tickets_sistema SET estado = %s WHERE id = %s;",
                    (nuevo_estado, ticket_id)
                )
                conn.commit()
        except Exception as e:
            st.error(f"Error al actualizar estado: {e}")
        finally:
            conn.close()

def eliminar_ticket_bd(ticket_id):
    conn = obtener_conexion()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM tickets_sistema WHERE id = %s;", (ticket_id,))
                conn.commit()
        except Exception as e:
            st.error(f"Error al eliminar ticket: {e}")
        finally:
            conn.close()

# Sincronizar datos actuales de la sesión con Neon
st.session_state['tickets_sistema'] = cargar_datos_permanentes()

# --- BARRA LATERAL ---
st.sidebar.header("🔄 Servidor en la Nube")
if st.sidebar.button("📥 Actualizar Datos", use_container_width=True):
    st.session_state['tickets_sistema'] = cargar_datos_permanentes()
    st.rerun()

st.sidebar.divider()
st.sidebar.header("🔍 Herramientas de Búsqueda")
busqueda = st.sidebar.text_input("Buscar por correo o asunto:", placeholder="Ej. AES...")
filtro = st.sidebar.selectbox("Filtrar por estado:", ["Todos", "🔴 Abierto", "🟡 En Proceso", "🟢 Resuelto"])

st.sidebar.divider()
st.sidebar.header("➕ Registrar Caso Manual")
with st.sidebar.form(key="formulario_ticket", clear_on_submit=True):
    nuevo_cliente = st.text_input("Correo del usuario afectado:", placeholder="usuario@correo.com")
    nuevo_asunto = st.text_input("Asunto / Problema:")
    nuevo_mensaje = st.text_area("Detalle de la falla:")
    boton_guardar = st.form_submit_button("💾 Guardar Ticket")
    
    if boton_guardar:
        if nuevo_cliente.strip() != "" and nuevo_asunto.strip() != "" and nuevo_mensaje.strip() != "":
            nuevo_id = str(int(time.time()))
            nuevo_ticket = { "id": nuevo_id, "cliente": nuevo_cliente, "asunto": nuevo_asunto, "mensaje": nuevo_mensaje, "estado": "🔴 Abierto" }
            
            guardar_ticket_bd(nuevo_ticket)
            st.sidebar.success("¡Ticket guardado en Neon!")
            time.sleep(0.5)
            st.rerun()

# Procesar filtros y búsqueda
tickets_filtrados = st.session_state['tickets_sistema']
if filtro != "Todos":
    tickets_filtrados = [t for t in tickets_filtrados if t['estado'] == filtro]
if busqueda.strip() != "":
    termino = busqueda.lower()
    tickets_filtrados = [t for t in tickets_filtrados if termino in t['cliente'].lower() or termino in t['asunto'].lower() or termino in t['mensaje'].lower()]

# --- DICCIONARIO DE PLANTILLAS ---
PLANTILLAS = {
    "Selecciona una plantilla...": "",
    "💬 Reporte Recibido de GEMINIS7": "Hola. Hemos recibido tu reporte técnico sobre la plataforma de mensajería. Nuestro equipo de ciberseguridad ya está analizando la traza en la base de datos para solucionar la incidencia en tu terminal a la brevedad.",
    "🔑 Error de Claves AES / Descifrado": "Hola. Si el sistema te arroja un aviso de 'Mensaje Corrupto', se debe a que la frase secreta de la sala de chat no coincide con la de tu contacto. Por favor solicítale que regenere la llave de invitación QR en sus ajustes.",
    "🌋 Fallas en Alerta de Sismo": "Hola. La Alerta Sísmica se alimenta del canal digital automatizado. Si experimentas retrasos, por favor ve a los ajustes de tu teléfono y asegúrate de que GEMINIS7 disponga de permisos para ejecutarse en segundo plano."
}

# --- 📥 SECCIÓN SUPERIOR: PANEL DE OPERACIONES ---
col1, col2 = st.columns(2)

with col1:
    st.header("📥 Lista de Tickets")
    if not tickets_filtrados:
        st.info("No se encontraron tickets con los criterios actuales.")
    
    for ticket in tickets_filtrados:
        texto_boton = f"{ticket['estado']} | {ticket['asunto'][:25]}..."
        if st.button(texto_boton, key=f"btn_{ticket['id']}", use_container_width=True):
            st.session_state['ticket_activo_id'] = ticket['id']

with col2:
    st.header("📝 Detalle y Gestión del Caso")
    t_activo = None
    if 'ticket_activo_id' in st.session_state:
        for t in st.session_state['tickets_sistema']:
            if t['id'] == st.session_state['ticket_activo_id']:
                t_activo = t
                break

    if t_activo:
        c_info, c_borrar = st.columns(2)
        with c_info:
            st.markdown(f"**De:** {t_activo['cliente']}")
            st.markdown(f"**Asunto:** {t_activo['asunto']}")
            st.markdown(f"**Estado Actual:** {t_activo['estado']}")
        with c_borrar:
            if st.button("🗑️️ Eliminar Ticket", type="secondary", use_container_width=True):
                eliminar_ticket_bd(t_activo['id'])
                if 'ticket_activo_id' in st.session_state:
                    del st.session_state['ticket_activo_id']
                st.toast("Ticket eliminado de Neon")
                time.sleep(0.5)
                st.rerun()

        st.text_area("Mensaje reportado:", value=t_activo['mensaje'], height=100, disabled=True)
        
        st.subheader("⚙️ Cambiar Estado")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🔴 Abierto", key="st_abierto", use_container_width=True):
                actualizar_estado_bd(t_activo['id'], "🔴 Abierto")
                st.rerun()
        with c2:
            if st.button("🟡 En Proceso", key="st_proceso", use_container_width=True):
                actualizar_estado_bd(t_activo['id'], "🟡 En Proceso")
                st.rerun()
        with c3:
            if st.button("🟢 Resuelto", key="st_resuelto", use_container_width=True):
                actualizar_estado_bd(t_activo['id'], "🟢 Resuelto")
                st.rerun()
        
        st.divider()
        st.subheader("✍️ Responder al Usuario")
        plantilla_elegida = st.selectbox("⚡ Respuestas rápidas:", list(PLANTILLAS.keys()))
        respuesta = st.text_area("Escribe la solución aquí:", value=PLANTILLAS[plantilla_elegida], height=100)
        
        if st.button("🚀 Enviar Respuesta", type="primary", use_container_width=True):
            if respuesta.strip() != "":
                st.success(f"¡Respuesta guardada con éxito para {t_activo['cliente']}!")
                actualizar_estado_bd(t_activo['id'], "🟢 Resuelto")
                time.sleep(0.5)
                st.rerun()
            else:
                st.warning("Escribe un mensaje antes de presionar enviar.")
    else:
        st.info("Selecciona un caso de la lista para gestionarlo.")

# --- 📊 SECCIÓN INFERIOR: RENDIMIENTO Y GRÁFICO ---
st.markdown("---")
st.header("📊 Resumen y Rendimiento de Casos")

tickets_actuales = cargar_datos_permanentes()
total_tickets = len(tickets_actuales)
abiertos = sum(1 for t in tickets_actuales if "Abierto" in t['estado'])
proceso = sum(1 for t in tickets_actuales if "Proceso" in t['estado'])
resueltos = sum(1 for t in tickets_actuales if "Resuelto" in t['estado'])

m1, m2, m3, m4 = st.columns(4)
m1.metric("📋 Total Casos", total_tickets)
m2.metric("🔴 Abiertos", abiertos)
m3.metric("🟡 En Proceso", proceso)
m4.metric("🟢 Resueltos", resueltos)

if total_tickets > 0:
    fig, ax = plt.subplots(figsize=(4, 2))
    fig.patch.set_facecolor('#00000000') # Transparente para acoplarse a Streamlit
    labels = ['Abiertos', 'En Proceso', 'Resueltos']
    sizes = [abiertos, proceso, resueltos]
    colors = ['#FF1A1A', '#FFD400', '#00CC44']
    
    filtered_labels = [l for i, l in enumerate(labels) if sizes[i] > 0]
    filtered_sizes = [s for s in sizes if s > 0]
    filtered_colors = [c for i, c in enumerate(colors) if sizes[i] > 0]
    
    if filtered_sizes:
        ax.pie(filtered_sizes, labels=filtered_labels, colors=filtered_colors, autopct='%1.1f%%', textprops={'color':"white", 'fontsize':8})
        ax.axis('equal')
        st.pyplot(fig)
