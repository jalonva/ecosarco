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
st.markdown("Herramienta de análisis automatizado con escala bidimensional HD de alta visibilidad.")

st.markdown("---")

# Inicializar estado de sesión
if "informe" not in st.session_state:
    st.session_state.informe = {}

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
        # CÁLCULO DINÁMICO DE TAMAÑO DE TEXTO Y TRAZO SEGÚN RESOLUCIÓN
        # ==============================================================================
        # Ajusta el tamaño de la letra y líneas proporcionalmente a la resolución
        font_scale = max(0.8, h / 400.0)      # Tamaño de fuente grande y legible
        thickness = max(2, int(h / 300.0))     # Grosor de la línea del texto
        tick_len_y = int(w * 0.05)             # Longitud de marcas Y (5% del ancho)
        tick_len_x = int(h * 0.05)             # Longitud de marcas X (5% de la altura)

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

            # ------------------------------------------------------------------
            # 📐 ESCALAS VISUALES HD (EJE Y Y EJE X)
            # ------------------------------------------------------------------
            paso_y = max(50, int(h / 8))
            for y_mark in range(0, h, paso_y):
                # Regla Vertical Y
                cv2.line(img_color, (0, y_mark), (tick_len_y, y_mark), (0, 255, 255), thickness)
                cv2.putText(img_color, f"{y_mark}", (tick_len_y + 8, y_mark + int(10 * font_scale)), 
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 255), thickness, cv2.LINE_AA)

            paso_x = max(80, int(w / 8))
            for x_mark in range(0, w, paso_x):
                # Regla Horizontal X
                cv2.line(img_color, (x_mark, h - 1), (x_mark, h - tick_len_x), (0, 255, 255), thickness)
                cv2.putText(img_color, f"{x_mark}", (x_mark - int(20 * font_scale), h - tick_len_x - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 255), thickness, cv2.LINE_AA)

            # Capas de grasa delimitadas
            cv2.rectangle(img_color, (int(w*0.25), gsa_y[0]), (int(w*0.75), gsa_y[1]), (0, 255, 0), thickness)
            cv2.rectangle(img_color, (int(w*0.25), gva_y[0]), (int(w*0.75), gva_y[1]), (0, 0, 255), thickness)

            st.image(img_color, channels="BGR", use_container_width=True)

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
                    "GSA_px": espesor_gsa,
                    "GVA_px": espesor_gva,
                    "Ratio": round(indice_correlacion, 2),
                    "Tipo": "Correlación Abdominal"
                }
                st.success("✅ Índice de correlación abdominal guardado en el informe.")

        # ==============================================================================
        # OPCIÓN B: ECOINTENSIDAD MUSCULAR (ROIs + DOBLE ESCALA HD)
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

            # ------------------------------------------------------------------
            # 📐 ESCALAS VISUALES HD (EJE Y Y EJE X)
            # ------------------------------------------------------------------
            paso_y = max(50, int(h / 8))
            for y_mark in range(0, h, paso_y):
                # Regla Vertical Y
                cv2.line(img_color, (0, y_mark), (tick_len_y, y_mark), (0, 255, 255), thickness)
                cv2.putText(img_color, f"{y_mark}", (tick_len_y + 8, y_mark + int(10 * font_scale)), 
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 255), thickness, cv2.LINE_AA)

            paso_x = max(80, int(w / 8))
            for x_mark in range(0, w, paso_x):
                # Regla Horizontal X
                cv2.line(img_color, (x_mark, h - 1), (x_mark, h - tick_len_x), (0, 255, 255), thickness)
                cv2.putText(img_color, f"{x_mark}", (x_mark - int(20 * font_scale), h - tick_len_x - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 255), thickness, cv2.LINE_AA)

            # Dibujar ROIs
            cv2.rectangle(img_color, (sub_x[0], sub_y[0]), (sub_x[1], sub_y[1]), (255, 0, 0), thickness)
            cv2.rectangle(img_color, (mus_x[0], mus_y[0]), (mus_x[1], mus_y[1]), (0, 0, 255), thickness)

            st.image(img_color, channels="BGR", use_container_width=True)

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
# INFORME Y GENERADOR PDF
# ==============================================================================
st.header("📋 INFORME CLÍNICO CONSOLIDADO")

if st.session_state.informe:
    st.write("Resumen de parámetros analizados:", st.session_state.informe)
else:
    st.info("Sube una imagen para comenzar la evaluación.")

            
