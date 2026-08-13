import streamlit as st
import cv2
import numpy as np
import matplotlib.pyplot as plt
import io
from datetime import datetime

# Importaciones para ReportLab (PDF)
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Configuración de página
st.set_page_config(page_title="EcoSarcopenia Pro", layout="centered")

st.title("🩺 Valoración Ecográfica Nutricional")
st.markdown("Herramienta de análisis automatizado con escalas e informe clínico avanzado.")

st.markdown("---")

# Inicializar estado de sesión
if "informe" not in st.session_state:
    st.session_state.informe = {}
if "hist_data" not in st.session_state:
    st.session_state.hist_data = {}

# 1. Selector de Región Anatómica
region = st.selectbox(
    "📌 Selecciona la región a analizar:",
    [
        "🦾 Bíceps Braquial (Miembro Superior - Ecointensidad)",
        "🦵 Tibial Anterior (Miembro Inferior - Ecointensidad)",
        "🧱 Recto Abdominal (Músculo Central - Ecointensidad)",
        "🫄 Adiposidad Abdominal (Cálculo Automático de Índice GVA/GSA)"
    ]
)

st.markdown("---")

es_evaluacion_grasa = "Adiposidad Abdominal" in region

uploaded_file = st.file_uploader(f"📂 Sube la ecografía para: {region}", type=["png", "jpg", "jpeg"], key=f"file_{region}")

