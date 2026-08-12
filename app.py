import streamlit as st
import cv2
import numpy as np
import matplotlib.pyplot as plt
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Configuración de página
st.set_page_config(page_title="EcoSarcopenia Pro", layout="centered")

st.title("🩺 Valoración Ecográfica Nutricional")
st.markdown("Herramienta de cuantificación rápida y generación de informe clínico consolidado.")

st.markdown("---")

# Inicializar estado de sesión
if "informe" not in st.session_state:
    st.session_state.informe = {}

# 1. Selector de Región Anatómica
region = st.selectbox(
    "📌 Selecciona la región / músculo a analizar:",
    [
        "🦾 Bíceps Braquial (Miembro Superior)",
        "🦵 Tibial Anterior (Miembro Inferior)",
        "🧱 Recto Abdominal (Músculo Central)",
        "🫄 Distribución de Grasa Abdominal"
    ]
)

st.markdown("---")

# 2. Carga de archivo
uploaded_file = st.file_uploader(f"📂 Sube la ecografía para: {region}", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img_gray = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
    h, w = img_gray.shape

    st.subheader("🖼️ Ajuste de ROIs y Guía de Escala")

    # Controles deslizantes
    col_sub, col_mus = st.columns(2)
    with col_sub:
        st.write("🔴 **Grasa Subcutánea**")
        sub_y = st.slider("Eje Y (Profundidad)", 0, h, (int(h*0.1), int(h*0.3)), key=f"sub_y_{region}")
        sub_x = st.slider("Eje X (Ancho)", 0, w, (int(w*0.1), int(w*0.9)), key=f"sub_x_{region}")
    
    with col_mus:
        st.write("🔵 **Músculo / Profundo**")
        mus_y = st.slider("Eje Y (Profundidad)", 0, h, (int(h*0.4), int(h*0.7)), key=f"mus_y_{region}")
        mus_x = st.slider("Eje X (Ancho)", 0, w, (int(w*0.1), int(w*0.9)), key=f"mus_x_{region}")

    # Dibujar recuadros
    img_color = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)
    cv2.rectangle(img_color, (sub_x[0], sub_y[0]), (sub_x[1], sub_y[1]), (255, 0, 0), 3) # Rojo
    cv2.rectangle(img_color, (mus_x[0], mus_y[0]), (mus_x[1], mus_y[1]), (0, 0, 255), 3) # Azul

    # MOSTRAR IMAGEN CON REGLA Y EJES GRADUADOS
    fig_img, ax_img = plt.subplots(figsize=(8, 5))
    ax_img.imshow(cv2.cvtColor(img_color, cv2.COLOR_BGR2RGB))
    ax_img.set_xlabel("Ancho (Eje X en píxeles)", fontsize=10)
    ax_img.set_ylabel("Profundidad (Eje Y en píxeles)", fontsize=10)
    ax_img.tick_params(axis='both', which='major', labelsize=9)
    plt.tight_layout()
    st.pyplot(fig_img)

    # Cálculos
    sub_crop = img_gray[sub_y[0]:sub_y[1], sub_x[0]:sub_x[1]]
    mus_crop = img_gray[mus_y[0]:mus_y[1], mus_x[0]:mus_x[1]]

    mean_sub = np.mean(sub_crop) if sub_crop.size > 0 else 0.0
    mean_mus = np.mean(mus_crop) if mus_crop.size > 0 else 0.0
    ratio = (mean_mus / mean_sub) if mean_sub > 0 else 0.0

    st.markdown("---")

    # Resultados y Métricas
    st.subheader("📊 Resultados de esta Toma")
    c1, c2, c3 = st.columns(3)
    c1.metric("Grasa Subcutánea (EI)", f"{mean_sub:.1f}")
    c2.metric("Músculo / Profundo (EI)", f"{mean_mus:.1f}")
    c3.metric("Ratio M/S", f"{ratio:.2f}")

    st.write("")
    if st.button("💾 GUARDAR MEDICIÓN EN INFORME FINAL", type="primary", use_container_width=True):
        st.session_state.informe[region] = {
            "Grasa": round(mean_sub, 1),
            "Músculo": round(mean_mus, 1),
            "Ratio": round(ratio, 2),
            "sub_crop": sub_crop,
            "mus_crop": mus_crop
        }
        st.success(f"✅ Medición de **{region}** guardada en el informe.")

    st.markdown("---")

    # HISTOGRAMA PUNTUAL DE ESTA TOMA
    st.subheader("📈 Histograma de esta Toma")
    fig_hist, ax_hist = plt.subplots(figsize=(7, 3))
    if sub_crop.size > 0:
        ax_hist.hist(sub_crop.ravel(), bins=256, range=[0, 256], color='red', alpha=0.5, label=f'Grasa ({mean_sub:.1f})')
    if mus_crop.size > 0:
        ax_hist.hist(mus_crop.ravel(), bins=256, range=[0, 256], color='blue', alpha=0.5, label=f'Músculo ({mean_mus:.1f})')
    ax_hist.set_xlim([0, 255])
    ax_hist.set_xlabel("Escala de Grises (0 = Negro, 255 = Blanco)")
    ax_hist.set_ylabel("Frecuencia")
    ax_hist.legend(loc='upper right')
    st.pyplot(fig_hist)

st.markdown("---")

