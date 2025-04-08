import streamlit as st
from streamlit_signature_pad import st_signature_pad
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import smtplib
from email.message import EmailMessage
import io
import os
import json
from pathlib import Path
import base64

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
        <li>🧹 Borra si necesitas rehacerla (botón de la propia herramienta).</li>
        <li>🧍 Introduce tu nombre completo.</li>
        <li>📬 Pulsa <strong>Enviar</strong> para finalizar.</li>
    </ol>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# CONSTANTES Y ESTADOS INICIALES
PDF_ORIGINAL = "documento.pdf"                # El PDF fijo que subiste al repo
DESTINATARIO = "quierovertodo20@gmail.com"    # A quién se envía el PDF firmado
REGISTRO_FIRMAS = Path("firmas_registradas.json")

#  (Para verificar si ya firmó)
def cargar_firmas_registradas():
    if REGISTRO_FIRMAS.exists():
        with open(REGISTRO_FIRMAS, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def guardar_firma(nombre):
    """Agrega el 'nombre' a la lista de firmantes en JSON."""
    firmas = cargar_firmas_registradas()
    firmas.append(nombre.strip().lower())
    with open(REGISTRO_FIRMAS, "w", encoding="utf-8") as f:
        json.dump(firmas, f, indent=2)

# ---------------------------------------------------------------------------
# FUNCIÓN: MOSTRAR PDF ORIGINAL
def mostrar_pdf_original(nombre_pdf):
    """Permite descargar el PDF original y retorna sus bytes."""
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
# FUNCIÓN: SUPERPONER FIRMA EN EL PDF
def firmar_pdf(pdf_bytes, signature_data_url, nombre_apellidos, x=50, y=50, pagina=0):
    """
    - Convierte la firma (base64 en signature_data_url) a bytes PNG.
    - Superpone en la página 'pagina' del PDF (pdf_bytes).
    - Agrega también un texto "Firmado por: <nombre_apellidos>" debajo de la firma.
    - Devuelve el PDF firmado en bytes.
    """
    # 1) Cargar PDF en memoria
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()

    # 2) Convertir firma base64 (signature_data_url) a bytes
    # streamlit-signature-pad retorna un string como 'data:image/png;base64,iVBORw0KGgo...'
    if not signature_data_url or not signature_data_url.startswith("data:image/png;base64,"):
        return None

    encoded = signature_data_url.split(",")[1]
    firma_png_bytes = base64.b64decode(encoded)

    # 3) Crear overlay con reportlab
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    firma_image = ImageReader(io.BytesIO(firma_png_bytes))

    # Dibuja la firma ~100px ancho
    c.drawImage(firma_image, x, y, width=100, preserveAspectRatio=True, mask='auto')
    c.setFont("Helvetica", 10)
    c.drawString(x, y - 15, f"Firmado por: {nombre_apellidos}")
    c.save()
    packet.seek(0)

    overlay_pdf = PdfReader(packet)

    # 4) Fusionar en la página 'pagina'
    for i, page in enumerate(reader.pages):
        if i == pagina:
            page.merge_page(overlay_pdf.pages[0])
        writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()

# ---------------------------------------------------------------------------
# FUNCIÓN: ENVIAR CORREO
def enviar_correo(pdf_bytes, nombre_apellidos):
    """
    Envía el 'pdf_bytes' como adjunto al correo DESTINATARIO
    usando credenciales en st.secrets["smtp"].
    """
    try:
        smtp_host = st.secrets["smtp"]["host"]
        smtp_port = int(st.secrets["smtp"]["port"])
        smtp_user = st.secrets["smtp"]["user"]
        smtp_pass = st.secrets["smtp"]["pass"]  # Asegúrate que en secrets TOML también sea 'pass'

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
# LÓGICA PRINCIPAL DE LA PÁGINA
st.divider()

# 1) Muestra PDF original y lo retorna en bytes
pdf_original_bytes = mostrar_pdf_original(PDF_ORIGINAL)

# 2) Captura la firma con streamlit-signature-pad
st.write("## ✍️ Firma aquí abajo:")
signature_data = st_signature_pad(
    stroke_width=2,    # grosor del trazo
    bg_color="#FFFFFF",
    pen_color="#000000",
    height=200,
    key="signature_pad"
)
# signature_data es un string base64 tipo "data:image/png;base64,iVBOR..."
# Si el usuario no ha dibujado nada, puede estar vacío ("") o None.

# 3) Nombre y apellidos
st.subheader("🧍 Nombre y apellidos")
nombre_apellidos = st.text_input("Introduce tu nombre completo")

st.divider()

# 4) Botón para enviar
if st.button("📬 Enviar Documento Firmado"):
    # Verificamos firma y nombre
    if not signature_data or len(signature_data) < 50:
        st.error("❌ Debes dibujar tu firma antes de enviar.")
    elif not nombre_apellidos.strip():
        st.error("❌ Por favor, introduce tu nombre y apellidos.")
    else:
        # Chequeamos si ya firmó antes
        nombre_normalizado = nombre_apellidos.strip().lower()
        firmas_previas = cargar_firmas_registradas()
        if nombre_normalizado in firmas_previas:
            st.error("⚠️ Ya has enviado este documento. Solo puedes hacerlo una vez.")
        else:
            with st.spinner("Generando y enviando el documento firmado..."):
                pdf_firmado = firmar_pdf(pdf_original_bytes, signature_data, nombre_apellidos)
                if not pdf_firmado:
                    st.error("No se pudo generar el PDF firmado. ¿Firmaste correctamente?")
                else:
                    enviar_correo(pdf_firmado, nombre_apellidos)
                    # Guardamos el nombre para no duplicar
                    guardar_firma(nombre_apellidos)
                    st.success("✅ Proceso completado. ¡Gracias por tu firma!")
