import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
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

# --- LIBRERÍAS DE OFICINA Y GRÁFICOS ---
from pptx import Presentation
from pptx.util import Pt as PtxPt, Inches as PtxInches
from pptx.dml.color import RGBColor as PtxRGB
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE
import matplotlib.pyplot as plt
import pandas as pd
import streamlit.components.v1 as components
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# --- LIBRERÍAS DE VOZ ---
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder

# ==========================================
# ⚙️ CONFIGURACIÓN DEL SISTEMA
# ==========================================
st.set_page_config(page_title="Agente IkigAI V50", page_icon="🏛️", layout="wide")

MODELO_USADO = 'gemini-2.5-flash' 

# ==========================================
# 🧠 MEMORIA MAESTRA
# ==========================================
MEMORIA_MAESTRA = """
PERFIL DEL USUARIO (QUIÉN SOY):
- Soy un Líder Transformador en Salud: Médico Especialista en Anestesiología y Cuidado Crítico (UCI), Epidemiólogo Clínico y Doctorando en Bioética.
- Roles de Alto Impacto:
  1. Academia: Vicedecano Académico de la Facultad de Medicina (Universidad Nacional de Colombia).
  2. Innovación: Coordinador del Centro de Telemedicina, IA e Innovación en Salud.
  3. Hospitalario: Director de Cuidado Crítico (UCI) y Líder de Humanización en el Hospital Universitario Nacional (HUN).
  4. Docencia: Profesor de Medicina y Cuidado Crítico.

MI ADN Y FILOSOFÍA:
- Motor Vital: Me mueve la innovación, la estrategia y estar a la vanguardia. Soy un líder innato que genera valor en cada acción.
- Humanismo: Me duele el sufrimiento del otro. Creo firmemente en las personas y en su capacidad de transformar el mundo.
- Enfoque: No solo implemento tecnología; acompaño la GESTIÓN DEL CAMBIO y la CO-CREACIÓN, especialmente llevando salud digital a los territorios.

INSTRUCCIONES OPERATIVAS:
1. ERES MI SECRETARÍA TÉCNICA DE ALTO NIVEL.
2. TUS ENTREGABLES DEBEN SER IMPECABLES: Listos para presentar en Junta Directiva o Consejo de Facultad.
3. SIEMPRE QUE PUEDAS, USA DATOS Y TABLAS.
4. NO INVENTES HECHOS. Si no sabes algo, búscalo en los documentos adjuntos o dilo.
5. NO USES BÚSQUEDA WEB (Google Search). Confía en tu lógica y en los archivos.
"""

# ==========================================
# 🎨 MOTOR VISUAL (MERMAID JS)
# ==========================================
def plot_mermaid(code):
    html_code = f"""
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'base', securityLevel: 'loose' }});
    </script>
    <div class="mermaid">{code}</div>
    """
    components.html(html_code, height=500, scrolling=True)

# ==========================================
# 📖 MOTOR DE LECTURA
# ==========================================
@st.cache_data
def get_pdf_text(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages: text += page.extract_text()
    return text

@st.cache_data
def get_docx_text(docx_file):
    doc = docx.Document(docx_file)
    return "\n".join([para.text for para in doc.paragraphs])

@st.cache_data
def get_excel_text(excel_file):
    try:
        all_sheets = pd.read_excel(excel_file, sheet_name=None)
        text = ""
        for sheet_name, df in all_sheets.items():
            text += f"\n--- HOJA: {sheet_name} ---\n{df.to_string()}"
        return text
    except Exception as e: return f"Error leyendo Excel: {e}"

@st.cache_data
def get_pptx_text(pptx_file):
    try:
        prs = Presentation(pptx_file)
        text = ""
        for i, slide in enumerate(prs.slides):
            text += f"\n--- SLIDE {i+1} ---\n"
            for shape in slide.shapes:
                if hasattr(shape, "text"): text += shape.text + "\n"
        return text
    except Exception as e: return f"Error leyendo PPTX: {e}"

def get_youtube_text(url):
    try:
        vid = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1]
        t = YouTubeTranscriptApi.get_transcript(vid, languages=['es', 'en'])
        return "TRANSCRIPCIÓN YT: " + " ".join([i['text'] for i in t])
    except: return "No se pudo obtener transcripción de YT."

