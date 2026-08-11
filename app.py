import streamlit as st
import cv2
import numpy as np
import matplotlib.pyplot as plt

# Configuración de la página
st.set_page_config(
    page_title="Miocuantificación por Ecografía",
    page_icon="🩺",
    layout="wide"
)

# Estilo personalizado CSS
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

st.title("🩺 Análisis de Ecogenicidad Muscular y Subcutánea")
st.subheader("Herramienta de Cuantificación para Estimación de Calidad Muscular")

st.markdown("---")

# Cargar imagen en el panel lateral
uploaded_file = st.sidebar.file_uploader("Cargar Ecografía (PNG, JPG)", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # Leer la imagen
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img_gray = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
    h, w = img_gray.shape

    st.sidebar.header("📐 Selección de ROIs")
    
    # Controles para ROI Subcutánea
    st.sidebar.subheader("Grasa Subcutánea (Roja)")
    sub_y = st.sidebar.slider("Posición Y (Subcutáneo)", 0, h, (int(h*0.1), int(h*0.3)))
    sub_x = st.sidebar.slider("Posición X (Subcutáneo)", 0, w, (int(w*0.2), int(w*0.8)))

    # Controles para ROI Muscular
    st.sidebar.subheader("Vientre Muscular (Azul)")
    mus_y = st.sidebar.slider("Posición Y (Músculo)", 0, h, (int(h*0.5), int(h*0.8)))
    mus_x = st.sidebar.slider("Posición X (Músculo)", 0, w, (int(w*0.2), int(w*0.8)))

    # Extraer recortes
    sub_crop = img_gray[sub_y[0]:sub_y[1], sub_x[0]:sub_x[1]]
    mus_crop = img_gray[mus_y[0]:mus_y[1], mus_x[0]:mus_x[1]]

    # Cálculos estadísticos
    mean_sub = np.mean(sub_crop) if sub_crop.size > 0 else 0.0
    std_sub = np.std(sub_crop) if sub_crop.size > 0 else 0.0
    
    mean_mus = np.mean(mus_crop) if mus_crop.size > 0 else 0.0
    std_mus = np.std(mus_crop) if mus_crop.size > 0 else 0.0

    ratio_ms = (mean_mus / mean_sub) if mean_sub > 0 else 0.0

    # Panel de métricas
    col1, col2, col3 = st.columns(3)
    col1.metric("Grasa Subcutánea (EI)", f"{mean_sub:.1f}", f"Std: ±{std_sub:.1f}")
    col2.metric("Vientre Muscular (EI)", f"{mean_mus:.1f}", f"Std: ±{std_mus:.1f}")
    
    # Estado de la relación M/S
    delta_color = "normal" if ratio_ms < 0.7 else "inverse"
    col3.metric("Ratio Músculo / Subcutáneo", f"{ratio_ms:.2f}", 
                "Normal (< 0.70)" if ratio_ms < 0.7 else "Elevado (Posible infiltración)", 
                delta_color=delta_color)

    st.markdown("---")

    # Visualización gráfica
    col_left, col_right = st.columns(2)

    with col_left:
        st.write("### 🖼️ Imagen con Regiones de Interés (ROIs)")
        img_color = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)
        
        # Dibujar rectángulos
        cv2.rectangle(img_color, (sub_x[0], sub_y[0]), (sub_x[1], sub_y[1]), (255, 0, 0), 2)
        cv2.rectangle(img_color, (mus_x[0], mus_y[0]), (mus_x[1], mus_y[1]), (0, 0, 255), 2)
        
        st.image(img_color, channels="BGR", use_container_width=True)

    with col_right:
        st.write("### 📊 Histogramas de Ecogenicidad")
        fig, ax = plt.subplots(figsize=(6, 4))
        if sub_crop.size > 0:
            ax.hist(sub_crop.ravel(), bins=256, range=[0, 256], color='red', alpha=0.5, label=f'Subcutáneo ({mean_sub:.1f})')
        if mus_crop.size > 0:
            ax.hist(mus_crop.ravel(), bins=256, range=[0, 256], color='blue', alpha=0.5, label=f'Músculo ({mean_mus:.1f})')
        
        ax.set_xlim([0, 255])
        ax.set_xlabel("Escala de Grises (0 = Negro, 255 = Blanco)")
        ax.set_ylabel("Frecuencia de Píxeles")
        ax.legend(loc='upper right')
        st.pyplot(fig)

else:
    st.info("👈 Para comenzar, despliega la barra lateral e ingresa una imagen ecográfica.")
