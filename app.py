import streamlit as st
import cv2
import numpy as np
import matplotlib.pyplot as plt
import io
from datetime import datetime

# Importaciones para generación de reporte en PDF con ReportLab
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA E INICIALIZACIÓN DE ESTADO
# ==============================================================================
st.set_page_config(page_title="EcoSarcopenia Pro v2.0", layout="centered")

st.title("🩺 EcoSarcopenia Pro - Valoración Nutricional")
st.markdown("Herramienta diagnóstica ecográfica con análisis multimodal e interpretación clínica derivada.")

st.markdown("---")

# Estado de la sesión para persistencia de datos
if "informe" not in st.session_state:
    st.session_state.informe = {}
if "hist_data" not in st.session_state:
    st.session_state.hist_data = {}
if "imagenes_roi" not in st.session_state:
    st.session_state.imagenes_roi = {}
if "imagenes_hist_indiv" not in st.session_state:
    st.session_state.imagenes_hist_indiv = {}

# ==============================================================================
# 1. SELECTOR DE REGIÓN ANATÓMICA
# ==============================================================================
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

        # ----------------------------------------------------------------------
        # OPCIÓN A: GRASA ABDOMINAL (ESPESORES E ÍNDICE GVA/GSA)
        # ----------------------------------------------------------------------
        if es_evaluacion_grasa:
            st.subheader("📏 Medición de Espesores e Índice GVA/GSA")
            st.info("💡 Ajusta las regiones de interés. La aplicación calculará automáticamente los espesores y el riesgo cardiometabólico derivado.")

            col_gsa_lim, col_gva_lim = st.columns(2)
            with col_gsa_lim:
                st.write("🟢 **Grasa Subcutánea Abdominal (GSA)**")
                gsa_y = st.slider("Límites Piel -> Fascia Anterior", 0, h, (int(h*0.10), int(h*0.30)), key="gsa_y")
            with col_gva_lim:
                st.write("🔴 **Grasa Visceral Abdominal (GVA)**")
                gva_y = st.slider("Límites Fascia Posterior -> Aorta", 0, h, (int(h*0.35), int(h*0.80)), key="gva_y")

            espesor_gsa = abs(gsa_y[1] - gsa_y[0])
            espesor_gva = abs(gva_y[1] - gva_y[0])
            indice_correlacion = (espesor_gva / espesor_gsa) if espesor_gsa > 0 else 0.0

            img_color = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)
            cv2.rectangle(img_color, (int(w*0.25), gsa_y[0]), (int(w*0.75), gsa_y[1]), (0, 255, 0), 3)
            cv2.rectangle(img_color, (int(w*0.25), gva_y[0]), (int(w*0.75), gva_y[1]), (0, 0, 255), 3)

            fig, ax = plt.subplots(figsize=(8, 4.5))
            ax.imshow(cv2.cvtColor(img_color, cv2.COLOR_BGR2RGB))
            ax.set_xlabel("Ancho Transversal (px)", fontsize=9)
            ax.set_ylabel("Profundidad (px)", fontsize=9)
            ax.grid(True, color='cyan', alpha=0.3, linestyle='--')
            plt.tight_layout()

            st.pyplot(fig)

            img_buf_roi = io.BytesIO()
            fig.savefig(img_buf_roi, format='png', dpi=150)
            img_buf_roi.seek(0)
            plt.close(fig)

            st.markdown("---")
            st.subheader("📊 Métricas de Adiposidad Abdominal")
            c1, c2, c3 = st.columns(3)
            c1.metric("Grasa Subcutánea (GSA)", f"{espesor_gsa} px")
            c2.metric("Grasa Visceral (GVA)", f"{espesor_gva} px")
            c3.metric("Índice GVA / GSA", f"{indice_correlacion:.2f}")

            if indice_correlacion > 1.0:
                st.error("🚨 **Predominio Visceral (Índice > 1.00):** Riesgo cardiometabólico y endotelial elevado.")
            else:
                st.success("✅ **Predominio Subcutáneo (Índice ≤ 1.00):** Perfil de distribución dentro de márgenes fisiológicos.")

            if st.button("💾 GUARDAR ÍNDICE ABDOMINAL EN INFORME", type="primary", use_container_width=True):
                st.session_state.informe["Grasa Abdominal"] = {
                    "Grasa": espesor_gsa,
                    "Músculo": espesor_gva,
                    "Ratio": round(indice_correlacion, 2),
                    "Tipo": "Correlación Abdominal"
                }
                st.session_state.imagenes_roi["Grasa Abdominal"] = img_buf_roi
                st.success("✅ Medición e imagen delimitada guardadas en el informe.")

        # ----------------------------------------------------------------------
        # OPCIÓN B: ECOINTENSIDAD MUSCULAR (ROIs)
        # ----------------------------------------------------------------------
        else:
            st.subheader("🖼️ Delimitación de ROIs sobre Ecografía Muscular")

            col_sub, col_mus = st.columns(2)
            with col_sub:
                st.write("🔵 **Tejido Adiposo Subcutáneo (Ref.)**")
                sub_y = st.slider("Eje Y (Profundidad)", 0, h, (int(h*0.15), int(h*0.35)), key=f"sub_y_{region}")
                sub_x = st.slider("Eje X (Ancho Transversal)", 0, w, (int(w*0.1), int(w*0.9)), key=f"sub_x_{region}")
            
            with col_mus:
                st.write("🔴 **Tejido Muscular (EI)**")
                mus_y = st.slider("Eje Y (Profundidad)", 0, h, (int(h*0.45), int(h*0.75)), key=f"mus_y_{region}")
                mus_x = st.slider("Eje X (Ancho Transversal)", 0, w, (int(w*0.1), int(w*0.9)), key=f"mus_x_{region}")

            img_color = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)

            cv2.rectangle(img_color, (sub_x[0], sub_y[0]), (sub_x[1], sub_y[1]), (255, 0, 0), 3)
            cv2.rectangle(img_color, (mus_x[0], mus_y[0]), (mus_x[1], mus_y[1]), (0, 0, 255), 3)

            fig_roi, ax_roi = plt.subplots(figsize=(8, 4.5))
            ax_roi.imshow(cv2.cvtColor(img_color, cv2.COLOR_BGR2RGB))
            ax_roi.set_xlabel("Ancho Transversal (px)", fontsize=9)
            ax_roi.set_ylabel("Profundidad (px)", fontsize=9)
            ax_roi.grid(True, color='cyan', alpha=0.3, linestyle='--')
            plt.tight_layout()

            st.pyplot(fig_roi)

            img_buf_roi = io.BytesIO()
            fig_roi.savefig(img_buf_roi, format='png', dpi=150)
            img_buf_roi.seek(0)
            plt.close(fig_roi)

            sub_crop = img_gray[sub_y[0]:sub_y[1], sub_x[0]:sub_x[1]]
            mus_crop = img_gray[mus_y[0]:mus_y[1], mus_x[0]:mus_x[1]]

            mean_sub = float(np.mean(sub_crop)) if sub_crop.size > 0 else 0.0
            mean_mus = float(np.mean(mus_crop)) if mus_crop.size > 0 else 0.0
            ratio_ms = (mean_mus / mean_sub) if mean_sub > 0 else 0.0

            st.markdown("---")
            st.subheader("📊 Resultados de Ecointensidad y Calidad Muscular")
            c1, c2, c3 = st.columns(3)
            c1.metric("Grasa Subcutánea (EI)", f"{mean_sub:.1f}")
            c2.metric("Músculo (EI)", f"{mean_mus:.1f}")
            c3.metric("Ratio M/S", f"{ratio_ms:.2f}")

            # Generar Histograma Individual
            fig_hist, ax_hist = plt.subplots(figsize=(7, 2.8))
            if sub_crop.size > 0:
                ax_hist.hist(sub_crop.ravel(), bins=256, range=[0, 256], color='#1976D2', alpha=0.6, label=f'Subcutáneo ({mean_sub:.1f} EI)')
            if mus_crop.size > 0:
                ax_hist.hist(mus_crop.ravel(), bins=256, range=[0, 256], color='#D32F2F', alpha=0.6, label=f'Músculo ({mean_mus:.1f} EI)')
            ax_hist.set_xlim([0, 255])
            ax_hist.set_title(f"Histograma Individual - {region.split('(')[0]}", fontsize=9, fontweight='bold')
            ax_hist.set_xlabel("Escala de Grises (0 = Negro, 255 = Blanco)", fontsize=8)
            ax_hist.set_ylabel("Frecuencia (px)", fontsize=8)
            ax_hist.legend(loc='upper right', fontsize=7.5)
            plt.tight_layout()

            st.pyplot(fig_hist)

            img_buf_hist = io.BytesIO()
            fig_hist.savefig(img_buf_hist, format='png', dpi=150)
            img_buf_hist.seek(0)
            plt.close(fig_hist)

            if st.button("💾 GUARDAR MEDICIÓN MUSCULAR EN INFORME", type="primary", use_container_width=True):
                st.session_state.informe[region] = {
                    "Grasa": round(mean_sub, 1),
                    "Músculo": round(mean_mus, 1),
                    "Ratio": round(ratio_ms, 2),
                    "Tipo": "Ecointensidad"
                }
                st.session_state.hist_data[region] = mus_crop.ravel()
                st.session_state.imagenes_roi[region] = img_buf_roi
                st.session_state.imagenes_hist_indiv[region] = img_buf_hist
                st.success(f"✅ Medición, ecografía e histograma de **{region}** guardados en el informe.")