if uploaded_file is not None:
    file_bytes = np.frombuffer(uploaded_file.getvalue(), dtype=np.uint8)
    img_gray = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
    
    if img_gray is not None:
        h, w = img_gray.shape

        # ==============================================================================
        # OPCIÓN A: GRASA ABDOMINAL (ESPESORES E ÍNDICE GVA/GSA)
        # ==============================================================================
        if es_evaluacion_grasa:
            st.subheader("📏 Medición Automática de Espesores e Índice de Correlación")
            st.info("💡 Ajusta los límites de profundidad. La app calcula los espesores y el índice GVA/GSA automáticamente.")

            col_gsa_lim, col_gva_lim = st.columns(2)
            with col_gsa_lim:
                st.write("🟢 **Capa Subcutánea (GSA)**")
                gsa_y = st.slider("Límites Piel -> Fascia Anterior", 0, h, (int(h*0.10), int(h*0.30)), key="gsa_y")
            with col_gva_lim:
                st.write("🔴 **Capa Visceral (GVA)**")
                gva_y = st.slider("Límites Fascia Posterior -> Aorta/Peritoneo", 0, h, (int(h*0.35), int(h*0.80)), key="gva_y")

            espesor_gsa = abs(gsa_y[1] - gsa_y[0])
            espesor_gva = abs(gva_y[1] - gva_y[0])
            indice_correlacion = (espesor_gva / espesor_gsa) if espesor_gsa > 0 else 0.0

            img_color = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)

            cv2.rectangle(img_color, (int(w*0.25), gsa_y[0]), (int(w*0.75), gsa_y[1]), (0, 255, 0), 3)
            cv2.rectangle(img_color, (int(w*0.25), gva_y[0]), (int(w*0.75), gva_y[1]), (0, 0, 255), 3)

            fig, ax = plt.subplots(figsize=(8, 6))
            ax.imshow(cv2.cvtColor(img_color, cv2.COLOR_BGR2RGB))
            ax.set_xlabel("Ancho Transversal (px)", fontsize=12, fontweight='bold', labelpad=10)
            ax.set_ylabel("Profundidad (px)", fontsize=12, fontweight='bold', labelpad=10)
            ax.tick_params(axis='both', which='major', labelsize=11)
            ax.grid(True, color='cyan', alpha=0.3, linestyle='--', linewidth=0.7)

            st.pyplot(fig)

            st.markdown("---")
            st.subheader("📊 Índice de Correlación Calculado")
            c1, c2, c3 = st.columns(3)
            c1.metric("Espesor Subcutáneo (GSA)", f"{espesor_gsa} px")
            c2.metric("Espesor Visceral (GVA)", f"{espesor_gva} px")
            c3.metric("Índice GVA / GSA", f"{indice_correlacion:.2f}")

            if indice_correlacion > 1.0:
                st.error("🚨 **Predominio Visceral (Índice > 1.00):** Riesgo cardiometabólico elevado.")
            else:
                st.success("✅ **Predominio Subcutáneo (Índice ≤ 1.00):** Distribución dentro de rangos normales.")

            st.write("")
            if st.button("💾 GUARDAR ÍNDICE ABDOMINAL EN INFORME", type="primary", use_container_width=True):
                st.session_state.informe["Grasa Abdominal"] = {
                    "Grasa": espesor_gsa,
                    "Músculo": espesor_gva,
                    "Ratio": round(indice_correlacion, 2),
                    "Tipo": "Correlación Abdominal"
                }
                st.success("✅ Índice de correlación abdominal guardado en el informe.")

        # ==============================================================================
        # OPCIÓN B: ECOINTENSIDAD MUSCULAR (ROIs)
        # ==============================================================================
        else:
            st.subheader("🖼️ Delimitación de ROIs sobre Ecografía Muscular")

            col_sub, col_mus = st.columns(2)
            with col_sub:
                st.write(f"🔵 **Tejido Adiposo Subcutáneo (Ref.)**")
                sub_y = st.slider("Eje Y (Profundidad)", 0, h, (int(h*0.15), int(h*0.35)), key=f"sub_y_{region}")
                sub_x = st.slider("Eje X (Ancho Transversal)", 0, w, (int(w*0.1), int(w*0.9)), key=f"sub_x_{region}")
            
            with col_mus:
                st.write(f"🔴 **Tejido Muscular (EI)**")
                mus_y = st.slider("Eje Y (Profundidad)", 0, h, (int(h*0.45), int(h*0.75)), key=f"mus_y_{region}")
                mus_x = st.slider("Eje X (Ancho Transversal)", 0, w, (int(w*0.1), int(w*0.9)), key=f"mus_x_{region}")

            img_color = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)

            cv2.rectangle(img_color, (sub_x[0], sub_y[0]), (sub_x[1], sub_y[1]), (255, 0, 0), 3)
            cv2.rectangle(img_color, (mus_x[0], mus_y[0]), (mus_x[1], mus_y[1]), (0, 0, 255), 3)

            fig, ax = plt.subplots(figsize=(8, 6))
            ax.imshow(cv2.cvtColor(img_color, cv2.COLOR_BGR2RGB))
            ax.set_xlabel("Ancho Transversal (px)", fontsize=12, fontweight='bold', labelpad=10)
            ax.set_ylabel("Profundidad (px)", fontsize=12, fontweight='bold', labelpad=10)
            ax.tick_params(axis='both', which='major', labelsize=11)
            ax.grid(True, color='cyan', alpha=0.3, linestyle='--', linewidth=0.7)

            st.pyplot(fig)

            sub_crop = img_gray[sub_y[0]:sub_y[1], sub_x[0]:sub_x[1]]
            mus_crop = img_gray[mus_y[0]:mus_y[1], mus_x[0]:mus_x[1]]

            mean_sub = np.mean(sub_crop) if sub_crop.size > 0 else 0.0
            mean_mus = np.mean(mus_crop) if mus_crop.size > 0 else 0.0
            ratio_ms = (mean_mus / mean_sub) if mean_sub > 0 else 0.0

            st.markdown("---")
            st.subheader("📊 Resultados de Ecointensidad (Calidad Muscular)")
            c1, c2, c3 = st.columns(3)
            c1.metric("Grasa Subcutánea (EI)", f"{mean_sub:.1f}")
            c2.metric("Músculo (EI)", f"{mean_mus:.1f}")
            c3.metric("Ratio M/S", f"{ratio_ms:.2f}")

            if st.button("💾 GUARDAR MEDICIÓN MUSCULAR EN INFORME", type="primary", use_container_width=True):
                st.session_state.informe[region] = {
                    "Grasa": round(mean_sub, 1),
                    "Músculo": round(mean_mus, 1),
                    "Ratio": round(ratio_ms, 2),
                    "Tipo": "Ecointensidad"
                }
                # Guardar datos para el histograma general
                st.session_state.hist_data[region] = mus_crop.ravel()
                st.success(f"✅ Medición de **{region}** guardada correctamente.")

            st.markdown("---")
            st.subheader("📈 Histograma de Escala de Grises")
            fig_hist, ax_hist = plt.subplots(figsize=(7, 3))
            if sub_crop.size > 0:
                ax_hist.hist(sub_crop.ravel(), bins=256, range=[0, 256], color='blue', alpha=0.5, label=f'Subcutáneo ({mean_sub:.1f})')
            if mus_crop.size > 0:
                ax_hist.hist(mus_crop.ravel(), bins=256, range=[0, 256], color='red', alpha=0.5, label=f'Músculo ({mean_mus:.1f})')
            ax_hist.set_xlim([0, 255])
            ax_hist.set_xlabel("Escala de Grises (0 = Negro, 255 = Blanco)")
            ax_hist.set_ylabel("Frecuencia")
            ax_hist.legend(loc='upper right')
            st.pyplot(fig_hist)

