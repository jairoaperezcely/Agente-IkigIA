import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
from bs4 import BeautifulSoup
import requests
from youtube_transcript_api import YouTubeTranscriptApi
import tempfile
import time
import os
from io import BytesIO
import json
from datetime import date

# --- LIBRERÍAS DE OFICINA Y GRÁFICOS ---
from pptx import Presentation
import matplotlib.pyplot as plt
import pandas as pd
import streamlit.components.v1 as components 

# ==========================================
# CONFIGURACIÓN GLOBAL
# ==========================================
st.set_page_config(page_title="Agente IkigAI V16", page_icon="🧬", layout="wide")

MODELO_USADO = 'gemini-2.5-flash' 
# Si falla, cambie por: 'gemini-2.0-flash-exp'

# ==========================================
# FUNCIÓN VISUALIZADORA (SOLUCIÓN PANTALLA NEGRA)
# ==========================================
def plot_mermaid(code):
    """
    Renderiza diagramas Mermaid sobre un fondo BLANCO explícito.
    Usa el componente nativo de Streamlit para máxima compatibilidad.
    """
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ 
                startOnLoad: true, 
                theme: 'default',  
                securityLevel: 'loose',
            }});
        </script>
        <style>
            /* Forzamos fondo blanco y márgenes para legibilidad perfecta */
            body {{ background-color: white; margin: 0; padding: 20px; font-family: sans-serif; }}
            .mermaid {{ display: flex; justify-content: center; }}
        </style>
    </head>
    <body>
        <div class="mermaid">
            {code}
        </div>
    </body>
    </html>
    """
    components.html(html_code, height=600, scrolling=True)

# ==========================================
# FUNCIONES DE LECTURA (INPUT)
# ==========================================
def get_pdf_text(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages: text += page.extract_text()
    return text

def get_docx_text(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs])

def get_excel_text(excel_file):
    try:
        all_sheets = pd.read_excel(excel_file, sheet_name=None)
        text = ""
        for sheet_name, df in all_sheets.items():
            text += f"\n--- HOJA: {sheet_name} ---\n{df.to_string()}"
        return text
    except Exception as e: return f"Error Excel: {e}"

def get_pptx_text(pptx_file):
    try:
        prs = Presentation(pptx_file)
        text = ""
        for i, slide in enumerate(prs.slides):
            text += f"\n--- SLIDE {i+1} ---\n"
            for shape in slide.shapes:
                if hasattr(shape, "text"): text += shape.text + "\n"
        return text
    except Exception as e: return f"Error PPTX: {e}"

# ==========================================
# FUNCIONES DE GENERACIÓN (OUTPUT)
# ==========================================
def create_chat_docx(messages):
    doc = docx.Document()
    doc.add_heading(f'Acta: {date.today()}', 0)
    for msg in messages:
        doc.add_heading(msg["role"], level=2)
        doc.add_paragraph(msg["content"])
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

def create_clean_docx(text_content):
    doc = docx.Document()
    clean_text = text_content.replace("```markdown", "").replace("```", "")
    for paragraph in clean_text.split('\n'):
        if paragraph.strip(): doc.add_paragraph(paragraph)
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

def generate_pptx_from_data(slide_data):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = slide_data[0].get("title", "Presentación IA")
    slide.placeholders[1].text = f"Generado: {date.today()}"
    for info in slide_data[1:]:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = info.get("title", "Título")
        tf = slide.placeholders[1].text_frame
        for point in info.get("content", []):
            p = tf.add_paragraph(); p.text = point; p.level = 0
    buffer = BytesIO(); prs.save(buffer); buffer.seek(0)
    return buffer

def generate_excel_from_data(excel_data):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, data in excel_data.items():
            pd.DataFrame(data).to_excel(writer, index=False, sheet_name=sheet_name[:30])
    output.seek(0)
    return output

def generate_advanced_chart(chart_data):
    fig, ax = plt.subplots(figsize=(10, 5))
    plt.style.use('seaborn-v0_8-darkgrid')
    labels = chart_data.get("labels", [])
    for ds in chart_data.get("datasets", []):
        if len(ds["values"]) == len(labels):
            if ds.get("type") == "line": ax.plot(labels, ds["values"], label=ds["label"], marker='o')
            else: ax.bar(labels, ds["values"], label=ds["label"], alpha=0.6)
    ax.legend(); ax.set_title(chart_data.get("title", "Gráfico")); plt.tight_layout()
    return fig

# FUNCIONES WEB/YT
def get_youtube_text(url):
    try:
        vid = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
        t = YouTubeTranscriptApi.get_transcript(vid, languages=['es', 'en'])
        return "YT: " + " ".join([i['text'] for i in t])
    except: return "Error YT"

def get_web_text(url):
    try: return "WEB: " + "\n".join([p.get_text() for p in BeautifulSoup(requests.get(url).content, 'html.parser').find_all('p')])
    except: return "Error Web"

# ==========================================
# ESTADO DE SESIÓN
# ==========================================
if "messages" not in st.session_state: st.session_state.messages = []
if "contexto_texto" not in st.session_state: st.session_state.contexto_texto = ""
if "archivo_multimodal" not in st.session_state: st.session_state.archivo_multimodal = None
if "generated_pptx" not in st.session_state: st.session_state.generated_pptx = None
if "generated_chart" not in st.session_state: st.session_state.generated_chart = None
if "generated_excel" not in st.session_state: st.session_state.generated_excel = None
if "generated_word_clean" not in st.session_state: st.session_state.generated_word_clean = None
if "generated_mermaid" not in st.session_state: st.session_state.generated_mermaid = None

# ==========================================
# BARRA LATERAL
# ==========================================
with st.sidebar:
    st.header("⚙️ Panel de Control")
    api_key = st.text_input("🔑 API Key:", type="password")
    temp_val = st.slider("Creatividad", 0.0, 1.0, 0.2)
    st.divider()
    rol = st.radio("Rol:", ["Vicedecano Académico", "Director de UCI", "Consultor Telesalud", "Profesor Universitario", "Investigador Científico", "Mentor de Trading", "Asistente Personal"])
    
    st.subheader("🛠️ FÁBRICA DE ARCHIVOS")
    
    # 1. GENERAR DOC
    if st.button("📄 Word (Doc)"):
        if st.session_state.messages:
            st.session_state.generated_word_clean = create_clean_docx(st.session_state.messages[-1]["content"])
            st.success("✅ Doc Listo")
    if st.session_state.generated_word_clean: st.download_button("📥 Bajar Doc", st.session_state.generated_word_clean, "documento.docx")

    # 2. GENERAR PPTX
    if st.button("🗣️ PPTX"):
        with st.spinner("Diseñando PPTX..."):
            hist = "\n".join([m['content'] for m in st.session_state.messages[-5:]])
            prompt = f"Analiza: {hist}. Genera JSON para PPTX: [{{'title':'Titulo Slide','content':['Punto 1','Punto 2']}}]"
            try:
                genai.configure(api_key=api_key); mod = genai.GenerativeModel(MODELO_USADO)
                res = mod.generate_content(prompt)
                clean_json = res.text.replace("```json","").replace("```","").strip()
                st.session_state.generated_pptx = generate_pptx_from_data(json.loads(clean_json))
                st.success("✅ PPTX Listo")
            except: st.error("Error generando PPTX. Intente de nuevo.")
    if st.session_state.generated_pptx: st.download_button("📥 Bajar PPTX", st.session_state.generated_pptx, "presentacion.pptx")

    # 3. GENERAR EXCEL
    if st.button("x ̅  Excel"):
        with st.spinner("Calculando Excel..."):
            hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
            prompt = f"Analiza: {hist}. Genera JSON para Excel: {{'Hoja1': [{{'ColumnaA':'Dato1', 'ColumnaB':'Dato2'}}]}}"
            try:
                genai.configure(api_key=api_key); mod = genai.GenerativeModel(MODELO_USADO)
                res = mod.generate_content(prompt)
                clean_json = res.text.replace("```json","").replace("```","").strip()
                st.session_state.generated_excel = generate_excel_from_data(json.loads(clean_json))
                st.success("✅ Excel Listo")
            except: st.error("Error generando Excel.")
    if st.session_state.generated_excel: st.download_button("📥 Bajar Excel", st.session_state.generated_excel, "datos.xlsx")

    # 4. GENERAR GRÁFICO
    if st.button("📊 Gráfico Datos"):
        with st.spinner("Graficando..."):
            hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
            prompt = f"Datos de: {hist}. JSON: {{'title':'T','labels':['A','B'],'datasets':[{{'label':'Serie1','values':[10,20],'type':'bar'}}]}}"
            try:
                genai.configure(api_key=api_key); mod = genai.GenerativeModel(MODELO_USADO)
                res = mod.generate_content(prompt)
                clean_json = res.text.replace("```json","").replace("```","").strip()
                st.session_state.generated_chart = generate_advanced_chart(json.loads(clean_json))
                st.success("✅ Gráfico Listo")
            except: st.error("No hay datos suficientes.")

    # 5. GENERAR ESQUEMA VISUAL (MERMAID) - BLINDADO
    if st.button("🎨 Generar Esquema Visual"):
        if len(st.session_state.messages) < 1: st.error("Hablemos primero de un tema.")
        else:
            with st.spinner("Diseñando diagrama..."):
                hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
                prompt_mermaid = f"""
                Analiza el historial reciente: {hist}. 
                Crea un CÓDIGO MERMAID.JS válido para visualizar esto.
                
                REGLAS DE ORO (CRÍTICAS PARA EVITAR ERRORES):
                1. NO uses paréntesis redondos () dentro de los textos de los nodos. Usa corchetes [] o comillas "".
                2. Ejemplo prohibido: Nodo A (Info extra) --> Nodo B
                3. Ejemplo correcto: Nodo A ["Info extra"] --> Nodo B
                4. NO pongas la palabra "mermaid" al principio, solo dentro de las etiquetas markdown.
                
                Tipos sugeridos: 'graph TD' (Procesos), 'mindmap' (Ideas), 'timeline' (Cronologías).
                SALIDA: Solo el código dentro de bloques ```mermaid ... ```
                """
                try:
                    genai.configure(api_key=api_key); mod = genai.GenerativeModel(MODELO_USADO)
                    res = mod.generate_content(prompt_mermaid)
                    st.session_state.generated_mermaid = res.text
                    st.success("✅ Esquema Listo (Ver Arriba)")
                except Exception as e: st.error(f"Error Visual: {e}")

    st.divider()
    st.subheader("📥 FUENTES OMNÍVORAS")
    tab1, tab2, tab3 = st.tabs(["📂 Docs", "👁️ Media", "🌐 Web/YT"])
    
    with tab1:
        uploaded_docs = st.file_uploader("Archivos", type=['pdf', 'docx', 'xlsx', 'pptx'], accept_multiple_files=True)
        if uploaded_docs and st.button(f"Leer {len(uploaded_docs)} Docs"):
            text_acc = ""
            prog = st.progress(0)
            for i, doc in enumerate(uploaded_docs):
                try:
                    if doc.type == "application/pdf": text_acc += f"\n[PDF: {doc.name}]\n{get_pdf_text(doc)}"
                    elif "word" in doc.type: text_acc += f"\n[DOC: {doc.name}]\n{get_docx_text(doc)}"
                    elif "sheet" in doc.type: text_acc += f"\n[XLS: {doc.name}]\n{get_excel_text(doc)}"
                    elif "presentation" in doc.type: text_acc += f"\n[PPT: {doc.name}]\n{get_pptx_text(doc)}"
                except: st.error(f"Error en {doc.name}")
                prog.progress((i+1)/len(uploaded_docs))
            st.session_state.contexto_texto = text_acc
            st.success("✅ Biblioteca Cargada")
    
    with tab2:
        up_media = st.file_uploader("Media", type=['mp4','mp3','png','jpg'])
        if up_media and api_key and st.button("Subir Media"):
            genai.configure(api_key=api_key)
            with st.spinner("Procesando en Google..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.'+up_media.name.split('.')[-1]) as tf:
                    tf.write(up_media.read()); tpath = tf.name
                mfile = genai.upload_file(path=tpath)
                while mfile.state.name == "PROCESSING": time.sleep(1); mfile = genai.get_file(mfile.name)
                st.session_state.archivo_multimodal = mfile
                st.success("✅ Media Lista"); os.remove(tpath)
    
    with tab3:
        if st.button("Leer YT") and (u:=st.text_input("Link YT")): 
            st.session_state.contexto_texto=get_youtube_text(u);st.success("✅ YT Leído")
        if st.button("Leer Web") and (w:=st.text_input("Link Web")): 
            st.session_state.contexto_texto=get_web_text(w);st.success("✅ Web Leída")

    st.divider()
    if st.session_state.messages:
        st.download_button("💾 Guardar Chat", create_chat_docx(st.session_state.messages), "chat.docx")
        st.download_button("🧠 Backup Memoria", json.dumps(st.session_state.messages), "memoria.json")
    
    uploaded_memory = st.file_uploader("Cargar Backup", type=['json'])
    if uploaded_memory and st.button("Restaurar"): 
        st.session_state.messages = json.load(uploaded_memory)
        st.rerun()
        
    if st.button("🗑️ Borrar Todo"): 
        st.session_state.clear()
        st.rerun()

# ==========================================
# CHAT Y VISUALIZADORES
# ==========================================
st.title(f"🤖 Agente V16: {rol}")
if not api_key: st.warning("⚠️ Ingrese API Key en la barra lateral."); st.stop()

# 1. VISUALIZADOR MERMAID (FONDO BLANCO)
if st.session_state.generated_mermaid:
    st.subheader("🎨 Esquema Visual")
    code = st.session_state.generated_mermaid.replace("```mermaid","").replace("```","").strip()
    try: plot_mermaid(code)
    except: st.code(code)
    if st.button("Cerrar Esquema"): st.session_state.generated_mermaid=None; st.rerun()

# 2. GRÁFICOS
if st.session_state.generated_chart: 
    st.pyplot(st.session_state.generated_chart)
    st.button("Cerrar Gráfico", on_click=lambda: st.session_state.update(generated_chart=None))

# 3. LÓGICA DE CHAT
genai.configure(api_key=api_key)
model = genai.GenerativeModel(MODELO_USADO, generation_config={"temperature": temp_val})

for m in st.session_state.messages: st.chat_message(m["role"]).markdown(m["content"])

if p := st.chat_input("Escriba su instrucción..."):
    st.session_state.messages.append({"role": "user", "content": p})
    st.chat_message("user").markdown(p)
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            ctx = st.session_state.contexto_texto
            prompt = f"Rol: {rol}. {('Usa SOLO adjuntos.' if ctx else 'Usa conocimiento general.')} Historial: {st.session_state.messages[-5:]}. Consulta: {p}"
            if ctx: prompt += f"\nDOCS: {ctx[:500000]}"
            con = [prompt]
            if st.session_state.archivo_multimodal: 
                con.insert(0, st.session_state.archivo_multimodal); con.append("(Analiza el archivo multimedia).")
            
            try:
                res = model.generate_content(con)
                st.markdown(res.text)
                st