st.markdown("---")

# ==============================================================================
# FUNCIONES AUXILIARES PARA EL REPORTLAB PDF
# ==============================================================================
def generar_imagen_histograma_lineas(hist_dict):
    """Genera perfil de líneas independientes sin áreas opacas ni mezcla de colores."""
    fig, ax = plt.subplots(figsize=(7, 2.5))
    colores = ['#D32F2F', '#2E7D32', '#6A1B9A', '#E65100']
    estilos = ['-', '--', '-.', ':']
    
    for idx, (reg, pixeles) in enumerate(hist_dict.items()):
        if pixeles.size > 0:
            nombre_corto = reg.split('(')[0].strip()
            ax.hist(
                pixeles, 
                bins=256, 
                range=[0, 256], 
                histtype='step', 
                linewidth=1.8, 
                color=colores[idx % len(colores)], 
                linestyle=estilos[idx % len(estilos)],
                label=nombre_corto
            )

    ax.set_xlim([0, 255])
    ax.set_title("Distribución Comparativa de Ecointensidad Muscular (Líneas de Frecuencia)", fontsize=9, fontweight='bold')
    ax.set_xlabel("Escala de Grises (0 = Negro, 255 = Blanco)", fontsize=8)
    ax.set_ylabel("Frecuencia de Píxeles", fontsize=8)
    ax.tick_params(axis='both', which='major', labelsize=7)
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.legend(loc='upper right', fontsize=7.5, framealpha=0.9)
    plt.tight_layout()

    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png', dpi=200)
    img_buf.seek(0)
    plt.close(fig)
    return img_buf