def get_web_text(url):
    try: 
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        paragraphs = soup.find_all('p')
        return "CONTENIDO WEB: " + "\n".join([p.get_text() for p in paragraphs])
    except: return "No se pudo leer la página web."

# ==========================================
# 🏭 MOTOR DE PRODUCCIÓN (OFFICE)
# ==========================================

# --- 1. GENERADOR WORD ---
def create_chat_docx(messages):
    doc = docx.Document()
    for section in doc.sections:
        section.top_margin = Cm(2.54); section.bottom_margin = Cm(2.54)
    
    header = doc.sections[0].header
    p = header.paragraphs[0]
    p.text = f"CONFIDENCIAL | Generado el {date.today()}"
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    t = doc.add_heading('BITÁCORA DE SESIÓN - AGENTE V50', 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("_" * 50).alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    def clean_chat(txt): 
        txt = re.sub(r'^#+\s*', '', txt, flags=re.MULTILINE)
        return txt.replace("**", "").replace("__", "").replace("`", "").strip()

    for msg in messages:
        role = "USUARIO" if msg["role"] == "user" else "ASISTENTE (IA)"
        p_head = doc.add_paragraph()
        run = p_head.add_run(f"[{role}]")
        run.bold = True
        run.font.color.rgb = RGBColor(0, 51, 102) if role == "ASISTENTE (IA)" else RGBColor(80, 80, 80)
        p_msg = doc.add_paragraph(clean_chat(msg["content"]))
        p_msg.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph("")
        
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# --- 2. GENERADOR WORD PRO ---
def create_clean_docx(text_content):
    doc = docx.Document()
    style = doc.styles['Normal']; style.font.name = 'Arial'; style.font.size = Pt(11)
    
    for section in doc.sections:
        section.top_margin = Cm(2.54); section.bottom_margin = Cm(2.54)

    for _ in range(4): doc.add_paragraph("")
    title = doc.add_paragraph("INFORME EJECUTIVO")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = title.runs[0]
    run_title.bold = True; run_title.font.size = Pt(24); run_title.font.color.rgb = RGBColor(0, 51, 102)
    
    subtitle = doc.add_paragraph("Vicedecanatura Académica / Dirección UCI")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.runs[0].font.size = Pt(14); subtitle.runs[0].italic = True
    
    doc.add_paragraph("__________________________________________________").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"\nFecha: {date.today().strftime('%d de %B de %Y')}").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_page_break()

    def clean_md(text): return text.replace("**", "").replace("__", "").replace("`", "").strip()

    def build_word_table(rows_data):
        if not rows_data: return
        table = doc.add_table(rows=len(rows_data), cols=len(rows_data[0]))
        table.style = 'Table Grid'
        for i, row in enumerate(rows_data):
            for j, cell_text in enumerate(row):
                if j < len(table.columns):
                    cell = table.cell(i, j)
                    cell.text = clean_md(cell_text)
                    if i == 0: 
                        shading = parse_xml(r'<w:shd {} w:fill="003366"/>'.format(nsdecls('w')))
                        cell._tc.get_or_add_tcPr().append(shading)
                        for p in cell.paragraphs:
                            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            for r in p.runs:
                                r.font.color.rgb = RGBColor(255, 255, 255); r.bold = True

    lines = text_content.split('\n')
    table_buffer = []; in_table = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|'):
            if "---" in stripped: continue 
            row_cells = [c.strip() for c in stripped[1:-1].split('|')]
            table_buffer.append(row_cells)
            in_table = True
        else:
            if in_table:
                build_word_table(table_buffer)
                table_buffer = []; in_table = False
                doc.add_paragraph("")

            if not stripped: continue

            header_match = re.match(r'^(#+)\s*(.*)', stripped)
            if header_match:
                hashes, raw_text = header_match.groups()
                level = len(hashes)
                clean_title = clean_md(raw_text)
                if level == 1:
                    h = doc.add_heading(clean_title, level=1)
                    h.runs[0].font.color.rgb = RGBColor(0, 51, 102); h.runs[0].font.size = Pt(16)
                elif level == 2:
                    h = doc.add_heading(clean_title, level=2)
                    h.runs[0].font.color.rgb = RGBColor(50, 50, 50); h.runs[0].font.size = Pt(14)
                else: doc.add_heading(clean_title, level=3)
            elif stripped.startswith('- ') or stripped.startswith('* '):
                doc.add_paragraph(clean_md(stripped[2:]), style='List Bullet')
            elif re.match(r'^\d+\.', stripped):
                parts = stripped.split('.', 1)
                doc.add_paragraph(clean_md(parts[1]) if len(parts)>1 else clean_md(stripped), style='List Number')
            else:
                p = doc.add_paragraph(clean_md(stripped))
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p.paragraph_format.space_after = Pt(6)

    if in_table and table_buffer: build_word_table(table_buffer)
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# --- 3. GENERADOR PPTX ---
def generate_pptx_from_data(slide_data, template_file=None):
    if template_file: 
        template_file.seek(0); prs = Presentation(template_file)
        using_template = True
    else: 
        prs = Presentation()
        using_template = False
    
    SLIDE_WIDTH = prs.slide_width; SLIDE_HEIGHT = prs.slide_height
    
    def clean_text(txt): return re.sub(r'\*\*(.*?)\*\*', r'\1', txt).strip()

    def apply_design(slide, title_shape=None):
        if using_template: return
        shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, PtxInches(0), PtxInches(0), PtxInches(0.4), SLIDE_HEIGHT)
        shape.fill.solid(); shape.fill.fore_color.rgb = PtxRGB(0, 51, 102)
        if title_shape:
            title_shape.text_frame.paragraphs[0].font.color.rgb = PtxRGB(0, 51, 102)
            title_shape.top = PtxInches(0.5); title_shape.left = PtxInches(0.8)
            title_shape.width = SLIDE_WIDTH - PtxInches(1.5)

    def create_chart_image(data_dict):
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(8, 5))
        labels = data_dict.get('labels', []); values = data_dict.get('values', [])
        label = data_dict.get('label', 'Datos')
        colors = ['#003366', '#708090', '#4682B4', '#A9A9A9']
        if len(labels) == len(values):
            bars = ax.bar(labels, values, color=colors[:len(labels)], alpha=0.9)
            ax.bar_label(bars, fmt='%.1f')
        ax.set_title(label, fontsize=14, fontweight='bold', color='#333333')
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        plt.tight_layout()
        img_stream = BytesIO(); plt.savefig(img_stream, format='png', dpi=150); img_stream.seek(0)
        plt.close(fig); return img_stream

    try:
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        if slide.shapes.title: 
            slide.shapes.title.text = clean_text(slide_data[0].get("title", "Presentación Estratégica"))
    except: pass

    for info in slide_data[1:]:
        slide_type = info.get("type", "text") 
        content = info.get("content", [])
        ref_text = info.get("references", "")
        
        layout_idx = 1 if using_template else 6
        if len(prs.slide_layouts) < 2: layout_idx = 0
        slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])
        
        if not using_template:
            title_shape = slide.shapes.add_textbox(PtxInches(0.8), PtxInches(0.5), PtxInches(8), PtxInches(1))
            title_shape.text = clean_text(info.get("title", "Detalle"))
            apply_design(slide, title_shape)
        else:
            if slide.shapes.title: slide.shapes.title.text = clean_text(info.get("title", "Detalle"))

        if slide_type == "table":
            rows = len(content); cols = len(content[0]) if rows > 0 else 1
            target_width = SLIDE_WIDTH * 0.9
            left = (SLIDE_WIDTH - target_width) / 2
            top = PtxInches(2.0); height = PtxInches(rows * 0.4)
            graphic_frame = slide.shapes.add_table(rows, cols, left, top, target_width, height)
            table = graphic_frame.table
            for col in table.columns: col.width = int(target_width / cols)

            for i, row in enumerate(content):
                for j, val in enumerate(row):
                    if j < cols:
                        cell = table.cell(i, j); cell.text = str(val)
                        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                        cell.text_frame.paragraphs[0].font.size = PtxPt(12 if len(str(val)) < 20 else 10)
                        cell.text_frame.paragraphs[0].font.name = 'Arial'
                        if i == 0:
                            cell.fill.solid(); cell.fill.fore_color.rgb = PtxRGB(0, 51, 102)
                            cell.text_frame.paragraphs[0].font.color.rgb = PtxRGB(255, 255, 255)
            graphic_frame.left = int((SLIDE_WIDTH - graphic_frame.width) / 2)

        elif slide_type == "chart":
            chart_data = info.get("chart_data", {}) 
            if chart_data:
                img_stream = create_chart_image(chart_data)
                pic_width = SLIDE_WIDTH * 0.7; pic_left = (SLIDE_WIDTH - pic_width) / 2; pic_top = PtxInches(2.2)
                slide.shapes.add_picture(img_stream, pic_left, pic_top, width=pic_width)

        else:
            if not using_template:
                box_width = SLIDE_WIDTH * 0.85; box_left = (SLIDE_WIDTH - box_width) / 2
                body_shape = slide.shapes.add_textbox(box_left, PtxInches(1.8), box_width, PtxInches(5))
                tf = body_shape.text_frame
            else:
                tf = None
                for shape in slide.placeholders:
                    if shape.placeholder_format.idx == 1: tf = shape.text_frame; tf.clear(); break
                if not tf:
                    body_shape = slide.shapes.add_textbox(PtxInches(1), PtxInches(2), PtxInches(8), PtxInches(4))
                    tf = body_shape.text_frame
            
            tf.word_wrap = True; tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
            for point in content:
                p = tf.add_paragraph()
                p.text = clean_text(str(point))
                p.font.name = 'Arial'; p.font.color.rgb = PtxRGB(60, 60, 60); p.space_after = PtxPt(12)

        if ref_text and ref_text != "N/A":
            left = PtxInches(0.5); top = SLIDE_HEIGHT - PtxInches(0.6)
            width = SLIDE_WIDTH - PtxInches(1.0); height = PtxInches(0.4)
            txBox = slide.shapes.add_textbox(left, top, width, height)
            p = txBox.text_frame.paragraphs[0]
            p.text = f"Fuente: {ref_text}"; p.font.size = PtxPt(10); p.font.italic = True; p.font.color.rgb = PtxRGB(120, 120, 120)

    buffer = BytesIO(); prs.save(buffer); buffer.seek(0)
    return buffer

