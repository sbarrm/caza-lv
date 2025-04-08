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

# ---------------------------------------------------------------------------
# CONFIGURACIÓN DE LA APP
st.set_page_config(page_title="Firma Digital - Documento de Caza", layout="centered")
st.title("🦌 Firma Digital del Documento de Caza")

st.markdown("""
Bienvenido, cazador. Por favor, sigue los pasos para firmar tu documento:

1. Descarga y revisa el documento de caza.
2. Introduce tu nombre completo.
3. Dibuja tu firma en el recuadro.
4. Haz clic en **Enviar** para completar el proceso.
""")

# ---------------------------------------------------------------------------
# CONSTANTES
PDF_ORIGINAL = "documento.pdf"
DESTINATARIO = "quierovertodo20@gmail.com"

# ---------------------------------------------------------------------------
# FUNCIÓN: MOSTRAR PDF ORIGINAL
def mostrar_pdf_original(nombre_pdf):
    if not os.path.exists(nombre_pdf):
        st.error(f"No se encontró el archivo '{nombre_pdf}'. Verifica que esté en el repositorio.")
        st.stop()

    with open(nombre_pdf, "rb") as f:
        pdf_bytes = f.read()

    st.download_button(
        label="📄 Descargar Documento de Caza",
        data=pdf_bytes,
        file_name="documento_caza_original.pdf",
        mime="application/pdf"
    )
    return pdf_bytes

# ---------------------------------------------------------------------------
# FUNCIÓN: CAPTURAR FIRMA EN LIENZO
def capturar_firma():
    st.subheader("✍️ Firma aquí abajo")
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 1)",
        stroke_width=2,
        stroke_color="#000000",
        background_color="#FFFFFF",
        width=400,
        height=200,
        drawing_mode="freedraw",
        key="canvas_firma"
    )

    if canvas_result.image_data is not None:
        firma_pil = Image.fromarray(canvas_result.image_data.astype(np.uint8))
        buffer = io.BytesIO()
        firma_pil.save(buffer, format="PNG")
        return buffer.getvalue()
    return None

# ---------------------------------------------------------------------------
# FUNCIÓN: AÑADIR FIRMA AL PDF
def firmar_pdf(pdf_bytes, firma_bytes, nombre_apellidos, x=50, y=50, pagina=0):
    lector = PdfReader(io.BytesIO(pdf_bytes))
    escritor = PdfWriter()

    lienzo = io.BytesIO()
    c = canvas.Canvas(lienzo, pagesize=letter)

    # Añadir imagen de la firma
    imagen_firma = ImageReader(io.BytesIO(firma_bytes))
    c.drawImage(imagen_firma, x, y, width=100, preserveAspectRatio=True, mask='auto')

    # Añadir texto con nombre debajo de la firma
    c.setFont("Helvetica", 10)
    c.drawString(x, y - 15, f"Firmado por: {nombre_apellidos}")

    c.save()
    lienzo.seek(0)

    overlay = PdfReader(lienzo)

    for i, pagina_pdf in enumerate(lector.pages):
        if i == pagina:
            pagina_pdf.merge_page(overlay.pages[0])
        escritor.add_page(pagina_pdf)

    resultado = io.BytesIO()
    escritor.write(resultado)
    return resultado.getvalue()

# ---------------------------------------------------------------------------
# FUNCIÓN: ENVIAR EMAIL
def enviar_correo(pdf_bytes):
    try:
        smtp_host = st.secrets["smtp"]["host"]
        smtp_port = int(st.secrets["smtp"]["port"])
        smtp_user = st.secrets["smtp"]["user"]
        smtp_pass = st.secrets["smtp"]["pass"]

        msg = EmailMessage()
        msg["Subject"] = "Documento de Caza Firmado"
        msg["From"] = f"Firma Digital <{smtp_user}>"
        msg["To"] = DESTINATARIO
        msg.set_content("Adjunto el documento de caza debidamente firmado.")

        msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename="documento_caza_firmado.pdf")

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

# Mostrar PDF y capturar firma
pdf_original_bytes = mostrar_pdf_original(PDF_ORIGINAL)
firma_bytes = capturar_firma()

# Campo obligatorio de nombre y apellidos
st.subheader("🧍 Nombre y Apellidos")
nombre_apellidos = st.text_input("Introduce tu nombre completo")

st.divider()

# Botón de envío con validaciones
if st.button("📬 Enviar Documento Firmado"):
    if not firma_bytes:
        st.error("❌ Debes dibujar tu firma antes de enviar.")
    elif not nombre_apellidos.strip():
        st.error("❌ Por favor, introduce tu nombre y apellidos.")
    else:
        with st.spinner("Generando y enviando el documento firmado..."):
            pdf_firmado = firmar_pdf(pdf_original_bytes, firma_bytes, nombre_apellidos)
            enviar_correo(pdf_firmado)