def generar_pdf_clinico(datos_informe, hist_data, imgs_roi, imgs_hist, nombre_paciente, nombre_medico, n_colegiado, observaciones):
    """Genera informe en PDF que incluye mediciones, ecografías, histogramas e INFORMACIÓN CLÍNICA DERIVADA."""
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

    titulo_style = ParagraphStyle('TituloPDF', parent=styles['Heading1'], fontSize=14, leading=18, textColor=colors.HexColor('#003366'), spaceAfter=2)
    subtitulo_style = ParagraphStyle('SubtituloPDF', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#555555'), spaceAfter=8)
    seccion_style = ParagraphStyle('SeccionPDF', parent=styles['Heading2'], fontSize=10, leading=13, textColor=colors.HexColor('#003366'), spaceBefore=8, spaceAfter=4, fontName='Helvetica-Bold')
    body_style = ParagraphStyle('BodyPDF', parent=styles['Normal'], fontSize=8, leading=11, textColor=colors.HexColor('#222222'))
    header_tabla = ParagraphStyle('HeaderTabla', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.white, fontName='Helvetica-Bold')
    cell_style = ParagraphStyle('CellTabla', parent=styles['Normal'], fontSize=7.5, leading=9.5, textColor=colors.HexColor('#222222'))

    # ENCABEZADO
    story.append(Paragraph("INFORME ECOGRÁFICO DE VALORACIÓN NUTRICIONAL Y SARCOPENIA", titulo_style))
    story.append(Paragraph(f"Fecha de emisión: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Sistema: EcoSarcopenia Pro v2.0", subtitulo_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#003366'), spaceAfter=8))

    # DATOS DE PACIENTE Y EVALUADOR
    datos_paciente = [
        [Paragraph(f"<b>Paciente:</b> {nombre_paciente}", body_style), Paragraph(f"<b>Médico Evaluador:</b> {nombre_medico}", body_style)],
        [Paragraph(f"<b>Fecha Evaluación:</b> {datetime.now().strftime('%d/%m/%Y')}", body_style), Paragraph(f"<b>Nº Colegiado:</b> {n_colegiado}", body_style)]
    ]
    t_paciente = Table(datos_paciente, colWidths=[270, 270])
    t_paciente.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0F4F8')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC'))
    ]))
    story.append(t_paciente)
    story.append(Spacer(1, 8))

    # 1. RESUMEN DE MEDICIONES
    story.append(Paragraph("1. RESUMEN DE MEDICIONES ECOGRÁFICAS Y RATIOS", seccion_style))
    tabla_datos = [[
        Paragraph("<b>Región Anatómica Analizada</b>", header_tabla),
        Paragraph("<b>Ref. Subcutáneo</b>", header_tabla),
        Paragraph("<b>Tejido Objetivo</b>", header_tabla),
        Paragraph("<b>Ratio / Índice</b>", header_tabla),
        Paragraph("<b>Estado Clínico Ecoestructural</b>", header_tabla)
    ]]

    ratios_musculares = []
    hay_grasa_visceral = False
    indice_gva_gsa_val = 0.0

    for reg, vals in datos_informe.items():
        ratio = vals["Ratio"]
        tipo = vals["Tipo"]
        if tipo == "Correlación Abdominal":
            hay_grasa_visceral = True
            indice_gva_gsa_val = ratio
            eval_text = "<font color='red'><b>Predominio Visceral</b></font>" if ratio > 1.0 else "<font color='green'><b>Predominio Subcutáneo</b></font>"
            sub_val = f"{vals['Grasa']} px"
            obj_val = f"{vals['Músculo']} px"
        else:
            ratios_musculares.append(ratio)
            sub_val = f"{vals['Grasa']} EI"
            obj_val = f"{vals['Músculo']} EI"
            if ratio < 0.8:
                eval_text = "<font color='green'><b>Ecoestructura Normal</b></font>"
            elif ratio <= 1.2:
                eval_text = "<font color='orange'><b>Miosteatosis Moderada</b></font>"
            else:
                eval_text = "<font color='red'><b>Miosteatosis Severa / Fibrótica</b></font>"

        tabla_datos.append([
            Paragraph(reg.split('(')[0].strip(), cell_style),
            Paragraph(sub_val, cell_style),
            Paragraph(obj_val, cell_style),
            Paragraph(f"<b>{ratio}</b>", cell_style),
            Paragraph(eval_text, cell_style)
        ])

    t = Table(tabla_datos, colWidths=[150, 95, 95, 80, 120])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')])
    ]))
    story.append(t)
    story.append(Spacer(1, 8))

    # 2. INFORMACIÓN CLÍNICA DERIVADA Y EVALUACIÓN DE SARCOPENIA
    story.append(Paragraph("2. INFORMACIÓN CLÍNICA DERIVADA Y EVALUACIÓN DE SARCOPENIA", seccion_style))
    
    max_ratio = max(ratios_musculares) if ratios_musculares else 0.0

    p_sarcopenia = []
    if max_ratio > 1.2:
        p_sarcopenia.append("• <b>Calidad Muscular Alterada (Miosteatosis Avanzada):</b> El ratio M/S elevado refleja sustitución del tejido magro por infiltración adiposa intramuscular y/o fibrosis pericimicial, criterio ecográfico patognomónico de sarcopenia cualitativa.")
    elif max_ratio >= 0.8:
        p_sarcopenia.append("• <b>Infiltración Adiposa Moderada:</b> Presencia de ecoestratificación difusa con pérdida incipiente de la arquitectura en 'pluma de ave', compatible con miosteatosis grado I-II.")
    else:
        p_sarcopenia.append("• <b>Calidad Muscular Preservada:</b> Parénquima predominantemente hipoecoico con septos fibroadiposos finos y bien definidos, representativo de reserva proteica preservada.")

    if hay_grasa_visceral:
        if indice_gva_gsa_val > 1.0:
            p_sarcopenia.append(f"• <b>Perfil Adiposo Visceral (Índice GVA/GSA = {indice_gva_gsa_val}):</b> Indica acumulación adiposa en compartimento profundo/visceral, correlacionada clínicamente con resistencia a la insulina, inflamación sistémica de bajo grado y riesgo de 'obesidad sarcopénica'.")
        else:
            p_sarcopenia.append(f"• <b>Distribución Adiposa Subcutánea (Índice GVA/GSA = {indice_gva_gsa_val}):</b> Expansión lipídica predominantemente subcutánea sin sobrecarga visceral patológica significativa.")

    p_sarcopenia.append("• <b>Recomendación Multidisciplinar Derivada:</b> Integrar estos hallazgos con pruebas funcionales (fuerza de prensión manual / Grip Strength y velocidad de la marcha) para estadificación según consensos internacionales (EWGSOP2/ESPEN).")

    box_data = [[Paragraph("<br/>".join(p_sarcopenia), body_style)]]
    t_box = Table(box_data, colWidths=[540])
    t_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EBF5FB')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#2980B9')),
        ('PADDING', (0,0), (-1,-1), 6)
    ]))
    story.append(t_box)
    story.append(Spacer(1, 8))

    # 3. REGISTRO INDIVIDUAL DE ECOGRAFÍAS E HISTOGRAMAS
    story.append(Paragraph("3. REGISTRO INDIVIDUAL DE ECOGRAFÍAS E HISTOGRAMAS DE ROI", seccion_style))
    for reg_key in datos_informe.keys():
        reg_nombre = reg_key.split('(')[0].strip()
        story.append(Paragraph(f"<b>• {reg_nombre}</b>", ParagraphStyle('RegSub', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor('#003366'))))
        
        filas_img = []
        if reg_key in imgs_roi and imgs_roi[reg_key] is not None:
            filas_img.append(RLImage(imgs_roi[reg_key], width=250, height=140))
        if reg_key in imgs_hist and imgs_hist[reg_key] is not None:
            filas_img.append(RLImage(imgs_hist[reg_key], width=250, height=140))
        
        if len(filas_img) == 2:
            t_imgs = Table([[filas_img[0], filas_img[1]]], colWidths=[260, 260])
            t_imgs.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
            story.append(t_imgs)
        elif len(filas_img) == 1:
            story.append(filas_img[0])
            
        story.append(Spacer(1, 4))

    # 4. HISTOGRAMA COMPARATIVO GENERAL
    if hist_data:
        story.append(Paragraph("4. HISTOGRAMA COMPARATIVO GENERAL (LÍNEAS DE FRECUENCIA)", seccion_style))
        img_hist_buf = generar_imagen_histograma_lineas(hist_data)
        story.append(RLImage(img_hist_buf, width=520, height=155))
        story.append(Spacer(1, 8))

    # 5. OBSERVACIONES CLÍNICAS Y DIAGNÓSTICO
    story.append(Paragraph("5. IMPRESIÓN CLÍNICA Y RECOMENDACIONES", seccion_style))
    obs_texto = observaciones.strip() if observaciones.strip() else "Sin observaciones específicas adicionadas."
    story.append(Paragraph(f"<b>Diagnóstico / Juicio Clínico:</b> {obs_texto}", body_style))
    story.append(Spacer(1, 15))

    # FIRMA Y SELLO
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
# SECCIÓN FINAL: INFORME CLÍNICO CONSOLIDADO Y DESCARGA
# ==============================================================================
st.header("📋 INFORME CLÍNICO CONSOLIDADO")