# --- 4. GENERADOR EXCEL ---
def generate_excel_from_data(excel_data):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, data in excel_data.items():
            df = pd.DataFrame(data)
            safe_name = re.sub(r'[\\/*?:\[\]]', "", sheet_name)[:30]
            df.to_excel(writer, index=False, sheet_name=safe_name)
            worksheet = writer.sheets[safe_name]
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="003366", end_color="003366", fill_type="solid")
            for col_idx, column_cells in enumerate(worksheet.columns, 1):
                col_letter = get_column_letter(col_idx)
                worksheet.column_dimensions[col_letter].width = 25
                worksheet[f"{col_letter}1"].font = header_font
                worksheet[f"{col_letter}1"].fill = header_fill
    output.seek(0)
    return output

# --- 5. GENERADOR GRÁFICOS ---
def generate_advanced_chart(chart_data):
    plt.style.use('seaborn-v0_8-whitegrid') 
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ['#003366', '#708090', '#A9A9A9', '#4682B4', '#DAA520']
    labels = chart_data.get("labels", []); datasets = chart_data.get("datasets", [])
    
    for i, ds in enumerate(datasets):
        color = colors[i % len(colors)]
        if len(ds["values"]) == len(labels):
            if ds.get("type") == "line": 
                ax.plot(labels, ds["values"], label=ds["label"], marker='o', color=color, linewidth=3)
            else: 
                bars = ax.bar(labels, ds["values"], label=ds["label"], color=color, alpha=0.85)
                ax.bar_label(bars, padding=3, fmt='%.1f', fontweight='bold')
    
    ax.legend(frameon=True, loc='upper right')
    ax.set_title(chart_data.get("title", "Análisis de Datos"), fontsize=16, fontweight='bold', color='#003366', pad=20)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    plt.tight_layout()
    return fig

