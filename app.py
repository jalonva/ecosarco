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
st.markdown("Herramienta de cuantificación rápida para consulta.")

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
        "🫄 Distribución de Grasa Abdominal (Independiente)"
    ]
)

st.markdown("---")

# 2. Carga de archivo
uploaded_file = st.file_uploader(f"📂 Sube la ecografía para: {region}", type=["png", "jpg", "jpeg"], key=f"file_{region}")

if uploaded_file is not None:
    file_bytes = np.frombuffer(uploaded_file.getvalue(), dtype=np.uint8)
    img_gray = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
    
    if img_gray is not None:
        h, w = img_gray.shape

        st.subheader("🖼️ Ajuste de ROIs sobre Ecografía Pura")

        # Controles deslizantes
        col_sub, col_mus = st.columns(2)
        with col_sub:
            st.write(f"🔴 **Superficial / Subcutánea**")
            sub_y = st.slider("Eje Y (Profundidad)", 0, h, (int(h*0.15), int(h*0.35)), key=f"sub_y_{region}")
            sub_x = st.slider("Eje X (Ancho)", 0, w, (int(w*0.1), int(w*0.9)), key=f"sub_x_{region}")
        
        with col_mus:
            st.write(f"🔵 **Profunda / Visceral / Muscular**")
            mus_y = st.slider("Eje Y (Profundidad)", 0, h, (int(h*0.45), int(h*0.75)), key=f"mus_y_{region}")
            mus_x = st.slider("Eje X (Ancho)", 0, w, (int(w*0.1), int(w*0.9)), key=f"mus_x_{region}")

        # Dibujar recuadros
        img_color = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)

        paso_y = max(50, int(h / 10))
        for y_mark in range(0, h, paso_y):
            cv2.line(img_color, (0, y_mark), (15, y_mark), (0, 255, 255), 2)
            cv2.putText(img_color, f"{y_mark}", (20, y_mark + 4), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

        cv2.rectangle(img_color, (sub_x[0], sub_y[0]), (sub_x[1], sub_y[1]), (255, 0, 0), 3)
        cv2.rectangle(img_color, (mus_x[0], mus_y[0]), (mus_x[1], mus_y[1]), (0, 0, 255), 3)

        st.image(img_color, channels="BGR", use_container_width=True)

        # Recortes para cálculos
        sub_crop = img_gray[sub_y[0]:sub_y[1], sub_x[0]:sub_x[1]]
        mus_crop = img_gray[mus_y[0]:mus_y[1], mus_x[0]:mus_x[1]]

        mean_sub = np.mean(sub_crop) if sub_crop.size > 0 else 0.0
        mean_mus = np.mean(mus_crop) if mus_crop.size > 0 else 0.0
        ratio = (mean_mus / mean_sub) if mean_sub > 0 else 0.0

        st.markdown("---")

        # Resultados
        st.subheader("📊 Resultados de esta Toma")
        c1, c2, c3 = st.columns(3)
        c1.metric("Superficial (EI)", f"{mean_sub:.1f}")
        c2.metric("Profunda (EI)", f"{mean_mus:.1f}")
        c3.metric("Ratio P/S", f"{ratio:.2f}")

        st.write("")
        if st.button("💾 GUARDAR MEDICIÓN EN INFORME FINAL", type="primary", use_container_width=True):
            st.session_state.informe[region] = {
                "Grasa": round(mean_sub, 1),
                "Músculo": round(mean_mus, 1),
                "Ratio": round(ratio, 2)
            }
            st.success(f"✅ Medición de **{region}** guardada en el informe.")

        st.markdown("---")

        # HISTOGRAMA INDEPENDIENTE
        st.subheader("📈 Histograma de esta Toma")
        fig_hist, ax_hist = plt.subplots(figsize=(7, 3))
        if sub_crop.size > 0:
            ax_hist.hist(sub_crop.ravel(), bins=256, range=[0, 256], color='red', alpha=0.5, label=f'Superficial ({mean_sub:.1f})')
        if mus_crop.size > 0:
            ax_hist.hist(mus_crop.ravel(), bins=256, range=[0, 256], color='blue', alpha=0.5, label=f'Profunda ({mean_mus:.1f})')
        ax_hist.set_xlim([0, 255])
        ax_hist.set_xlabel("Escala de Grises (0 = Negro, 255 = Blanco)")
        ax_hist.set_ylabel("Frecuencia")
        ax_hist.legend(loc='upper right')
        st.pyplot(fig_hist)

st.markdown("---")

# ==============================================================================
# FUNCIÓN GENERADORA DEL PDF CLINICO CON VALORES DE REFERENCIA
# ==============================================================================
def generar_pdf(informe_dict, avg_sub, avg_mus, avg_ratio, conclusion_muscular, info_visceral):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1A365D'), spaceAfter=8)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Heading2'], fontSize=11, textColor=colors.HexColor('#2B6CB0'), spaceAfter=6)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor('#2D3748'))
    small_style = ParagraphStyle('SmallStyle', parent=styles['Normal'], fontSize=8, leading=11, textColor=colors.HexColor('#4A5568'))

    # Encabezado
    story.append(Paragraph("INFORME DE VALORACIÓN ECOGRÁFICA NUTRICIONAL", title_style))
    fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(f"<b>Fecha de evaluación:</b> {fecha_str}", body_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E0'), spaceAfter=10))
    
    # 1. Tabla Resumen con Comparativa Normativa
    story.append(Paragraph("1. Desglose de Mediciones y Comparativa Normativa", subtitle_style))
    data = [["Región / Área", "Capa Sup.", "Capa Prof.", "Ratio P/S", "Valor Normal", "Resultado"]]
    
    for reg, datos in informe_dict.items():
        es_visceral = "Grasa" in reg
        rango_ref = "< 1.00 (Subcutáneo)" if es_visceral else "< 0.70 (Normal)"
        
        if es_visceral:
            estado = "Normal" if datos["Ratio"] < 1.0 else "Elevado (Visceral)"
        else:
            estado = "Normal" if datos["Ratio"] < 0.7 else ("Moderado" if datos["Ratio"] < 1.0 else "Elevado")
            
        data.append([reg, str(datos["Grasa"]), str(datos["Músculo"]), str(datos["Ratio"]), rango_ref, estado])
        
    t = Table(data, colWidths=[150, 65, 65, 60, 100, 80])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2B6CB0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')])
    ]))
    story.append(t)
    story.append(Spacer(1, 12))
    
    # 2. Conclusión Muscular
    story.append(Paragraph("2. Evaluación Muscular Global (Excluye Grasa Visceral)", subtitle_style))
    if avg_ratio is not None:
        data_sumario = [
            ["Media Subcutánea", "Media Músculo", "Ratio M/S Global", "Rango de Referencia Normal"],
            [f"{avg_sub:.1f}", f"{avg_mus:.1f}", f"{avg_ratio:.2f}", "< 0.70"]
        ]
        t_sumario = Table(data_sumario, colWidths=[120, 120, 120, 140])
        t_sumario.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EDF2F7')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ]))
        story.append(t_sumario)
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>Diagnóstico Muscular:</b> {conclusion_muscular}", body_style))
    else:
        story.append(Paragraph("<i>No se registraron mediciones musculares.</i>", body_style))
        
    story.append(Spacer(1, 12))
    
    # 3. Conclusión Visceral
    story.append(Paragraph("3. Valoración Adiposidad Abdominal / Visceral", subtitle_style))
    if info_visceral:
        story.append(Paragraph(f"<b>Diagnóstico Cardiometabólico:</b> {info_visceral}", body_style))
    else:
        story.append(Paragraph("<i>No se evaluó adiposidad visceral en esta sesión.</i>", body_style))
        
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E0'), spaceAfter=8))
    
    # 4. Leyenda de Valores Normales
    story.append(Paragraph("<b>Guía de Interpretación Clínica:</b>", small_style))
    story.append(Paragraph("• <b>Ratio Muscular (M/S):</b> < 0.70 (Tejido Muscular Sano) | 0.70 - 0.99 (Infiltración Grasa Moderada) | ≥ 1.00 (Miosteatosis Severa / Atrofia)", small_style))
    story.append(Paragraph("• <b>Ratio Abdominal (P/S):</b> < 1.00 (Predominio Subcutáneo / Normal) | ≥ 1.00 (Predominio Visceral Profundo / Riesgo Aumentado)", small_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# ==============================================================================
# SECCIÓN DEL INFORME CLÍNICO CONSOLIDADO
# ==============================================================================
st.header("📋 INFORME CLÍNICO CONSOLIDADO")

if st.session_state.informe:
    st.subheader("📌 Desglose y Comparativa Normativa")
    tabla_datos = []
    
    mediciones_musculo = {k: v for k, v in st.session_state.informe.items() if "Grasa" not in k}
    medicion_visceral = {k: v for k, v in st.session_state.informe.items() if "Grasa" in k}

    for reg, datos in st.session_state.informe.items():
        es_visceral = "Grasa" in reg
        rango_ref = "< 1.00" if es_visceral else "< 0.70"
        
        if es_visceral:
            estado = "Normal" if datos["Ratio"] < 1.0 else "Elevado (Visceral)"
        else:
            estado = "Normal" if datos["Ratio"] < 0.7 else ("Moderado" if datos["Ratio"] < 1.0 else "Elevado")

        tabla_datos.append({
            "Región / Área": reg,
            "Capa Sup. (EI)": datos["Grasa"],
            "Capa Prof. (EI)": datos["Músculo"],
            "Ratio P/S": datos["Ratio"],
            "Valor Normal": rango_ref,
            "Estado": estado
        })
    st.table(tabla_datos)

    avg_sub, avg_mus, avg_ratio, conclusion_muscular = None, None, None, ""
    info_visceral_txt = ""

    # 1. VALORACIÓN MUSCULAR
    if mediciones_musculo:
        st.subheader("🦾 1. VALORACIÓN MUSCULAR GLOBAL (Excluye Grasa Visceral)")
        avg_sub = np.mean([d["Grasa"] for d in mediciones_musculo.values()])
        avg_mus = np.mean([d["Músculo"] for d in mediciones_musculo.values()])
        avg_ratio = np.mean([d["Ratio"] for d in mediciones_musculo.values()])

        col_g1, col_g2, col_g3 = st.columns(3)
        col_g1.metric("Media Grasa Subcutánea", f"{avg_sub:.1f}")
        col_g2.metric("Media Ecogenicidad Muscular", f"{avg_mus:.1f}")
        col_g3.metric("Ratio M/S Global", f"{avg_ratio:.2f}", delta="Normal: < 0.70", delta_color="inverse")

        if avg_ratio < 0.7:
            conclusion_muscular = f"Calidad Muscular Conservada (Score: {avg_ratio:.2f}): Dentro del rango de referencia normal (< 0.70)."
            st.success(f"✅ **{conclusion_muscular}**")
        elif 0.7 <= avg_ratio < 1.0:
            conclusion_muscular = f"Infiltración Grasa Moderada (Score: {avg_ratio:.2f}): Ligeramente por encima de la norma (0.70 - 0.99)."
            st.warning(f"⚠️ **{conclusion_muscular}**")
        else:
            conclusion_muscular = f"Miosteatosis / Atrofia Severa (Score: {avg_ratio:.2f}): Muy elevado respecto a la norma (≥ 1.00)."
            st.error(f"🚨 **{conclusion_muscular}**")

    # 2. VALORACIÓN VISCERAL
    if medicion_visceral:
        st.markdown("---")
        st.subheader("🫄 2. VALORACIÓN DE ADIPOSIDAD ABDOMINAL Y VISCERAL")
        for reg, datos in medicion_visceral.items():
            r_visc = datos["Ratio"]
            st.write(f"**Grasa Profunda/Subcutánea Abdominal:** {r_visc:.2f} *(Valor normal: < 1.00)*")
            if r_visc > 1.0:
                info_visceral_txt = f"Predominio de Adiposidad Visceral Profunda (Ratio: {r_visc:.2f} | Normal < 1.00): Elevado riesgo cardiometabólico."
                st.error(f"🚨 **{info_visceral_txt}**")
            else:
                info_visceral_txt = f"Distribución Subcutánea Normal (Ratio: {r_visc:.2f} | Normal < 1.00): Acumulación dentro de parámetros aceptables."
                st.info(f"ℹ️ **{info_visceral_txt}**")

    st.markdown("---")
    
    # BOTÓN PDF
    pdf_bytes = generar_pdf(st.session_state.informe, avg_sub, avg_mus, avg_ratio, conclusion_muscular, info_visceral_txt)
    
    st.download_button(
        label="📥 DESCARGAR INFORME CLÍNICO COMPLETO EN PDF",
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