if st.session_state.informe:
    st.markdown("### Resumen de Parámetros Analizados")
    
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

    st.subheader("📝 Datos del Informe y Firma Médica")
    col_p, col_m, col_c = st.columns(3)
    with col_p:
        nombre_pac = st.text_input("👤 Paciente:", value="Paciente Anónimo")
    with col_m:
        nombre_med = st.text_input("🩺 Médico Evaluador:", value="Dr. / Dra.")
    with col_c:
        num_col = st.text_input("🆔 Nº Colegiado:", value="123456")

    obs_clinicas = st.text_area(
        "💬 Observaciones Clínicas / Juicio Diagnóstico:",
        placeholder="Escribe aquí las recomendaciones de nutrición clínica, plan de ejercicio o seguimiento..."
    )

    st.markdown("---")

    pdf_bytes = generar_pdf_clinico(
        st.session_state.informe,
        st.session_state.hist_data,
        st.session_state.imagenes_roi,
        st.session_state.imagenes_hist_indiv,
        nombre_paciente=nombre_pac,
        nombre_medico=nombre_med,
        n_colegiado=num_col,
        observaciones=obs_clinicas
    )
    
    st.download_button(
        label="📄 DESCARGAR INFORME CLÍNICO COMPLETO (PDF)",
        data=pdf_bytes,
        file_name=f"Informe_EcoSarcopenia_{nombre_pac.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True
    )

else:
    st.info("💡 Realiza y guarda al menos una medición para habilitar el informe y la descarga en PDF.")
