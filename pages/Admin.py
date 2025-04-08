import streamlit as st
import json
from pathlib import Path

# Configuración
st.set_page_config(page_title="🛡️ Admin - Firmas de Caza", layout="centered")
st.title("🛡️ Panel de Administración")

# Estilo personalizado
st.markdown("""
<style>
    .firma-card {
        border: 1px solid rgba(255,255,255,0.15);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        background-color: rgba(255,255,255,0.05);
    }
    .firma-header {
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Ruta del archivo JSON
REGISTRO_FIRMAS = Path("../firmas_registradas.json")

# Credenciales
admin_user = st.secrets["admin"]["username"]
admin_pass = st.secrets["admin"]["password"]

# Login
usuario = st.text_input("👤 Usuario")
clave = st.text_input("🔑 Contraseña", type="password")

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
    st.markdown(f"### 📋 Total de firmas registradas: {len(firmas)}")

    if not firmas:
        st.info("No hay firmas registradas aún.")
    else:
        for i, nombre in enumerate(firmas):
            with st.container():
                st.markdown(f"<div class='firma-card'><div class='firma-header'>✍️ Firma #{i+1}</div>", unsafe_allow_html=True)
                nuevo_nombre = st.text_input("🧍 Nombre completo", value=nombre, key=f"edit_{i}")
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("💾 Guardar", key=f"save_{i}"):
                        firmas[i] = nuevo_nombre.strip().lower()
                        guardar_firmas(firmas)
                        st.success("✅ Guardado correctamente.")
                        st.rerun()
                with col2:
                    if st.button("🗑️ Eliminar", key=f"del_{i}"):
                        del firmas[i]
                        guardar_firmas(firmas)
                        st.warning("❌ Registro eliminado.")
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)  # Cierra la tarjeta

    st.markdown("---")
    if st.button("🔄 Recargar lista"):
        st.rerun()

else:
    st.warning("🔒 Acceso restringido. Introduce tus credenciales.")
