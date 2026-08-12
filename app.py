import streamlit as st
import cv2
import numpy as np
import matplotlib.pyplot as plt

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

    st.subheader("🖼️ Ajuste de Regiones de Interés (ROIs)")

    # Controles deslizantes con información de escala
    col_sub, col_mus = st.columns(2)
    with col_sub:
        st.write(f"🔴 **Grasa Subcutánea** *(Dimensión total Y:{h}px, X:{w}px)*")
        sub_y = st.slider("Profundidad Y (Grasa)", 0, h, (int(h*0.1), int(h*0.3)), key=f"sub_y_{region}")
        sub_x = st.slider("Anchura X (Grasa)", 0, w, (int(w*0.1), int(w*0.9)), key=f"sub_x_{region}")
    
    with col_mus:
        st.write(f"🔵 **Músculo / Profundo** *(Dimensión total Y:{h}px, X:{w}px)*")
        mus_y = st.slider("Profundidad Y (Músculo)", 0, h, (int(h*0.4), int(h*0.7)), key=f"mus_y_{region}")
        mus_x = st.slider("Anchura X (Músculo)", 0, w, (int(w*0.1), int(w*0.9)), key=f"mus_x_{region}")

    # DIBUJAR RECUADROS Y TEXTO DIRECTO SOBRE LA IMAGEN
    img_color = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)
    
    # Recuadro Grasa (Rojo)
    cv2.rectangle(img_color, (sub_x[0], sub_y[0]), (sub_x[1], sub_y[1]), (255, 0, 0), 2)
    cv2.putText(img_color, f"Grasa Y:{sub_y[0]}-{sub_y[1]}", (sub_x[0], max(20, sub_y[0]-5)), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    # Recuadro Músculo (Azul)
    cv2.rectangle(img_color, (mus_x[0], mus_y[0]), (mus_x[1], mus_y[1]), (0, 0, 255), 2)
    cv2.putText(img_color, f"Musculo Y:{mus_y[0]}-{mus_y[1]}", (mus_x[0], max(20, mus_y[0]-5)), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    # Mostrar la imagen ecográfica limpia a tamaño completo
    st.image(img_color, channels="BGR", use_container_width=True)

    # Cálculos
    sub_crop = img_gray[sub_y[0]:sub_y[1], sub_x[0]:sub_x[1]]
    mus_crop = img_gray[mus_y[0]:mus_y[1], mus_x[0]:mus_x[1]]

    mean_sub = np.mean(sub_crop) if sub_crop.size > 0 else 0.0
    mean_mus = np.mean(mus_crop) if mus_crop.size > 0 else 0.0
    ratio = (mean_mus / mean_sub) if mean_sub > 0 else 0.0

    st.markdown("---")

    # Resultados puntuales
    st.subheader("📊 Resultados de esta Toma")
    c1, c2, c3 = st.columns(3)
    c1.metric("Grasa Subcutánea (EI)", f"{mean_sub:.1f}")
    c2.metric("Músculo / Profundo (EI)", f"{mean_mus:.1f}")
    c3.metric("Ratio M/S", f"{ratio:.2f}")

    if st.button("💾 Guardar esta medición en el Informe Final"):
        st.session_state.informe[region] = {
            "Grasa": round(mean_sub, 1),
            "Músculo": round(mean_mus, 1),
            "Ratio": round(ratio, 2)
        }
        st.success(f"✅ Medición de **{region}** guardada correctamente.")

    st.markdown("---")

    # HISTOGRAMA INDEPENDIENTE
    st.subheader("📈 Histograma de Ecogenicidad")
    fig, ax = plt.subplots(figsize=(7, 3))
    if sub_crop.size > 0:
        ax.hist(sub_crop.ravel(), bins=256, range=[0, 256], color='red', alpha=0.5, label=f'Grasa ({mean_sub:.1f})')
    if mus_crop.size > 0:
        ax.hist(mus_crop.ravel(), bins=256, range=[0, 256], color='blue', alpha=0.5, label=f'Músculo ({mean_mus:.1f})')
    ax.set_xlim([0, 255])
    ax.set_xlabel("Escala de Grises (0 = Negro, 255 = Blanco)")
    ax.set_ylabel("Frecuencia de Píxeles")
    ax.legend(loc='upper right')
    st.pyplot(fig)

st.markdown("---")

# SECCIÓN DEL INFORME CONSOLIDADO
st.header("📋 INFORME CLÍNICO CONSOLIDADO")

if st.session_state.informe:
    tabla_datos = []
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

    if st.button("🗑️ Limpiar datos y comenzar nuevo paciente"):
        st.session_state.informe = {}
        st.rerun()

else:
    st.info("Aún no has guardado ninguna medición. Selecciona un músculo arriba y pulsa 'Guardar esta medición'.")
