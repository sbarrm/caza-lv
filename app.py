import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import io
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from PIL import Image
import numpy as np
import smtplib
from email.message import EmailMessage

# ---------------------------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Firma PDF", layout="centered")
st.title("Firma de PDF")

"""
### Visualiza y firma el siguiente documento.
1. Revisa el PDF (puedes descargarlo si quieres).
2. Dibuja tu firma en el recuadro.
3. Haz clic en "Enviar" para que se envíe el PDF firmado a **quierovertodo20@gmail.com**.
"""

# ---------------------------------------------------------------------------
# 1) MOSTRAR Y/O PERMITIR DESCARGAR EL PDF FIJO
PDF_FILENAME = "documento.pdf"  # El archivo que subiste al repo

# Verificamos que existe en la carpeta
if not os.path.exists(PDF_FILENAME):
    st.error(f"No se encontró el archivo '{PDF_FILENAME}'. Sube el PDF al repositorio.")
    st.stop()

with open(PDF_FILENAME, "rb") as f:
    pdf_bytes = f.read()

st.download_button(
    label="Descargar el PDF original",
    data=pdf_bytes,
    file_name="documento_original.pdf",
    mime="application/pdf"
)

# ---------------------------------------------------------------------------
# 2) CAPTURAR FIRMA CON UN LIENZO
st.write("## Dibuja tu firma")
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

firma_img = None
if canvas_result.image_data is not None:
    # Convertimos la imagen del canvas a formato PNG en memoria
    firma_pil = Image.fromarray((canvas_result.image_data).astype(np.uint8))
    firma_buffer = io.BytesIO()
    firma_pil.save(firma_buffer, format="PNG")
    firma_buffer.seek(0)
    firma_img = firma_buffer.read()

# ---------------------------------------------------------------------------
# 3) FUNCIÓN PARA SUPERPONER LA FIRMA EN EL PDF
def add_signature_to_pdf(pdf_raw_bytes, firma_png_bytes, x=50, y=50, page_num=0):
    """
    Superpone la imagen de la firma (firma_png_bytes) en la página `page_num`
    del PDF (pdf_raw_bytes). Devuelve los bytes del PDF firmado.
    """
    pdf_reader = PdfReader(io.BytesIO(pdf_raw_bytes))
    pdf_writer = PdfWriter()

    # Creamos un PDF temporal con la firma usando reportlab
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    firma_image = ImageReader(io.BytesIO(firma_png_bytes))
    # Dibuja la firma con ancho ~100 px (ajusta a tu gusto)
    c.drawImage(firma_image, x, y, width=100, preserveAspectRatio=True, mask='auto')
    c.save()
    packet.seek(0)

    # Overlay con la firma
    overlay_pdf = PdfReader(packet)

    # Merge en la página correspondiente
    for i, page in enumerate(pdf_reader.pages):
        if i == page_num:
            page.merge_page(overlay_pdf.pages[0])
        pdf_writer.add_page(page)

    output_stream = io.BytesIO()
    pdf_writer.write(output_stream)
    return output_stream.getvalue()

# ---------------------------------------------------------------------------
# 4) BOTÓN PARA ENVIAR (FIRMAR Y MANDAR CORREO)
st.write("---")
enviar_btn = st.button("Enviar")

if enviar_btn:
    if firma_img is None:
        st.error("Por favor dibuja tu firma antes de enviar.")
    else:
        # Generar PDF con firma en la primera página
        pdf_firmado = add_signature_to_pdf(pdf_bytes, firma_img, x=50, y=50, page_num=0)

        # Mostramos un "spinner" mientras enviamos
        with st.spinner("Generando y enviando el PDF firmado..."):
            try:
                # Configura tus credenciales SMTP.
                # Si quieres no exponerlas en el código, guárdalas en st.secrets (ver más abajo).
                # Aquí un ejemplo con Mailjet (sin tarjeta).
                smtp_host = st.secrets["smtp"]["host"]    # p.ej. "in-v3.mailjet.com"
                smtp_port = int(st.secrets["smtp"]["port"])  # p.ej. 587
                smtp_user = st.secrets["smtp"]["user"]    # p.ej. "API_KEY"
                smtp_pass = st.secrets["smtp"]["pass"]    # p.ej. "API_SECRET"

                # Construimos el correo
                msg = EmailMessage()
                msg["Subject"] = "Documento firmado"
                msg["From"] = f"FirmaPDF <{smtp_user}>"   # Remitente
                msg["To"] = "quierovertodo20@gmail.com"   # Correo fijo solicitado
                msg.set_content("Hola,\n\nAdjunto el documento firmado.\n")

                # Adjuntar PDF
                msg.add_attachment(pdf_firmado, maintype="application", subtype="pdf",
                                  filename="documento_firmado.pdf")

                # Enviamos
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)

                st.success("¡PDF firmado enviado con éxito a quierovertodo20@gmail.com!")
            except Exception as e:
                st.error(f"Error al enviar el correo: {e}")