st.markdown("---")

# ==============================================================================
# FUNCIÓN QUE GENERA EL HISTOGRAMA GENERAL PARA EL PDF
# ==============================================================================
def generar_imagen_histograma_general(hist_dict):
    fig, ax = plt.subplots(figsize=(7, 2.5))
    colores = ['red', 'green', 'purple', 'orange']
    
    for idx, (reg, pixeles) in enumerate(hist_dict.items()):
        if pixeles.size > 0:
            nombre_corto = reg.split('(')[0].strip()
            ax.hist(pixeles, bins=256, range=[0, 256], color=colores[idx % len(colores)], alpha=0.4, label=nombre_corto)

    ax.set_xlim([0, 255])
    ax.set_title("Distribución Comparativa de Ecointensidad Muscular (Escala de Grises)", fontsize=9, fontweight='bold')
    ax.set_xlabel("Intensidad de Gris (0-255)", fontsize=8)
    ax.set_ylabel("Frecuencia (px)", fontsize=8)
    ax.tick_params(axis='both', which='major', labelsize=7)
    ax.legend(loc='upper right', fontsize=7)
    plt.tight_layout()

    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', dpi=200)
    img_buf.seek(0)
    plt.close(fig)
    return img_buf

# ==============================================================================
# FUNCIÓN GENERADORA DE PDF AVANZADO
# ==============================================================================
def generar_pdf_clinico(datos_informe, hist_data, nombre_paciente, nombre_medico, n_colegiado, observaciones):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    story = []
    styles = getSampleStyleSheet()

    # Estilos
    titulo_style = ParagraphStyle('TituloPDF', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#003366'), spaceAfter=4)
    subtitulo_style = ParagraphStyle('SubtituloPDF', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#666666'), spaceAfter=12)
    seccion_style = ParagraphStyle('SeccionPDF', parent=styles['Heading2'], fontSize=11, leading=14, textColor=colors.HexColor('#003366'), spaceBefore=10, spaceAfter=6, fontName='Helvetica-Bold')
    body_style = ParagraphStyle('BodyPDF', parent=styles['Normal'], fontSize=8.5, leading=11.5, textColor=colors.HexColor('#333333'))
    header_tabla = ParagraphStyle('HeaderTabla', parent=styles['Normal'], fontSize=8.5, leading=10, textColor=colors.white, fontName='Helvetica-Bold')
    cell_style = ParagraphStyle('CellTabla', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#222222'))

    # Encabezado
    story.append(Paragraph("INFORME ECOGRÁFICO DE VALORACIÓN NUTRICIONAL Y SARCOPENIA", titulo_style))
    story.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')} | EcoSarcopenia Pro v2.0", subtitulo_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#003366'), spaceAfter=10))

    # Datos
    datos_paciente = [
        [Paragraph(f"<b>Paciente:</b> {nombre_paciente}", body_style), Paragraph(f"<b>Médico Eval.:</b> {nombre_medico}", body_style)],
        [Paragraph(f"<b>Fecha Eval.:</b> {datetime.now().strftime('%d/%m/%Y')}", body_style), Paragraph(f"<b>Nº Colegiado:</b> {n_colegiado}", body_style)]
    ]
    t_paciente = Table(datos_paciente, colWidths=[270, 270])
    t_paciente.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0F4F8')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC'))
    ]))
    story.append(t_paciente)
    story.append(Spacer(1, 10))

    # Tabla de Resultados
    story.append(Paragraph("1. RESUMEN DE MEDICIONES ECOGRÁFICAS", seccion_style))
    tabla_datos = [[
        Paragraph("<b>Región Anatómica Analizada</b>", header_tabla),
        Paragraph("<b>Ref. Subcutáneo</b>", header_tabla),
        Paragraph("<b>Tejido Objetivo</b>", header_tabla),
        Paragraph("<b>Ratio / Índice</b>", header_tabla),
        Paragraph("<b>Evaluación Presuntiva</b>", header_tabla)
    ]]

    for reg, vals in datos_informe.items():
        ratio = vals["Ratio"]
        tipo = vals["Tipo"]
        if tipo == "Correlación Abdominal":
            eval_text = "<font color='red'><b>Predominio Visceral</b></font>" if ratio > 1.0 else "<font color='green'><b>Predominio Subcutáneo</b></font>"
        else:
            if ratio < 0.8:
                eval_text = "<font color='green'><b>Buena Calidad Muscular</b></font>"
            elif ratio <= 1.2:
                eval_text = "<font color='orange'><b>Infiltración Moderada</b></font>"
            else:
                eval_text = "<font color='red'><b>Infiltración Severa</b></font>"

        tabla_datos.append([
            Paragraph(reg, cell_style),
            Paragraph(str(vals["Grasa"]), cell_style),
            Paragraph(str(vals["Músculo"]), cell_style),
            Paragraph(f"<b>{ratio}</b>", cell_style),
            Paragraph(eval_text, cell_style)
        ])

    t = Table(tabla_datos, colWidths=[160, 95, 95, 90, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')])
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    # Histograma General (si existen regiones musculares)
    if hist_data:
        story.append(Paragraph("2. HISTOGRAMA COMPARATIVO DE ECOINTENSIDAD", seccion_style))
        img_hist_buf = generar_imagen_histograma_general(hist_data)
        story.append(RLImage(img_hist_buf, width=520, height=180))
        story.append(Spacer(1, 8))

    # Observaciones Clínicas
    story.append(Paragraph("3. OBSERVACIONES CLÍNICAS Y DIAGNÓSTICO", seccion_style))
    obs_texto = observaciones.strip() if observaciones.strip() else "Sin observaciones registradas."
    story.append(Paragraph(f"<b>Notas:</b> {obs_texto}", body_style))
    story.append(Spacer(1, 25))

    # Firma
    tabla_firma = [
        [Paragraph(f"__________________________________________<br/><b>Dr/a. {nombre_medico}</b><br/>Col. Nº {n_colegiado}", body_style),
         Paragraph("__________________________________________<br/><b>Firma / Conformidad del Paciente</b>", body_style)]
    ]
    t_firma = Table(tabla_firma, colWidths=[270, 270])
    t_firma.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    story.append(t_firma)

    doc.build(story)
    buffer.seek(0)
    return buffer

# ==============================================================================
# SECCIÓN FINAL: INFORME CLÍNICO CONSOLIDADO Y FORMULARIO PREVIO
# ==============================================================================
st.header("📋 INFORME CLÍNICO CONSOLIDADO")

if st.session_state.informe:
    st.markdown("### Resumen de Parámetros Analizados")
    
    # Formato visual de las mediciones
    for item_region, valores in st.session_state.informe.items():
        with st.container():
            st.subheader(f"📌 {item_region}")
            col1, col2, col3 = st.columns(3)
            
            if valores["Tipo"] == "Correlación Abdominal":
                col1.metric("Espesor Subcutáneo (GSA)", f"{valores['Grasa']} px")
                col2.metric("Espesor Visceral (GVA)", f"{valores['Músculo']} px")
                col3.metric("Índice GVA / GSA", f"{valores['Ratio']}")
            else:
                col1.metric("Grasa Subcutánea (EI)", f"{valores['Grasa']}")
                col2.metric("Músculo (EI)", f"{valores['Músculo']}")
                col3.metric("Ratio M/S", f"{valores['Ratio']}")
            st.markdown("---")

    # 📝 FORMULARIO INTERACTIVO PARA DATOS DEL MÉDICO Y OBSERVACIONES
    st.subheader("📝 Datos del Informe y Firma Médica")
    col_p, col_m, col_c = st.columns(3)
    with col_p:
        nombre_pac = st.text_input("👤 Paciente:", value="Paciente Anónimo")
    with col_m:
        nombre_med = st.text_input("🩺 Médico Evaluador:", value="Dr. / Dra.")
    with col_c:
        num_col = st.text_input("🆔 Nº Colegiado:", value="123456")

    obs_clinicas = st.text_area(
        "💬 Observaciones Clínicas / Diagnóstico Presuntivo:",
        placeholder="Escribe aquí el juicio clínico, recomendaciones de nutrición o tratamiento..."
    )

    st.markdown("---")

    # Generación y descarga del PDF completo
    pdf_bytes = generar_pdf_clinico(
        st.session_state.informe,
        st.session_state.hist_data,
        nombre_paciente=nombre_pac,
        nombre_medico=nombre_med,
        n_colegiado=num_col,
        observaciones=obs_clinicas
    )
    
    st.download_button(
        label="📄 DESCARGAR INFORME CLÍNICO COMPLETO (PDF)",
        data=pdf_bytes,
        file_name=f"Informe_Ecografico_{nombre_pac.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True
    )

else:
    st.info("💡 Realiza y guarda al menos una medición para habilitar el informe y la descarga en PDF.")
