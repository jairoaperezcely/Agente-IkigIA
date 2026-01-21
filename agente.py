import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from bs4 import BeautifulSoup
import requests
from youtube_transcript_api import YouTubeTranscriptApi
import tempfile
import time
import os
from io import BytesIO
import json
from datetime import date
import re 

# --- LIBRERÍAS DE OFICINA, GRÁFICOS Y ESTILOS ---
from pptx import Presentation
from pptx.util import Pt as PtxPt
import matplotlib.pyplot as plt
import pandas as pd
import streamlit.components.v1 as components 
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side 
from openpyxl.utils import get_column_letter

# ==========================================
# CONFIGURACIÓN GLOBAL
# ==========================================
st.set_page_config(page_title="Agente IkigAI V21", page_icon="👔", layout="wide")

MODELO_USADO = 'gemini-2.5-flash' 

# ==========================================
# FUNCIÓN VISUALIZADORA MERMAID
# ==========================================
def plot_mermaid(code):
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ startOnLoad: true, theme: 'default', securityLevel: 'loose' }});
        </script>
        <style>
            body {{ background-color: white; margin: 0; padding: 20px; font-family: sans-serif; }}
            .mermaid {{ display: flex; justify-content: center; }}
        </style>
    </head>
    <body>
        <div class="mermaid">{code}</div>
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
# FUNCIONES DE GENERACIÓN (OUTPUT DE LUJO)
# ==========================================

