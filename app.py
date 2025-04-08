import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import os
import io
import base64

###############################################################################
# OPCIONAL: Para enviar correos, podríamos usar 'smtplib' o 'yagmail', etc.
# Ejemplo con 'smtplib' y credenciales en st.secrets (Mailjet, etc.)
import smtplib
from email.message import EmailMessage

###############################################################################
# Configuración de la página de Streamlit
st.set_page_config(page_title="Firmar PDF con Streamlit", layout="centered")

st.title("Firmar PDF con Streamlit")

"""
Este demo te permite:
1. Subir un PDF.
2. Dibujar tu firma.
3. Descargar el PDF firmado o (opcional) enviarlo por correo.
"""

###############################################################################
# 1) Subir el PDF
pdf_file = st.file_uploader("Sube tu PDF", type=["pdf"])
if pdf_file is not None:
    pdf_bytes = pdf_file.read()  # Leemos todo el contenido en memoria
    st.success("PDF cargado correctamente.")
else:
    pdf_bytes = None

###############################################################################
# 2) Dibujar la firma en un lienzo
st.write("Dibuja tu firma en el recuadro (puedes usar el ratón o el dedo en una pantalla táctil).")

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

# El resultado de la firma vendrá en canvas_result.image_data como un array RGBA
# Si el usuario ha dibujado algo, lo convertimos a una imagen
firma_img = None
if canvas_result.image_data is not None:
    # Convertimos la imagen de NumPy array a bytes PNG
    import numpy as np
    from PIL import Image

    firma_pil = Image.fromarray((canvas_result.image_data).astype(np.uint8))
    # Para saber si está vacía o no, podríamos hacer más validaciones,
    # pero por simplicidad asumimos que si la persona dibujó algo, se considera firma.
    firma_buffer = io.BytesIO()
    firma_pil.save(firma_buffer, format="PNG")
    firma_buffer.seek(0)
    firma_img = firma_buffer.read()

###############################################################################
# 3) Botón para incrustar la firma y generar un PDF firmado
def add_signature_to_pdf(pdf_raw_bytes, firma_png_bytes, x=50, y=50, page_num=0):
    """
    Superpone la imagen de la firma en la página page_num del PDF.
    (x, y) es la coordenada inferior-izquierda donde se dibujará la firma.
    Devuelve bytes del PDF con la firma incrustada.
    """
    # 3.1) Leemos el PDF
    pdf_reader = PdfReader(io.BytesIO(pdf_raw_bytes))
    pdf_writer = PdfWriter()

    # 3.2) Creamos un PDF "temporal" con la firma usando reportlab
    packet = io.BytesIO()
    # Asumimos tamaño carta, pero idealmente deberías obtener el size real de la página
    c = canvas.Canvas(packet, pagesize=letter)

    # Cargamos la imagen de la firma con reportlab
    firma_image = ImageReader(io.BytesIO(firma_png_bytes))

    # Ejemplo: dibujamos la firma con ancho ~100 px, alto proporcional
    c.drawImage(firma_image, x, y, width=100, preserveAspectRatio=True, mask='auto')
    c.save()

    packet.seek(0)
    # 3.3) Fusionar la "capa de firma" en la página deseada
    overlay_pdf = PdfReader(packet)

    # Vamos página por página
    for i, page in enumerate(pdf_reader.pages):
        if i == page_num:
            # "merge_page" superpone el contenido de overlay_pdf en la página
            page.merge_page(overlay_pdf.pages[0])  # asumiendo 1 pag en overlay
        pdf_writer.add_page(page)

    # 3.4) Generar PDF final
    output_stream = io.BytesIO()
    pdf_writer.write(output_stream)
    return output_stream.getvalue()

col1, col2, col3 = st.columns(3)
with col2:
    generar_btn = st.button("Generar PDF firmado")

pdf_firmado_bytes = None

if generar_btn:
    if not pdf_bytes:
        st.error("Primero sube un PDF.")
    elif not firma_img:
        st.error("Por favor dibuja tu firma.")
    else:
        # Procesamos e incrustamos la firma
        pdf_firmado_bytes = add_signature_to_pdf(pdf_bytes, firma_img, x=50, y=50, page_num=0)
        st.success("Firma aplicada con éxito. Puedes descargar el PDF resultante abajo.")

###############################################################################
# 4) Mostrar botón de descarga
if pdf_firmado_bytes:
    st.download_button(
        label="Descargar PDF firmado",
        data=pdf_firmado_bytes,
        file_name="documento_firmado.pdf",
        mime="application/pdf"
    )

###############################################################################
# 5) (OPCIONAL) Enviar por correo
# Para que sea gratis y sin tarjeta, podrías usar credenciales de SMTP de 
# un servicio como Mailjet/Brevo sin exponerlas en código. 
#  - Ve a la Config de tu app en share.streamlit.io -> "Advanced settings" -> "Secrets"
#  - Define tus variables, ej:
#       [smtp]
#       host = "in-v3.mailjet.com"
#       port = "587"
#       user = "API_KEY"
#       password = "API_SECRET"
#  - En este ejemplo, las leemos con st.secrets["smtp"]["host"] etc.

st.write("---")
st.subheader("Enviar PDF firmado por correo (opcional)")

destinatario = st.text_input("Correo del destinatario", value="ejemplo@correo.com")

if st.button("Enviar PDF por correo"):
    if not pdf_firmado_bytes:
        st.error("Primero genera el PDF firmado.")
    else:
        try:
            # Ejemplo con smtplib
            host = st.secrets["smtp"]["host"]
            port = int(st.secrets["smtp"]["port"])
            user = st.secrets["smtp"]["user"]
            password = st.secrets["smtp"]["password"]

            msg = EmailMessage()
            msg["Subject"] = "Documento firmado"
            msg["From"] = f"FirmaPDF <{user}>"
            msg["To"] = destinatario
            msg.set_content("Hola,\n\nSe adjunta el documento firmado.\n")

            # Adjuntamos el PDF
            msg.add_attachment(pdf_firmado_bytes, maintype="application", subtype="pdf",
                              filename="documento_firmado.pdf")

            with smtplib.SMTP(host, port) as server:
                server.starttls()  # Asegura la conexión
                server.login(user, password)
                server.send_message(msg)

            st.success(f"Correo enviado correctamente a {destinatario}.")

        except Exception as e:
            st.error(f"Error al enviar correo: {e}")
