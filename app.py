import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import fitz  # PyMuPDF
import json
import io

# Configuración de la página
st.set_page_config(page_title="Lector Tiquetes Energizar", page_icon="✈️", layout="centered")

st.title("✈️ Lector de Tiquetes Energizar")
st.write("Sube imágenes o archivos PDF para extraer datos a Excel.")

# Obtener la API Key desde los Secrets de Streamlit
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ No se encontró la API Key en los Secrets de Streamlit. Configúrala en Settings > Secrets.")

COLUMNAS = [
    "N° tiquete", 
    "cliente", 
    "matrícula", 
    "n° de vuelo", 
    "Destino", 
    "país", 
    "hora de inicio", 
    "hora final", 
    "galones entregados", 
    "Temp", 
    "API °60"
]

def extraer_datos(imagen, model):
    prompt = """
    Analiza este comprobante de entrega de combustible de aviación (Energizar Aviación).
    Extrae la información exacta y devuélvela estrictamente en formato JSON válido, sin ningún texto adicional ni formato markdown:

    {
      "N° tiquete": "Número que aparece al lado de MDE N°",
      "cliente": "Nombre del cliente",
      "matrícula": "Matrícula del avión (ej. CC-DIM)",
      "n° de vuelo": "Número de vuelo",
      "Destino": "Código del destino (ej. SMR)",
      "país": "País del destino (ej. Colombia si es SMR)",
      "hora de inicio": "Hora bajo INICIO TANQUEO (hh:mm)",
      "hora final": "Hora bajo FINAL TANQUEO (hh:mm)",
      "galones entregados": "Valor en GALONES ENTREGADOS",
      "Temp": "Valor en TEMP",
      "API °60": "Valor en API °60"
    }
    """
    response = model.generate_content([prompt, imagen])
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())

archivos = st.file_uploader(
    "Selecciona fotos o archivos PDF:", 
    type=["jpg", "jpeg", "png", "pdf"], 
    accept_multiple_files=True
)

if archivos and api_key:
    genai.configure(api_key=api_key)
    # Nombre de modelo compatible con la capa gratuita
    model = genai.GenerativeModel('gemini-1.5-flash-002')
    
    if st.button("🚀 Extraer Datos a Excel", type="primary"):
        resultados = []
        progreso = st.progress(0)
        
        for i, archivo in enumerate(archivos):
            st.info(f"Procesando: {archivo.name}")
            bytes_data = archivo.read()
            
            if archivo.type == "application/pdf":
                pdf_doc = fitz.open(stream=bytes_data, filetype="pdf")
                for page in pdf_doc:
                    pix = page.get_pixmap(dpi=150)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    try:
                        resultados.append(extraer_datos(img, model))
                    except Exception as e:
                        st.error(f"Error en PDF: {e}")
            else:
                img = Image.open(io.BytesIO(bytes_data))
                try:
                    resultados.append(extraer_datos(img, model))
                except Exception as e:
                    st.error(f"Error en {archivo.name}: {e}")
                    
            progreso.progress((i + 1) / len(archivos))
            
        if resultados:
            df = pd.DataFrame(resultados)
            for col in COLUMNAS:
                if col not in df.columns:
                    df[col] = ""
            df = df[COLUMNAS]
            
            st.success("¡Información extraída con éxito!")
            st.dataframe(df)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Tiquetes')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 Descargar Excel (.xlsx)",
                data=excel_data,
                file_name="Registro_Tiquetes_Energizar.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        
