import streamlit as st
import cv2
import numpy as np
import matplotlib.pyplot as plt

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
# SECCIÓN DEL INFORME CLÍNICO CONSOLIDADO (SUMARIO Y MEDIAS GLOBAL)
# ==============================================================================
st.header("📋 INFORME CLÍNICO CONSOLIDADO")

if st.session_state.informe:
    # 1. TABLA RESUMEN POR ZONAS
    st.subheader("📌 Desglose por Región Anatómica")
    tabla_datos = []
    
    # Listas para calcular promedios globales (excluyendo la prueba de grasa visceral pura si no es muscular)
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

    # 2. SUMARIO EJECUTIVO CON MEDIAS GLOBALES CORPORALES
    st.subheader("📊 SUMARIO GLOBAL CORPORAL (Promedio de Músculos)")
    if musculares:
        avg_sub = np.mean([d["Grasa"] for d in musculares])
        avg_mus = np.mean([d["Músculo"] for d in musculares])
        avg_ratio = np.mean([d["Ratio"] for d in musculares])

        col_g1, col_g2, col_g3 = st.columns(3)
        col_g1.metric("Media Grasa Subcutánea", f"{avg_sub:.1f}")
        col_g2.metric("Media Ecogenicidad Muscular", f"{avg_mus:.1f}")
        
        diag_global_text = "Calidad Global Conservada" if avg_ratio < 0.7 else ("Infiltración Leve/Mod." if avg_ratio < 1.0 else "Sarcopenia/Miosteatosis Severa")
        col_g3.metric("Ratio M/S Global Promedio", f"{avg_ratio:.2f}", diag_global_text)

        # Conclusión Diagnóstica
        if avg_ratio < 0.7:
            st.success(f"✅ **Ecosarcopenia Negativa (Score Global: {avg_ratio:.2f}):** El promedio de los músculos evaluados muestra una masa y calidad muscular globalmente bien conservadas.")
        elif 0.7 <= avg_ratio < 1.0:
            st.warning(f"⚠️ **Infiltración Grasa / Sarcopenia Inicial (Score Global: {avg_ratio:.2f}):** Ligero o moderado aumento global en la ecogenicidad muscular. Se sugiere intervención preventiva.")
        else:
            st.error(f"🚨 **Miosteatosis / Atrofia Severa Global (Score Global: {avg_ratio:.2f}):** Elevada reflectividad generalizada. Indicación clara de tratamiento nutricional y ejercicio prescriptivo.")

    # 3. GALERÍA DE HISTOGRAMAS EN EL INFORME
    st.subheader("📈 Galería Comparativa de Histogramas")
    cols_hist = st.columns(len(st.session_state.informe))
    for idx, (reg, datos) in enumerate(st.session_state.informe.items()):
        with cols_hist[idx]:
            st.caption(f"**{reg.split('(')[0]}**")
            fig_h, ax_h = plt.subplots(figsize=(3.5, 2.5))
            if datos["sub_crop"].size > 0:
                ax_h.hist(datos["sub_crop"].ravel(), bins=256, range=[0, 256], color='red', alpha=0.5)
            if datos["mus_crop"].size > 0:
                ax_h.hist(datos["mus_crop"].ravel(), bins=256, range=[0, 256], color='blue', alpha=0.5)
            ax_h.set_xlim([0, 255])
            ax_h.tick_params(labelsize=6)
            st.pyplot(fig_h)

    st.write("")
    if st.button("🗑️ Limpiar datos y comenzar nuevo paciente", use_container_width=True):
        st.session_state.informe = {}
        st.rerun()

else:
    st.info("Aún no has guardado ninguna medición. Selecciona un músculo arriba, ajusta la toma y pulsa 'GUARDAR MEDICIÓN EN INFORME FINAL'.")
