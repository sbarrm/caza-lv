import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from PIL import Image
import numpy as np
import smtplib
from email.message import EmailMessage
import io
import os
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIGURACIÓN DE LA APP
st.set_page_config(page_title="🦌 Firma de Documento de caza", layout="centered")
st.markdown("<h1 style='text-align: center;'>🦌 Firma del documento de caza</h1>", unsafe_allow_html=True)

st.markdown("""
<style>
    .caja {
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.2);
        margin-bottom: 1.5rem;
    }
    ol {
        padding-left: 1.2rem;
    }
</style>

<div class='caja'>
    <p><strong>¡Bienvenido, cazador!</strong></p>
    <p>Completa los siguientes pasos para validar tu documento:</p>
    <ol>
        <li>📄 Descarga y revisa el documento de caza.</li>
        <li>✍️ Dibuja tu firma en el recuadro.</li>
        <li>🧹 Borra si necesitas rehacerla.</li>
        <li>🧍 Introduce tu nombre completo.</li>
        <li>📬 Pulsa <strong>Enviar</strong> para finalizar.</li>
    </ol>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# CONSTANTES Y ESTADOS INICIALES
PDF_ORIGINAL = "documento.pdf"                # Nombre del PDF que subiste al repo
DESTINATARIO = "quierovertodo20@gmail.com"    # Correo fijo al que se envía el PDF firmado
REGISTRO_FIRMAS = Path("firmas_registradas.json")

if "canvas_key" not in st.session_state:
    st.session_state["canvas_key"] = "firma_default"
if "firma_bytes" not in st.session_state:
    st.session_state["firma_bytes"] = None
if "firma_valida" not in st.session_state:
    st.session_state["firma_valida"] = False
if "firma_vacia" not in st.session_state:
    st.session_state["firma_vacia"] = None

# ---------------------------------------------------------------------------
# FUNCIONES PARA GUARDAR Y LEER JSON
def cargar_firmas_registradas():
    """
    Retorna la lista de nombres que ya firmaron (guardados en un JSON).
    """
    if REGISTRO_FIRMAS.exists():
        with open(REGISTRO_FIRMAS, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def guardar_firma(nombre):
    """
    Agrega el 'nombre' a la lista de firmantes registrados.
    """
    firmas = cargar_firmas_registradas()
    firmas.append(nombre.strip().lower())
    with open(REGISTRO_FIRMAS, "w", encoding="utf-8") as f:
        json.dump(firmas, f, indent=2)

# ---------------------------------------------------------------------------
# FUNCIÓN: MOSTRAR PDF ORIGINAL
def mostrar_pdf_original(nombre_pdf):
    """
    Descarga el PDF (el usuario puede revisarlo) y retorna sus bytes.
    """
    if not os.path.exists(nombre_pdf):
        st.error(f"❌ No se encontró el archivo '{nombre_pdf}'.")
        st.stop()
    with open(nombre_pdf, "rb") as f:
        pdf_bytes = f.read()

    st.download_button(
        "📥 Descargar Documento de Caza",
        data=pdf_bytes,
        file_name="documento_caza_original.pdf",
        mime="application/pdf"
    )
    return pdf_bytes

# ---------------------------------------------------------------------------
# FUNCIÓN: CAPTURAR FIRMA Y DETECTAR SI ESTÁ VACÍA
def capturar_firma():
    """
    Muestra un canvas para dibujar la firma.
    Detecta si la firma está vacía comparándola con la primera imagen capturada.
    """
    st.subheader("✍️ Firma aquí abajo")

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🧹 Borrar firma"):
            # Reiniciamos la clave del canvas y el estado
            st.session_state["canvas_key"] = str(np.random.rand())
            st.session_state["firma_bytes"] = None
            st.session_state["firma_valida"] = False
            st.session_state["firma_vacia"] = None

    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 1)",
        stroke_width=2,
        stroke_color="#000000",
        background_color="#FFFFFF",
        width=400,
        height=200,
        drawing_mode="freedraw",
        key=st.session_state["canvas_key"],
        display_toolbar=False
    )

    # Si el usuario dibuja algo, se actualiza image_data
    if canvas_result.image_data is not None:
        # Tomamos solo los 3 canales (RGB) y convertimos a uint8
        imagen_actual = (canvas_result.image_data[:, :, :3]).astype(np.uint8)

        # Si no hemos guardado la firma vacía, la guardamos
        if st.session_state["firma_vacia"] is None:
            st.session_state["firma_vacia"] = imagen_actual.copy()

        # Comparamos la imagen actual con la vacía
        es_valida = not np.array_equal(imagen_actual, st.session_state["firma_vacia"])

        if es_valida:
            # Convertimos la imagen a PNG en memoria
            firma_pil = Image.fromarray(imagen_actual)
            buffer = io.BytesIO()
            firma_pil.save(buffer, format="PNG")
            st.session_state["firma_bytes"] = buffer.getvalue()
            st.session_state["firma_valida"] = True
        else:
            # No hay firma real
            st.session_state["firma_bytes"] = None
            st.session_state["firma_valida"] = False

# ---------------------------------------------------------------------------
# FUNCIÓN: FIRMAR PDF (superponer firma + nombre)
def firmar_pdf(pdf_bytes, firma_bytes, nombre_apellidos, x=50, y=50, pagina=0):
    """
    Superpone la imagen de la firma (firma_bytes) en la página 'pagina' del PDF (pdf_bytes).
    Además, escribe el texto: "Firmado por: <nombre_apellidos>" justo debajo de la firma.
    """
    lector = PdfReader(io.BytesIO(pdf_bytes))
    escritor = PdfWriter()

    # Creamos un PDF temporal con la firma usando reportlab
    lienzo = io.BytesIO()
    c = canvas.Canvas(lienzo, pagesize=letter)

    # Cargamos la imagen de la firma
    imagen_firma = ImageReader(io.BytesIO(firma_bytes))

    # Dibuja la firma con ancho ~100 px
    c.drawImage(imagen_firma, x, y, width=100, preserveAspectRatio=True, mask='auto')
    c.setFont("Helvetica", 10)
    c.drawString(x, y - 15, f"Firmado por: {nombre_apellidos}")
    c.save()
    lienzo.seek(0)

    # Overlay
    overlay = PdfReader(lienzo)

    # Fusionamos en la página especificada
    for i, pagina_pdf in enumerate(lector.pages):
        if i == pagina:
            pagina_pdf.merge_page(overlay.pages[0])
        escritor.add_page(pagina_pdf)

    resultado = io.BytesIO()
    escritor.write(resultado)
    return resultado.getvalue()

# ---------------------------------------------------------------------------
# FUNCIÓN: ENVIAR EMAIL
def enviar_correo(pdf_bytes, nombre_apellidos):
    """
    Envía el 'pdf_bytes' como adjunto al correo DESTINATARIO,
    con un body que indica quién firmó.
    Las credenciales SMTP se obtienen de st.secrets["smtp"].
    """
    try:
        smtp_host = st.secrets["smtp"]["host"]
        smtp_port = int(st.secrets["smtp"]["port"])
        smtp_user = st.secrets["smtp"]["user"]
        smtp_pass = st.secrets["smtp"]["pass"]  # Asegúrate de que en secrets.toml esté "pass" o "password"

        msg = EmailMessage()
        msg["Subject"] = "Documento de Caza Firmado"
        msg["From"] = f"Firma Digital <{smtp_user}>"
        msg["To"] = DESTINATARIO
        msg.set_content(
            f"Hola,\n\nAdjunto el documento firmado por:\n👤 {nombre_apellidos}\n\nSaludos,\nSistema de Firma"
        )

        msg.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename="documento_caza_firmado.pdf"
        )

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        st.success(f"✅ Documento enviado con éxito a {DESTINATARIO}")
    except Exception as e:
        st.error(f"❌ Error al enviar el correo: {e}")

# ---------------------------------------------------------------------------
# FLUJO PRINCIPAL
st.divider()

# 1) Mostramos y permitimos descargar el PDF original
pdf_original_bytes = mostrar_pdf_original(PDF_ORIGINAL)

# 2) Capturamos la firma
capturar_firma()
firma_bytes = st.session_state.get("firma_bytes", None)
firma_valida = st.session_state.get("firma_valida", False)

# 3) Pedimos nombre y apellidos
st.subheader("🧍 Nombre y apellidos")
nombre_apellidos = st.text_input("Introduce tu nombre completo")

st.divider()

# 4) Botón para enviar (firma + correo)
if st.button("📬 Enviar Documento Firmado"):
    if not firma_valida:
        st.error("❌ Debes dibujar tu firma antes de enviar.")
    elif not nombre_apellidos.strip():
        st.error("❌ Por favor, introduce tu nombre y apellidos.")
    else:
        # Verificamos si el usuario ya firmó antes (para no duplicar)
        nombre_normalizado = nombre_apellidos.strip().lower()
        firmas_previas = cargar_firmas_registradas()
        if nombre_normalizado in firmas_previas:
            st.error("⚠️ Ya has enviado este documento. Solo puedes hacerlo una vez.")
        else:
            with st.spinner("Generando y enviando el documento firmado..."):
                pdf_firmado = firmar_pdf(pdf_original_bytes, firma_bytes, nombre_apellidos)
                enviar_correo(pdf_firmado, nombre_apellidos)
                guardar_firma(nombre_apellidos)
                st.success("✅ Proceso completado. ¡Gracias por tu firma!")
