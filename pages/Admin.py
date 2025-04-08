import streamlit as st
import json
from pathlib import Path

# Configuración
st.set_page_config(page_title="🛡️ Admin - Firmas de Caza", layout="centered")
st.title("🛡️ Panel de Administración - Firmas Registradas")

# Ruta del archivo JSON
REGISTRO_FIRMAS = Path("../firmas_registradas.json")

# Credenciales
admin_user = st.secrets["admin"]["username"]
admin_pass = st.secrets["admin"]["password"]

# Login
usuario = st.text_input("👤 Usuario")
clave = st.text_input("🔑 Contraseña", type="password")

# Funciones
def cargar_firmas():
    if REGISTRO_FIRMAS.exists():
        with open(REGISTRO_FIRMAS, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def guardar_firmas(firmas):
    with open(REGISTRO_FIRMAS, "w", encoding="utf-8") as f:
        json.dump(firmas, f, indent=2)

# Lógica de acceso
if usuario == admin_user and clave == admin_pass:
    st.success("🔓 Acceso concedido")

    firmas = cargar_firmas()
    st.markdown(f"### 📋 Total de firmas: {len(firmas)}")
    st.markdown("---")

    if not firmas:
        st.info("Aún no hay firmas registradas.")
    else:
        # Tabla con columnas: contador, nombre, eliminar
        col_num, col_nombre, col_accion = st.columns([1, 6, 2])
        col_num.markdown("**#**")
        col_nombre.markdown("**🧍 Nombre**")
        col_accion.markdown("**🗑️ Eliminar**")

        for i, nombre in enumerate(firmas):
            col_num, col_nombre, col_accion = st.columns([1, 6, 2])
            col_num.write(i + 1)
            col_nombre.write(nombre)
            if col_accion.button("Eliminar", key=f"del_{i}"):
                del firmas[i]
                guardar_firmas(firmas)
                st.warning(f"❌ Registro '{nombre}' eliminado.")
                st.rerun()
else:
    st.warning("🔒 Acceso restringido. Introduce tus credenciales.")
