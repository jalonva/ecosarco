import streamlit as st
import cv2
import numpy as np
import matplotlib.pyplot as plt

# Configuración de página
st.set_page_config(page_title="EcoSarcopenia Pro - Informe Clínico", layout="centered")

st.title("🩺 Valoración Ecográfica Nutricional")
st.markdown("Herramienta de cuantificación rápida y generación de informe clínico consolidado.")

st.markdown("---")

# Inicializar el estado de la sesión para guardar mediciones
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

    st.subheader("🖼️ Ajuste de Regiones (ROIs)")
    img_color = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)

    # Controles
    col_sub, col_mus = st.columns(2)
    with col_sub:
        st.write("🔴 **Tejido Subcutáneo (Grasa)**")
        sub_y = st.slider("Posición Y (Grasa)", 0, h, (int(h*0.1), int(h*0.3)), key=f"sub_y_{region}")
        sub_x = st.slider("Posición X (Grasa)", 0, w, (int(w*0.2), int(w*0.8)), key=f"sub_x_{region}")
    
    with col_mus:
        st.write("🔵 **Tejido Muscular / Profundo**")
        mus_y = st.slider("Posición Y (Músculo/Visceral)", 0, h, (int(h*0.5), int(h*0.8)), key=f"mus_y_{region}")
        mus_x = st.slider("Posición X (Músculo/Visceral)", 0, w, (int(w*0.2), int(w*0.8)), key=f"mus_x_{region}")

    # Dibujar recuadros
    cv2.rectangle(img_color, (sub_x[0], sub_y[0]), (sub_x[1], sub_y[1]), (255, 0, 0), 3)
    cv2.rectangle(img_color, (mus_x[0], mus_y[0]), (mus_x[1], mus_y[1]), (0, 0, 255), 3)

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
    c1.metric("Grasa Subcutánea", f"{mean_sub:.1f}")
    c2.metric("Músculo / Profundo", f"{mean_mus:.1f}")
    c3.metric("Ratio M/S", f"{ratio:.2f}")

    # Botón para guardar medición en el informe
    if st.button("💾 Guardar esta medición en el Informe Final"):
        st.session_state.informe[region] = {
            "Grasa": round(mean_sub, 1),
            "Músculo": round(mean_mus, 1),
            "Ratio": round(ratio, 2)
        }
        st.success(f"✅ Medición de **{region}** guardada correctamente en el informe.")

st.markdown("---")

# 3. SECCIÓN DEL INFORME FINAL ACUMULADO
st.header("📋 INFORME CLÍNICO CONSOLIDADO")

if st.session_state.informe:
    st.write("### Resumen de Regiones Evaluadas:")
    
    # Crear una tabla visual de resumen
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

    # Conclusión Diagnóstica Global Automática
    st.subheader("💡 Orientación Diagnóstica Global")
    
    ratios_elevados = sum(1 for d in st.session_state.informe.values() if d["Ratio"] >= 0.7)
    total_medidos = len(st.session_state.informe)
    
    if ratios_elevados == 0:
        st.success("✅ **Ecosarcopenia Negativa:** Calidad muscular y distribución grasa adecuadamente conservadas en todas las regiones evaluadas.")
    elif ratios_elevados == total_medidos:
        st.error("🚨 **Sarcopenia / Miosteatosis Generalizada:** Elevada eco-intensidad generalizada. Se sugiere intervención nutricional y de ejercicio de fuerza.")
    else:
        st.warning("⚠️ **Afectación Muscular Regional / Focal:** Existen áreas con sospecha de infiltración grasa o atrofia. Revisar los puntos marcados como 'Moderado' o 'Elevado'.")

    # Botón para reiniciar para el siguiente paciente
    if st.button("🗑️ Limpiar datos y comenzar nuevo paciente"):
        st.session_state.informe = {}
        st.rerun()

else:
    st.info("Aún no has guardado ninguna medición. Selecciona un músculo arriba, ajusta la toma y pulsa 'Guardar esta medición en el Informe Final'.")
   