# ==========================================
# 💾 ESTADO
# ==========================================
keys = ["messages", "contexto_texto", "archivo_multimodal", "generated_pptx", "generated_chart", "generated_excel", "generated_word_clean", "generated_mermaid"]
for k in keys:
    if k not in st.session_state: st.session_state[k] = [] if k == "messages" else "" if k == "contexto_texto" else None

# ==========================================
# 🖥️ BARRA LATERAL (DISEÑO ORGANIZADO)
# ==========================================
with st.sidebar:
    st.markdown("### 🏛️ Panel de Control")
    st.divider()
    
    # 1. CREDENCIALES
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ Autenticado")
    else:
        api_key = st.text_input("🔑 API Key:", type="password")

    # 2. PERFIL DE USUARIO (Compacto)
    st.markdown("##### 👤 Perfil Activo")
    rol = st.selectbox("", [ 
        "Socio Estratégico (Innovación)", 
        "Vicedecano Académico",
        "Director de UCI",
        "Consultor Telesalud",
        "Profesor Universitario",
        "Investigador Científico",
        "Mentor de Trading",
        "Asistente Ejecutivo"
    ], label_visibility="collapsed")

    prompts_roles = {
        "Socio Estratégico (Innovación)": "Eres Consultor Senior. Reta la instrucción, aplica marcos mentales y busca disrupción.",
        "Vicedecano Académico": "Eres Vicedecano. Tono institucional, riguroso, normativo y formal.",
        "Director de UCI": "Eres Intensivista. Prioriza la vida, guías clínicas, seguridad y eficiencia.",
        "Consultor Telesalud": "Eres experto en Salud Digital y Normativa (Ley 1419).",
        "Profesor Universitario": "Eres docente. Explica con pedagogía y ejemplos claros.",
        "Investigador Científico": "Eres metodólogo. Prioriza datos, evidencia y referencias.",
        "Mentor de Trading": "Eres Trader Institucional. Analiza estructura de mercado.",
        "Asistente Ejecutivo": "Eres eficiente, conciso y organizado."
    }
    
    # 3. AJUSTES
    c1, c2 = st.columns(2)
    with c1: modo_voz = st.toggle("🎙️ Voz", value=False)
    with c2: temp_val = st.slider("Creatividad", 0.0, 1.0, 0.2)

    st.markdown("---")

    # 4. HERRAMIENTAS DE PRODUCCIÓN (OCULTAS POR DEFECTO)
    with st.expander("🛠️ Herramientas de Producción", expanded=False):
        tab_office, tab_data, tab_visual = st.tabs(["📝 Docs", "📊 Datos", "🎨 Arte"])

        with tab_office:
            if st.button("📄 Generar Word", use_container_width=True):
                if st.session_state.messages:
                    with st.spinner("Redactando..."):
                        last_msg = st.session_state.messages[-1]["content"]
                        st.session_state.generated_word_clean = create_clean_docx(last_msg)
            if st.session_state.generated_word_clean: 
                st.download_button("📥 Bajar .docx", st.session_state.generated_word_clean, "informe.docx", use_container_width=True)
            
            st.markdown("---")
            uploaded_template = st.file_uploader("Plantilla PPTX", type=['pptx'], key="ppt_up")
            if st.button("📊 Generar PPTX", use_container_width=True):
                with st.spinner("Diseñando..."):
                    hist = "\n".join([m['content'] for m in st.session_state.messages[-5:]])
                    prompt = f"Analiza: {hist}. Genera JSON para PPTX. JSON: [{{'title':'T','type':'text','content':['A']}}]. SOLO JSON."
                    try:
                        genai.configure(api_key=api_key)
                        mod = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA)
                        res = mod.generate_content(prompt)
                        clean = res.text.replace("```json", "").replace("```", "").strip()
                        start = clean.find("["); end = clean.rfind("]") + 1
                        clean = clean[start:end]
                        tpl = uploaded_template if uploaded_template else None
                        st.session_state.generated_pptx = generate_pptx_from_data(json.loads(clean), tpl)
                    except Exception as e: st.error(f"Error PPT: {e}")
            if st.session_state.generated_pptx: 
                st.download_button("📥 Bajar .pptx", st.session_state.generated_pptx, "presentacion.pptx", use_container_width=True)

        with tab_data:
            if st.button("📗 Excel", use_container_width=True):
                with st.spinner("Procesando..."):
                    genai.configure(api_key=api_key)
                    mod = genai.GenerativeModel(MODELO_USADO)
                    prompt = f"Datos de: {st.session_state.messages[-1]['content']}. JSON: {{'Hoja1':[{{'Col':'Val'}}]}}. SOLO JSON."
                    try:
                        res = mod.generate_content(prompt).text
                        clean = res.replace("```json","").replace("```","").strip()
                        start = clean.find("{"); end = clean.rfind("}") + 1
                        clean = clean[start:end]
                        st.session_state.generated_excel = generate_excel_from_data(json.loads(clean))
                    except: st.error("Sin datos.")
            if st.session_state.generated_excel: 
                st.download_button("📥 Bajar .xlsx", st.session_state.generated_excel, "datos.xlsx", use_container_width=True)
            
            st.markdown("---")
            if st.button("📈 Gráfico", use_container_width=True):
                with st.spinner("Graficando..."):
                    hist = "\n".join([m['content'] for m in st.session_state.messages[-5:]])
                    prompt = f"Datos gráfico de: {hist}. JSON: {{'title':'T','labels':['A'],'datasets':[{{'label':'L','values':[10],'type':'bar'}}]}}. SOLO JSON."
                    try:
                        genai.configure(api_key=api_key)
                        res = genai.GenerativeModel(MODELO_USADO).generate_content(prompt).text
                        clean = res.replace("```json","").replace("```","").strip()
                        st.session_state.generated_chart = generate_advanced_chart(json.loads(clean))
                    except: st.error("Sin datos.")

        with tab_visual:
            if st.button("🎨 Diagrama", use_container_width=True):
                with st.spinner("Dibujando..."):
                    hist = "\n".join([m['content'] for m in st.session_state.messages[-5:]])
                    prompt = f"Diagrama MERMAID de: {hist}. Usa 'graph TD'. Solo código."
                    try:
                        genai.configure(api_key=api_key)
                        res = genai.GenerativeModel(MODELO_USADO).generate_content(prompt).text
                        st.session_state.generated_mermaid = res
                    except: pass

    # 5. INSUMOS Y CONTEXTO (OCULTO)
    with st.expander("📥 Insumos y Contexto", expanded=False):
        uploaded_docs = st.file_uploader("Documentos (PDF, Office)", accept_multiple_files=True)
        if uploaded_docs and st.button("Procesar Archivos", use_container_width=True):
            with st.spinner("Leyendo..."):
                text_acc = ""
                for doc in uploaded_docs:
                    try:
                        if doc.type == "application/pdf": text_acc += f"\n[PDF]\n" + get_pdf_text(doc)
                        elif "word" in doc.type: text_acc += f"\n[DOC]\n" + get_docx_text(doc)
                        elif "sheet" in doc.type: text_acc += f"\n[XLS]\n" + get_excel_text(doc)
                        elif "presentation" in doc.type: text_acc += f"\n[PPT]\n" + get_pptx_text(doc)
                    except: pass
                st.session_state.contexto_texto += text_acc
                st.success(f"{len(uploaded_docs)} leídos")
        
        st.divider()
        up_media = st.file_uploader("Multimedia (Audio/Video)", type=['mp4','mp3','png','jpg'])
        if up_media and api_key and st.button("Analizar Media", use_container_width=True):
            genai.configure(api_key=api_key)
            with st.spinner("Subiendo..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.'+up_media.name.split('.')[-1]) as tf:
                    tf.write(up_media.read()); tpath = tf.name
                mfile = genai.upload_file(path=tpath)
                while mfile.state.name == "PROCESSING": time.sleep(1); mfile = genai.get_file(mfile.name)
                st.session_state.archivo_multimodal = mfile
                st.success("Listo")
                os.remove(tpath)

        st.divider()
        u = st.text_input("YouTube URL")
        if u and st.button("Leer YT", use_container_width=True): 
            st.session_state.contexto_texto += "\n" + get_youtube_text(u)
            st.success("OK")
        
        w = st.text_input("Web URL")
        if w and st.button("Leer Web", use_container_width=True): 
            st.session_state.contexto_texto += "\n" + get_web_text(w)
            st.success("OK")

    st.markdown("---")
    # BACKUP Y RESET
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑️ Reset", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    with c2:
        st.download_button("💾 Backup", json.dumps(st.session_state.messages), "chat.json", use_container_width=True)

# ==========================================
# 🚀 ÁREA PRINCIPAL
# ==========================================
st.title(f"🤖 Agente V50: {rol}")
if not api_key: st.warning("⚠️ Ingrese API Key en la barra lateral"); st.stop()

# --- VISUALIZADORES ---
if st.session_state.generated_mermaid:
    st.subheader("🎨 Visualización")
    code = st.session_state.generated_mermaid.replace("```mermaid","").replace("```","").strip()
    try: plot_mermaid(code)
    except: st.code(code)
    if st.button("Cerrar Visualización"): st.session_state.generated_mermaid=None; st.rerun()

if st.session_state.generated_chart: 
    st.subheader("📊 Gráfico")
    st.pyplot(st.session_state.generated_chart)
    st.button("Cerrar Gráfico", on_click=lambda: st.session_state.update(generated_chart=None))

# --- CHAT ---
genai.configure(api_key=api_key)

# MODO VOZ
if modo_voz:
    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown("### 🎙️")
        audio = mic_recorder(start_prompt="🔴", stop_prompt="⏹️", key='recorder')
    with col2:
        if audio:
            st.audio(audio['bytes'])
            with st.spinner("Escuchando..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tf:
                    tf.write(audio['bytes']); tpath = tf.name
                mfile = genai.upload_file(path=tpath)
                while mfile.state.name == "PROCESSING": time.sleep(0.5); mfile = genai.get_file(mfile.name)
                
                ctx = st.session_state.contexto_texto
                instruccion = prompts_roles.get(rol, "Experto")
                prompt = f"Rol: {rol}. {instruccion}. Responde hablado. Contexto: {ctx[:30000]}"
                
                res = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA).generate_content([prompt, mfile])
                
                st.chat_message("assistant").markdown(res.text)
                st.session_state.messages.append({"role": "user", "content": "(Audio enviado)"})
                st.session_state.messages.append({"role": "assistant", "content": res.text})
                
                tts = gTTS(text=res.text, lang='es')
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                    tts.save(fp.name); st.audio(fp.name)
                os.remove(tpath)

# MODO TEXTO
for m in st.session_state.messages: 
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Escriba su instrucción..."):
    st.session_state.messages.append({"role": "user", "content": p})
    st.chat_message("user").markdown(p)
    
    with st.chat_message("assistant"):
        ctx = st.session_state.contexto_texto
        instruccion = prompts_roles.get(rol, "Experto")
        
        prompt_final = f"""
        ROL: {rol}
        DEFINICIÓN: {instruccion}
        HISTORIAL: {st.session_state.messages[-6:]}
        CONTEXTO DOCS: {ctx[:100000]}
        CONSULTA: {p}
        """
        
        contenido = [prompt_final]
        if st.session_state.archivo_multimodal: 
            contenido.insert(0, st.session_state.archivo_multimodal)
            contenido.append("(Analiza el archivo adjunto)")
        
        try:
            model = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA, generation_config={"temperature": temp_val})
            response = model.generate_content(contenido, stream=True)
            def stream():
                for chunk in response: yield chunk.text
            full_res = st.write_stream(stream)
            st.session_state.messages.append({"role": "assistant", "content": full_res})
        except Exception as e: st.error(f"Error: {e}")
