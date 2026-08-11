import streamlit as st
import cv2
import numpy as np
import matplotlib.pyplot as plt

# Configuración de página
st.set_page_config(page_title="Ecografía Pro", layout="centered")

st.title("🩺 Análisis de Ecogenicidad Muscular")
st.markdown("Herramienta visual para estimar la calidad del tejido muscular mediante la relación Músculo / Subcutáneo.")

st.markdown("---")

# 1. Cargar imagen directamente en el cuerpo principal
uploaded_file = st.file_uploader("📂 Sube la ecografía a analizar", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # Leer la imagen
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img_gray = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
    h, w = img_gray.shape

    # 2. Visualización Principal de la Imagen
    st.subheader("🖼️ Vista de la Imagen y Selección")
    
    # Preparamos la imagen a color para dibujar
    img_color = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)

    # 3. Controles en columnas bien visibles justo al lado / debajo
    st.markdown("##### ⚙️ Ajusta las regiones a medir:")
    col_sub, col_mus = st.columns(2)
    
    with col_sub:
        st.write("🔴 **Grasa Subcutánea**")
        sub_y = st.slider("Posición Y (Subcutáneo)", 0, h, (int(h*0.1), int(h*0.3)), key="sub_y")
        sub_x = st.slider("Posición X (Subcutáneo)", 0, w, (int(w*0.2), int(w*0.8)), key="sub_x")
    
    with col_mus:
        st.write("🔵 **Vientre Muscular**")
        mus_y = st.slider("Posición Y (Músculo)", 0, h, (int(h*0.5), int(h*0.8)), key="mus_y")
        mus_x = st.slider("Posición X (Músculo)", 0, w, (int(w*0.2), int(w*0.8)), key="mus_x")

    # Dibujar rectángulos en vivo
    cv2.rectangle(img_color, (sub_x[0], sub_y[0]), (sub_x[1], sub_y[1]), (255, 0, 0), 3) # Rojo
    cv2.rectangle(img_color, (mus_x[0], mus_y[0]), (mus_x[1], mus_y[1]), (0, 0, 255), 3) # Azul

    # Mostrar la imagen
    st.image(img_color, channels="BGR", use_container_width=True)

    # 4. Cálculos Estadísticos
    sub_crop = img_gray[sub_y[0]:sub_y[1], sub_x[0]:sub_x[1]]
    mus_crop = img_gray[mus_y[0]:mus_y[1], mus_x[0]:mus_x[1]]

    mean_sub = np.mean(sub_crop) if sub_crop.size > 0 else 0.0
    std_sub = np.std(sub_crop) if sub_crop.size > 0 else 0.0
    
    mean_mus = np.mean(mus_crop) if mus_crop.size > 0 else 0.0
    std_mus = np.std(mus_crop) if mus_crop.size > 0 else 0.0

    ratio = (mean_mus / mean_sub) if mean_sub > 0 else 0.0

    st.markdown("---")

    # 5. Métricas de Resultados
    st.subheader("📊 Cuantificación de Ecogenicidad")
    c1, c2, c3 = st.columns(3)
    c1.metric("Grasa Subcutánea (EI)", f"{mean_sub:.1f}", f"±{std_sub:.1f}")
    c2.metric("Vientre Muscular (EI)", f"{mean_mus:.1f}", f"±{std_mus:.1f}")
    
    # Definir el estado clínico para la tarjeta
    delta_text = "Normal (< 0.70)" if ratio < 0.7 else "Elevado (Infiltración)"
    delta_color = "normal" if ratio < 0.7 else "inverse"
    c3.metric("Ratio Músculo / Subcutáneo", f"{ratio:.2f}", delta_text, delta_color=delta_color)

    # 6. Conclusión e Interpretación Clínica
    st.subheader("📋 Conclusión Clínica")
    if ratio < 0.7:
        st.success("""
        **Calidad Muscular Conservada:**
        * La ecogenicidad del músculo se mantiene baja en relación con la grasa subcutánea.
        * No hay evidencia visual ni cuantitativa significativa de infiltración miosteatósica o fibrosa.
        """)
    elif 0.7 <= ratio < 1.0:
        st.warning("""
        **Infiltración Grasa / Fibrosa Leve o Moderada:**
        * Se observa aumento en la intesidad de eco del vientre muscular.
        * Sugiere posible miosteatosis leve-moderada o pérdida de masa muscular (sarcopenia inicial).
        """)
    else:
        st.error("""
        **Ecogenicidad Muscular Severamente Elevada (M/S ≥ 1.0):**
        * El músculo presenta una reflectividad similar o superior a la de la grasa subcutánea.
        * Alta sospecha de infiltración miosteatósica avanzada, sustitución fibrosa o miopatía.
        """)

    st.markdown("---")

    # 7. Histogramas de Distribución
    st.subheader("📈 Histograma de Frecuencia de Grises")
    fig, ax = plt.subplots(figsize=(7, 3.5))
    
    if sub_crop.size > 0:
        ax.hist(sub_crop.ravel(), bins=256, range=[0, 256], color='red', alpha=0.5, label=f'Grasa (Media: {mean_sub:.1f})')
    if mus_crop.size > 0:
        ax.hist(mus_crop.ravel(), bins=256, range=[0, 256], color='blue', alpha=0.5, label=f'Músculo (Media: {mean_mus:.1f})')
    
    ax.set_xlim([0, 255])
    ax.set_xlabel("Escala de Grises (0 = Negro, 255 = Blanco)")
    ax.set_ylabel("Nº de Píxeles")
    ax.legend(loc='upper right')
    st.pyplot(fig)

else:
    st.info("👆 Para comenzar, sube una imagen ecográfica utilizando el botón de arriba.")
