import streamlit as st
import json
from pathlib import Path

REGISTRO_FIRMAS = Path("firmas_registradas.json")

# --- Cargar credenciales ---
admin_user = st.secrets["admin"]["username"]
admin_pass = st.secrets["admin"]["password"]

# --- Login básico ---
st.set_page_config(page_title="🛡️ Admin - Firmas de Caza")
st.title("🛡️ Panel de Administración - Firmas Recibidas")

usuario = st.text_input("Usuario")
clave = st.text_input("Contraseña", type="password")

if usuario == admin_user and clave == admin_pass:
    st.success("🔓 Acceso concedido")

    def cargar_firmas():
        if REGISTRO_FIRMAS.exists():
            with open(REGISTRO_FIRMAS, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def guardar_firmas(firmas):
        with open(REGISTRO_FIRMAS, "w", encoding="utf-8") as f:
            json.dump(firmas, f, indent=2)

    firmas = cargar_firmas()
    st.write(f"📋 Total firmas registradas: **{len(firmas)}**")

    for i, nombre in enumerate(firmas):
        col1, col2, col3 = st.columns([3, 3, 1])
        with col1:
            nuevo_nombre = st.text_input(f"Nombre {i+1}", value=nombre, key=f"edit_{i}")
        with col2:
            if st.button("💾 Guardar", key=f"save_{i}"):
                firmas[i] = nuevo_nombre.strip().lower()
                guardar_firmas(firmas)
                st.success("Guardado correctamente.")
                st.experimental_rerun()
        with col3:
            if st.button("🗑️ Eliminar", key=f"del_{i}"):
                del firmas[i]
                guardar_firmas(firmas)
                st.warning("Registro eliminado.")
                st.experimental_rerun()

    if st.button("🔄 Recargar lista"):
        st.experimental_rerun()

else:
    st.warning("🔒 Acceso restringido. Introduce tus credenciales.")