# 1. WORD ACTA (MEMORANDO)
def create_chat_docx(messages):
    doc = docx.Document()
    # Márgenes Estándar
    sections = doc.sections
    for section in sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(2.54)
        section.right_margin = Cm(2.54)

    # Encabezado
    header = doc.sections[0].header
    p = header.paragraphs[0]
    p.text = f"CONFIDENCIAL | {date.today()}"
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    # Título
    t = doc.add_heading('BITÁCORA DE SESIÓN', 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("_" * 40).alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    for msg in messages:
        role = "USUARIO" if msg["role"] == "user" else "ASISTENTE"
        p_head = doc.add_paragraph()
        run = p_head.add_run(f"[{role}]")
        run.bold = True
        run.font.color.rgb = RGBColor(0, 51, 102) if role == "ASISTENTE" else RGBColor(80, 80, 80)
        p_msg = doc.add_paragraph(msg["content"])
        p_msg.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph("")
        
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# 2. WORD DOCUMENTO PRO (NUEVO DISEÑO ELEGANTE)
def create_clean_docx(text_content):
    doc = docx.Document()
    
    # --- CONFIGURACIÓN DE ESTILOS GLOBALES ---
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial' # Fuente limpia y profesional
    font.size = Pt(11)
    
    # Márgenes Profesionales (2.54 cm / 1 inch)
    sections = doc.sections
    for section in sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(2.54)
        section.right_margin = Cm(2.54)

    # --- PORTADA ELEGANTE ---
    # Espacio inicial
    for _ in range(3): doc.add_paragraph("")
    
    # Título Principal
    title = doc.add_paragraph("INFORME EJECUTIVO")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = title.runs[0]
    run_title.bold = True
    run_title.font.size = Pt(24)
    run_title.font.color.rgb = RGBColor(0, 51, 102) # Azul Marino
    
    # Línea divisoria
    doc.add_paragraph("__________________________________________________").alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Fecha y Autor
    meta = doc.add_paragraph(f"\nFecha de Emisión: {date.today().strftime('%d de %B de %Y')}")
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.runs[0].italic = True
    
    # Salto de página para empezar el contenido limpio
    doc.add_page_break()

    # --- CONTENIDO INTERPRETADO ---
    clean_text = text_content.replace("```markdown", "").replace("```", "")
    lines = clean_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Título 1 (H1)
        if line.startswith('# '): 
            text_h1 = line.replace('# ','')
            h1 = doc.add_heading(text_h1, level=1)
            h1_run = h1.runs[0]
            h1_run.font.color.rgb = RGBColor(0, 51, 102) # Azul Corporativo
            h1_run.font.size = Pt(16)
            h1.alignment = WD_ALIGN_PARAGRAPH.LEFT
            
        # Título 2 (H2)
        elif line.startswith('## '):
            text_h2 = line.replace('## ','')
            h2 = doc.add_heading(text_h2, level=2)
            h2_run = h2.runs[0]
            h2_run.font.color.rgb = RGBColor(50, 50, 50) # Gris oscuro
            h2_run.font.size = Pt(14)
            
        # Título 3 (H3)
        elif line.startswith('### '):
            text_h3 = line.replace('### ','')
            h3 = doc.add_heading(text_h3, level=3)
            h3.runs[0].font.color.rgb = RGBColor(80, 80, 80) # Gris medio
            
        # Viñetas
        elif line.startswith('- ') or line.startswith('* '):
            p = doc.add_paragraph(line[2:], style='List Bullet')
            p.paragraph_format.space_after = Pt(2) # Espacio fino entre items
            
        # Listas Numeradas
        elif line[0].isdigit() and line[1] == '.':
            # Intentar separar numero del texto
            parts = line.split('.', 1)
            if len(parts) > 1:
                p = doc.add_paragraph(parts[1].strip(), style='List Number')
                p.paragraph_format.space_after = Pt(2)
            else:
                doc.add_paragraph(line)
                
        # Párrafos Normales
        else:
            # Eliminar negritas de markdown (**texto**) para limpieza (opcional, aquí lo dejamos simple)
            clean_line = line.replace("**", "") 
            p = doc.add_paragraph(clean_line)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY # Justificado elegante
            p.paragraph_format.space_after = Pt(8) # Aire entre párrafos
            p.paragraph_format.line_spacing = 1.15 # Espaciado cómodo

    # Pie de página en todas las secciones
    for section in doc.sections:
        footer = section.footer
        p_foot = footer.paragraphs[0]
        p_foot.text = "Documento generado con Inteligencia Artificial - Uso Interno"
        p_foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_foot.style.font.size = Pt(8)
        p_foot.style.font.color.rgb = RGBColor(150, 150, 150)
    
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# 3. PPTX PRO (MOTOR INTELIGENTE)
def generate_pptx_from_data(slide_data, template_file=None):
    if template_file: 
        template_file.seek(0)
        prs = Presentation(template_file)
    else: 
        prs = Presentation()
    
    def clean_text(txt):
        txt = re.sub(r'\*\*(.*?)\*\*', r'\1', txt) 
        return txt.strip()

    try:
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        if slide.shapes.title: 
            slide.shapes.title.text = clean_text(slide_data[0].get("title", "Presentación"))
        if len(slide.placeholders) > 1: 
            slide.placeholders[1].text = f"Generado el: {date.today()}"
    except:
        slide = prs.slides.add_slide(prs.slide_layouts[0])

    for info in slide_data[1:]:
        layout_index = 1 if len(prs.slide_layouts) > 1 else 0
        slide = prs.slides.add_slide(prs.slide_layouts[layout_index])
        
        if slide.shapes.title: 
            slide.shapes.title.text = clean_text(info.get("title", "Info"))
        
        content_list = info.get("content", [])
        total_chars = sum(len(point) for point in content_list)
        font_size = 24 
        if total_chars > 600: font_size = 14
        elif total_chars > 400: font_size = 18
        elif total_chars > 200: font_size = 20
        
        for shape in slide.placeholders:
            if shape.placeholder_format.idx == 1: 
                tf = shape.text_frame; tf.clear() 
                for point in content_list:
                    cleaned_point = clean_text(point)
                    p = tf.add_paragraph()
                    p.text = cleaned_point
                    p.font.size = PtxPt(font_size) 
                    p.level = 0 
                    p.space_after = PtxPt(6) 

    buffer = BytesIO(); prs.save(buffer); buffer.seek(0)
    return buffer

# 4. EXCEL PRO
def generate_excel_from_data(excel_data):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, data in excel_data.items():
            df = pd.DataFrame(data)
            df.to_excel(writer, index=False, sheet_name=sheet_name[:30])
            worksheet = writer.sheets[sheet_name[:30]]
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
            border_style = Side(border_style="thin", color="000000")
            border = Border(left=border_style, right=border_style, top=border_style, bottom=border_style)
            for col_idx, column_cells in enumerate(worksheet.columns, 1):
                column_letter = get_column_letter(col_idx)
                worksheet.column_dimensions[column_letter].width = 20
                header_cell = worksheet[f"{column_letter}1"]
                header_cell.font = header_font; header_cell.fill = header_fill
                header_cell.alignment = Alignment(horizontal="center")
                for cell in column_cells: cell.border = border
    output.seek(0)
    return output

# 5. GRÁFICO PRO
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
    st.header("⚙️ Configuración")
    api_key = st.text_input("🔑 API Key:", type="password")
    temp_val = st.slider("Creatividad", 0.0, 1.0, 0.2)
    st.divider()
    rol = st.radio("Rol:", ["Vicedecano Académico", "Director de UCI", "Consultor Telesalud", "Profesor Universitario", "Investigador Científico", "Mentor de Trading", "Asistente Personal"])
    
    st.markdown("---")
    st.subheader("🏭 Centro de Producción")
    
    tab_office, tab_data, tab_visual = st.tabs(["📝 Oficina", "📊 Analítica", "🎨 Diseño"])

    # 1. OFICINA
    with tab_office:
        st.markdown("##### 📄 Informes Ejecutivos")
        if st.button("Generar Word (Elegante)", use_container_width=True):
            if st.session_state.messages:
                last_msg = st.session_state.messages[-1]["content"]
                st.session_state.generated_word_clean = create_clean_docx(last_msg)
                st.success("¡Listo!")
        if st.session_state.generated_word_clean: 
            st.download_button("📥 Descargar Informe", st.session_state.generated_word_clean, "informe_ejecutivo.docx", use_container_width=True)
        
        st.divider()
        st.markdown("##### 🗣️ Presentaciones")
        uploaded_template = st.file_uploader("Plantilla PPTX (Opcional)", type=['pptx'])
        if st.button("Generar PPTX", use_container_width=True):
            with st.spinner("Diseñando..."):
                hist = "\n".join([m['content'] for m in st.session_state.messages[-5:]])
                prompt = f"""
                Analiza: {hist}. 
                Genera JSON para PPTX.
                REGLAS: Máximo 5 puntos por slide. Texto resumido.
                FORMATO: [{{'title':'T','content':['A','B']}}]
                IMPORTANTE: Responde SOLO el JSON.
                """
                try:
                    genai.configure(api_key=api_key); mod = genai.GenerativeModel(MODELO_USADO)
                    res = mod.generate_content(prompt)
                    clean_text = res.text.replace("```json","").replace("```","").strip()
                    start = clean_text.find("["); end = clean_text.rfind("]") + 1
                    if start != -1 and end != -1: clean_text = clean_text[start:end]
                    tpl = uploaded_template if uploaded_template else None
                    st.session_state.generated_pptx = generate_pptx_from_data(json.loads(clean_text), tpl)
                    st.success("¡Listo!")
                except Exception as e: st.error(f"Error: {e}")
        if st.session_state.generated_pptx: 
            st.download_button("📥 Descargar PPTX", st.session_state.generated_pptx, "presentacion.pptx", use_container_width=True)

    # 2. ANALÍTICA
    with tab_data:
        st.markdown("##### 📗 Hojas de Cálculo")
        if st.button("Generar Excel (Pro)", use_container_width=True):
            with st.spinner("Calculando..."):
                hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
                prompt = f"Analiza: {hist}. JSON Excel: {{'Hoja1': [{{'ColumnaA':'Dato1', 'ColumnaB':'Dato2'}}]}}"
                try:
                    genai.configure(api_key=api_key); mod = genai.GenerativeModel(MODELO_USADO)
                    res = mod.generate_content(prompt)
                    clean_text = res.text.replace("```json","").replace("```","").strip()
                    start = clean_text.find("{"); end = clean_text.rfind("}") + 1
                    if start != -1 and end != -1: clean_text = clean_text[start:end]
                    st.session_state.generated_excel = generate_excel_from_data(json.loads(clean_text))
                    st.success("¡Listo!")
                except: st.error("Error Excel.")
        if st.session_state.generated_excel: 
            st.download_button("📥 Descargar Excel", st.session_state.generated_excel, "datos_pro.xlsx", use_container_width=True)
            
        st.divider()
        st.markdown("##### 📈 Gráficos")
        if st.button("Generar Gráfico", use_container_width=True):
            with st.spinner("Graficando..."):
                hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
                prompt = f"Datos de: {hist}. JSON: {{'title':'T','labels':['A'],'datasets':[{{'label':'L','values':[1],'type':'bar'}}]}}"
                try:
                    genai.configure(api_key=api_key); mod = genai.GenerativeModel(MODELO_USADO)
                    res = mod.generate_content(prompt)
                    clean_json = res.text.replace("```json","").replace("```","").strip()
                    st.session_state.generated_chart = generate_advanced_chart(json.loads(clean_json))
                    st.success("¡Listo!")
                except: st.error("Sin datos.")

    # 3. DISEÑO
    with tab_visual:
        st.markdown("##### 🎨 Diagramas")
        if st.button("Crear Esquema Visual", use_container_width=True):
            if len(st.session_state.messages) < 1: st.error("Falta tema.")
            else:
                with st.spinner("Dibujando..."):
                    hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
                    prompt_mermaid = f"""
                    Analiza: {hist}. Crea CÓDIGO MERMAID.JS válido.
                    REGLAS: NO usar paréntesis () en nodos. Usa [].
                    Tipos: 'graph TD', 'mindmap'.
                    SALIDA: Solo bloque ```mermaid ... ```
                    """
                    try:
                        genai.configure(api_key=api_key); mod = genai.GenerativeModel(MODELO_USADO)
                        res = mod.generate_content(prompt_mermaid)
                        st.session_state.generated_mermaid = res.text
                        st.success("¡Listo!")
                    except Exception as e: st.error(f"Error: {e}")

    st.markdown("---")
    st.subheader("📥 Fuentes")
    tab1, tab2, tab3 = st.tabs(["📂 Docs", "👁️ Media", "🌐 Web"])
    
    with tab1:
        uploaded_docs = st.file_uploader("Archivos", type=['pdf', 'docx', 'xlsx', 'pptx'], accept_multiple_files=True)
        if uploaded_docs and st.button(f"Leer {len(uploaded_docs)} Docs", use_container_width=True):
            text_acc = ""
            for doc in uploaded_docs:
                try:
                    if doc.type == "application/pdf": text_acc += get_pdf_text(doc)
                    elif "word" in doc.type: text_acc += get_docx_text(doc)
                    elif "sheet" in doc.type: text_acc += get_excel_text(doc)
                    elif "presentation" in doc.type: text_acc += get_pptx_text(doc)
                except: pass
            st.session_state.contexto_texto = text_acc
            st.success("Cargado")
    
    with tab2:
        up_media = st.file_uploader("Media", type=['mp4','mp3','png','jpg'])
        if up_media and api_key and st.button("Subir Media", use_container_width=True):
            genai.configure(api_key=api_key)
            with st.spinner("Procesando..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.'+up_media.name.split('.')[-1]) as tf:
                    tf.write(up_media.read()); tpath = tf.name
                mfile = genai.upload_file(path=tpath)
                while mfile.state.name == "PROCESSING": time.sleep(1); mfile = genai.get_file(mfile.name)
                st.session_state.archivo_multimodal = mfile
                st.success("Listo"); os.remove(tpath)
    
    with tab3:
        if st.button("Leer YT", use_container_width=True) and (u:=st.text_input("Link YT")): 
            st.session_state.contexto_texto=get_youtube_text(u);st.success("OK")
        if st.button("Leer Web", use_container_width=True) and (w:=st.text_input("Link Web")): 
            st.session_state.contexto_texto=get_web_text(w);st.success("OK")

    st.markdown("---")
    if st.session_state.messages:
        c1, c2 = st.columns(2)
        c1.download_button("💾 Chat", create_chat_docx(st.session_state.messages), "acta.docx", use_container_width=True)
        c2.download_button("🧠 Backup", json.dumps(st.session_state.messages), "mem.json", use_container_width=True)
    
    uploaded_memory = st.file_uploader("Cargar Backup", type=['json'])
    if uploaded_memory and st.button("Restaurar", use_container_width=True): 
        st.session_state.messages = json.load(uploaded_memory); st.rerun()
        
    if st.button("🗑️ Borrar Todo", use_container_width=True): st.session_state.clear(); st.rerun()

# ==========================================
# CHAT
# ==========================================
st.title(f"🤖 Agente V21: {rol}")
if not api_key: st.warning("⚠️ Ingrese API Key"); st.stop()

if st.session_state.generated_mermaid:
    st.subheader("🎨 Esquema Visual")
    code = st.session_state.generated_mermaid.replace("```mermaid","").replace("```","").strip()
    try: plot_mermaid(code)
    except: st.code(code)
    if st.button("Cerrar Esquema"): st.session_state.generated_mermaid=None; st.rerun()

if st.session_state.generated_chart: 
    st.pyplot(st.session_state.generated_chart)
    st.button("Cerrar Gráfico", on_click=lambda: st.session_state.update(generated_chart=None))

genai.configure(api_key=api_key)
model = genai.GenerativeModel(MODELO_USADO, generation_config={"temperature": temp_val})

for m in st.session_state.messages: st.chat_message(m["role"]).markdown(m["content"])

if p := st.chat_input("Escriba su instrucción..."):
    st.session_state.messages.append({"role": "user", "content": p})
    st.chat_message("user").markdown(p)
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            ctx =