# ==============================================================================
# FUNCIÓN AUXILIAR PARA CREAR PDF
# ==============================================================================
def generar_pdf(informe_dict, avg_sub, avg_mus, avg_ratio, conclusion):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#1A365D'), spaceAfter=10)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#2B6CB0'), spaceAfter=8)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor('#2D3748'))
    
    # Encabezado
    story.append(Paragraph("INFORME DE VALORACIÓN ECOGRÁFICA NUTRICIONAL", title_style))
    fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(f"<b>Fecha de evaluación:</b> {fecha_str}", body_style))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E0'), spaceAfter=15))
    
    # Tabla de Resultados por Región
    story.append(Paragraph("1. Desglose por Región Anatómica", subtitle_style))
    data = [["Región / Músculo", "Grasa (EI)", "Músculo (EI)", "Ratio M/S", "Diagnóstico"]]
    
    for reg, datos in informe_dict.items():
        estado = "Conservado" if datos["Ratio"] < 0.7 else ("Moderado" if datos["Ratio"] < 1.0 else "Elevado")
        data.append([reg, str(datos["Grasa"]), str(datos["Músculo"]), str(datos["Ratio"]), estado])
        
    t = Table(data, colWidths=[180, 80, 80, 70, 90])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2B6CB0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')])
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    
    # Sumario Global
    story.append(Paragraph("2. Promedios Globales Corporales", subtitle_style))
    data_sumario = [
        ["Media Grasa Subcutánea", "Media Ecogenicidad Muscular", "Ratio M/S Global Promedio"],
        [f"{avg_sub:.1f}", f"{avg_mus:.1f}", f"{avg_ratio:.2f}"]
    ]
    t_sumario = Table(data_sumario, colWidths=[160, 170, 170])
    t_sumario.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EDF2F7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2D3748')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
    ]))
    story.append(t_sumario)
    story.append(Spacer(1, 15))
    
    # Conclusión Clínica
    story.append(Paragraph("<b>Conclusión Diagnóstica:</b>", body_style))
    story.append(Paragraph(f"{conclusion}", body_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# ==============================================================================
# SECCIÓN DEL INFORME CLÍNICO CONSOLIDADO
# ==============================================================================
st.header("📋 INFORME CLÍNICO CONSOLIDADO")

if st.session_state.informe:
    # 1. TABLA RESUMEN POR ZONAS
    st.subheader("📌 Desglose por Región Anatómica")
    tabla_datos = []
    
    musculares = [d for reg, d in st.session_state.informe.items() if "Grasa" not in reg]
    
    for reg, datos in st.session_state.informe.items():
        estado = "Conservado" if datos["Ratio"] < 0.7 else ("Moderado" if datos["Ratio"] < 1.0 else "Elevado")
        tabla_datos.append({
            "Región / Músculo": reg,
            "Grasa (EI)": datos["Grasa"],
            "Músculo (EI)": datos["Músculo"],
            "Ratio M/S": datos["Ratio"],
            "Diagnóstico": estado
        })
    st.table(tabla_datos)

    # 2. SUMARIO EJECUTIVO CON MEDIAS GLOBALES
    st.subheader("📊 SUMARIO GLOBAL CORPORAL")
    if musculares:
        avg_sub = np.mean([d["Grasa"] for d in musculares])
        avg_mus = np.mean([d["Músculo"] for d in musculares])
        avg_ratio = np.mean([d["Ratio"] for d in musculares])

        col_g1, col_g2, col_g3 = st.columns(3)
        col_g1.metric("Media Grasa Subcutánea", f"{avg_sub:.1f}")
        col_g2.metric("Media Ecogenicidad Muscular", f"{avg_mus:.1f}")
        
        diag_global_text = "Conservado" if avg_ratio < 0.7 else ("Infiltración Leve" if avg_ratio < 1.0 else "Severo")
        col_g3.metric("Ratio M/S Global Promedio", f"{avg_ratio:.2f}", diag_global_text)

        # Conclusión Diagnóstica Texto
        if avg_ratio < 0.7:
            conclusion_text = f"Ecosarcopenia Negativa (Score Global: {avg_ratio:.2f}): El promedio de los músculos evaluados muestra una masa y calidad muscular globalmente bien conservadas."
            st.success(f"✅ **{conclusion_text}**")
        elif 0.7 <= avg_ratio < 1.0:
            conclusion_text = f"Infiltración Grasa / Sarcopenia Inicial (Score Global: {avg_ratio:.2f}): Ligero o moderado aumento global en la ecogenicidad muscular. Se sugiere intervención preventiva."
            st.warning(f"⚠️ **{conclusion_text}**")
        else:
            conclusion_text = f"Miosteatosis / Atrofia Severa Global (Score Global: {avg_ratio:.2f}): Elevada reflectividad generalizada. Indicación clara de tratamiento nutricional y ejercicio prescriptivo."
            st.error(f"🚨 **{conclusion_text}**")

        st.markdown("---")
        
        # BOTÓN DE DESCARGA PDF
        pdf_bytes = generar_pdf(st.session_state.informe, avg_sub, avg_mus, avg_ratio, conclusion_text)
        
        st.download_button(
            label="📥 DESCARGAR INFORME CLÍNICO EN PDF",
            data=pdf_bytes,
            file_name=f"Informe_Ecografico_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )

    st.write("")
    if st.button("🗑️ Limpiar datos y comenzar nuevo paciente", use_container_width=True):
        st.session_state.informe = {}
        st.rerun()

else:
    st.info("Aún no has guardado ninguna medición. Selecciona un músculo arriba, ajusta la toma y pulsa 'GUARDAR MEDICIÓN EN INFORME FINAL'.")
