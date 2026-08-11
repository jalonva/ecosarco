import streamlit as st
import cv2
import numpy as np
import matplotlib.pyplot as plt

# Configuración de página
st.set_page_config(page_title="Ecografía Pro", layout="centered")

st.title("🩺 Análisis Ecográfico")

# 1. Carga de archivo (esto siempre debe ir primero)
uploaded_file = st.file_uploader("Sube tu ecografía aquí", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # Procesar imagen
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img_gray = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
    h, w = img_gray.shape

    # --- CONTROLES DE AJUSTE ---
    st.subheader("⚙️ Ajuste de Regiones (ROIs)")
    
    col_sub, col_mus = st.columns(2)
    
    with col_sub:
        st.write("🔴 **Grasa Subcutánea**")
        sub_y = st.slider("Altura Y", 0, h, (int(h*0.1), int(h*0.3)), key="sub_y")
        sub_x = st.slider("Ancho X", 0, w, (int(w*0.2), int(w*0.8)), key="sub_x")
    
    with col_mus:
        st.write("🔵 **Músculo**")
        mus_y = st.slider("Altura Y", 0, h, (int(h*0.5), int(h*0.8)), key="mus_y")
        mus_x = st.slider("Ancho X", 0, w, (int(w*0.2), int(w*0.8)), key="mus_x")

    # --- VISUALIZACIÓN ---
    st.write("---")
    st.subheader("🖼️ Vista Previa")
    
    img_color = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)
    
    # Dibujar recuadros
    cv2.rectangle(img_color, (sub_x[0], sub_y[0]), (sub_x[1], sub_y[1]), (255, 0, 0), 3) # Rojo
    cv2.rectangle(img_color, (mus_x[0], mus_y[0]), (mus_x[1], mus_y[1]), (0, 0, 255), 3) # Azul
    
    st.image(img_color, channels="BGR", use_container_width=True)

    # --- RESULTADOS ---
    sub_crop = img_gray[sub_y[0]:sub_y[1], sub_x[0]:sub_x[1]]
    mus_crop = img_gray[mus_y[0]:mus_y[1], mus_x[0]:mus_x[1]]
    
    mean_sub = np.mean(sub_crop) if sub_crop.size > 0 else 0
    mean_mus = np.mean(mus_crop) if mus_crop.size > 0 else 0
    ratio = (mean_mus / mean_sub) if mean_sub > 0 else 0

    st.write("---")
    st.subheader("📊 Resultados")
    c1, c2, c3 = st.columns(3)
    c1.metric("Grasa", f"{mean_sub:.1f}")
    c2.metric("Músculo", f"{mean_mus:.1f}")
    c3.metric("Ratio M/S", f"{ratio:.2f}")

else:
    st.info("👆 Por favor, sube una imagen para comenzar el análisis.")
