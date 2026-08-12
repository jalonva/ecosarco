import streamlit as st
import cv2
import numpy as np
import matplotlib.pyplot as plt

# Configuración de página
st.set_page_config(page_title="EcoSarcopenia Pro", layout="centered")

st.title("🩺 Ecografía Nutricional y Sarcopenia")
st.markdown("Herramienta de cuantificación rápida para consulta sin desvestir al paciente.")

st.markdown("---")

# 1. Selector de Región Anatómica
region = st.selectbox(
    "📌 Selecciona la región / músculo a analizar:",
    [
        "🦾 Bíceps Braquial (Miembro Superior)",
        "🦵 Tibial Anterior (Miembro Inferior)",
        "🧱 Recto Abdominal (Músculo Central)",
        "🫄 Estudio de Distribución de Grasa (Abdominal)"
    ]
)

st.markdown("---")

# 2. Carga de archivo
uploaded_file = st.file_uploader(f"📂 Sube la ecografía para: {region}", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # Leer la imagen
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img_gray = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
    h, w = img_gray.shape

    st.subheader("🖼️ Ajuste de Regiones (ROIs)")
    
    img_color = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)

    # 3. Controles
    col_sub, col_mus = st.columns(2)
    
    with col_sub:
        st.write("🔴 **Tejido Subcutáneo (Grasa)**")
        sub_y = st.slider("Posición Y (Grasa)", 0, h, (int(h*0.1), int(h*0.3)), key="sub_y")
        sub_x = st.slider("Posición X (Grasa)", 0, w, (int(w*0.2), int(w*0.8)), key="sub_x")
    
    with col_mus:
        st.write("🔵 **Tejido Muscular / Profundo**")
        mus_y = st.slider("Posición Y (Músculo/Visceral)", 0, h, (int(h*0.5), int(h*0.8)), key="mus_y")
        mus_x = st.slider("Posición X (Músculo/Visceral)", 0, w, (int(w*0.2), int(w*0.8)), key="mus_x")

    # Dibujar recuadros
    cv2.rectangle(img_color, (sub_x[0], sub_y[0]), (sub_x[1], sub_y[1]), (255, 0, 0), 3) # Rojo
    cv2.rectangle(img_color, (mus_x[0], mus_y[0]), (mus_x[1], mus_y[1]), (0, 0, 255), 3) # Azul

    # Imagen principal
    st.image(img_color, channels="BGR", use_container_width=True)

    # 4. Cálculos
    sub_crop = img_gray[sub_y[0]:sub_y[1], sub_x[0]:sub_x[1]]
    mus_crop = img_gray[mus_y[0]:mus_y[1], mus_x[0]:mus_x[1]]

    mean_sub = np.mean(sub_crop) if sub_crop.size > 0 else 0.0
    std_sub = np.std(sub_crop) if sub_crop.size > 0 else 0.0
    
    mean_mus = np.mean(mus_crop) if mus_crop.size > 0 else 0.0
    std_mus = np.std(mus_crop) if mus_crop.size > 0 else 0.0

    ratio = (mean_mus / mean_sub) if mean_sub > 0 else 0.0

    st.markdown("---")

    # 5. Métricas y Diagnósticos adaptados según la selección
    st.subheader("📊 Resultados del Análisis")
    c1, c2, c3 = st.columns(3)
    c1.metric("Grasa Subcutánea (EI)", f"{mean_sub:.1f}", f"±{std_sub:.1f}")
    c2.metric("Músculo / Zona Profunda (EI)", f"{mean_mus:.1f}", f"±{std_mus:.1f}")
    
    delta_text = "Normal (< 0.70)" if ratio < 0.7 else "Elevado (Infiltración)"
    delta_color = "normal" if ratio < 0.7 else "inverse"
    c3.metric("Ratio Músculo / Subcutáneo", f"{ratio:.2f}", delta_text, delta_color=delta_color)

    st.subheader("📋 Interpretación Clínica Específica")
    
    if "Grasa" in region:
        if ratio > 0.8:
            st.error("⚠️ **Patrón Metabólico / Inflamatorio:** Elevada reflectividad profunda. Alta sospecha de mayor componente de grasa visceral/infiltración adiposa profunda.")
        else:
            st.success("✅ **Distribución Grasa Predominantemente Subcutánea:** Menor componente proinflamatorio profundo.")
    else:
        if ratio < 0.7:
            st.success(f"✅ **Ecogenicidad en {region.split('(')[0]} Conservada:** Buena calidad muscular, sin signos cuantitativos de miosteatosis o sustitución fibrosa.")
        elif 0.7 <= ratio < 1.0:
            st.warning(f"⚠️ **Infiltración Leve/Moderada en {region.split('(')[0]}:** Posible pérdida de calidad muscular o sarcopenia inicial.")
        else:
            st.error(f"🚨 **Ecogenicidad Severamente Elevada en {region.split('(')[0]}:** Alta miosteatosis o atrofia avanzada.")

    st.markdown("---")

    # 6. Histograma
    st.subheader("📈 Histograma de Ecogenicidad")
    fig, ax = plt.subplots(figsize=(7, 3))
    if sub_crop.size > 0:
        ax.hist(sub_crop.ravel(), bins=256, range=[0, 256], color='red', alpha=0.5, label=f'Grasa ({mean_sub:.1f})')
    if mus_crop.size > 0:
        ax.hist(mus_crop.ravel(), bins=256, range=[0, 256], color='blue', alpha=0.5, label=f'Músculo ({mean_mus:.1f})')
    ax.set_xlim([0, 255])
    ax.set_xlabel("Escala de Grises (0 = Negro, 255 = Blanco)")
    ax.set_ylabel("Frecuencia")
    ax.legend(loc='upper right')
    st.pyplot(fig)

else:
    st.info("👆 Selecciona el apartado y sube la ecografía para comenzar.")
