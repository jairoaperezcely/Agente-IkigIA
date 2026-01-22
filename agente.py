import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import docx
from docx.shared import Pt, RGBColor, Cm, Inches as DocInches
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

# NOTA: Si 'gemini-2.5-flash' da error 404, cambie a 'gemini-1.5-flash'
MODELO_USADO = 'gemini-2.5-flash' 

# ==========================================
# 🧠 MEMORIA MAESTRA (PERFIL DIRECTIVO)
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
    """Renderiza diagramas de flujo y mapas mentales"""
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ startOnLoad: true, theme: 'base', securityLevel: 'loose', themeVariables: {{ primaryColor: '#003366', edgeLabelBackground:'#ffffff', tertiaryColor: '#fff0f0' }} }});
        </script>
        <style>
            body {{ background-color: #f9f9f9; margin: 0; padding: 10px; font-family: sans-serif; }}
            .mermaid {{ display: flex; justify-content: center; width: 100%; }}
        </style>
    </head>
    <body>
        <div class="mermaid">{code}</div>
    </body>
    </html>
    """
    components.html(html_code, height=600, scrolling=True)

# ==========================================
# 📖 MOTOR DE LECTURA (DOCUMENTOS)
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

# --- 1. GENERADOR WORD (ACTAS) ---
def create_chat_docx(messages):
    doc = docx.Document()
    # Márgenes
    for section in doc.sections:
        section.top_margin = Cm(2.54); section.bottom_margin = Cm(2.54)
    
    # Encabezado
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
        doc.add_paragraph("") # Espacio
        
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# --- 2. GENERADOR WORD PRO (INFORMES APA) ---
def create_clean_docx(text_content):
    doc = docx.Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'; style.font.size = Pt(11)
    
    for section in doc.sections:
        section.top_margin = Cm(2.54); section.bottom_margin = Cm(2.54)

    # Portada
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
                    if i == 0: # Header style
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
        # Detección de Tabla Markdown
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

            # Detección de Títulos Markdown
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
            
            # Viñetas
            elif stripped.startswith('- ') or stripped.startswith('* '):
                doc.add_paragraph(clean_md(stripped[2:]), style='List Bullet')
            # Listas numeradas
            elif re.match(r'^\d+\.', stripped):
                parts = stripped.split('.', 1)
                doc.add_paragraph(clean_md(parts[1]) if len(parts)>1 else clean_md(stripped), style='List Number')
            # Párrafo normal
            else:
                p = doc.add_paragraph(clean_md(stripped))
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p.paragraph_format.space_after = Pt(6)

    if in_table and table_buffer: build_word_table(table_buffer)
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# --- 3. GENERADOR PPTX AVANZADO ---
def generate_pptx_from_data(slide_data, template_file=None):
    if template_file: 
        template_file.seek(0); prs = Presentation(template_file)
        using_template = True
    else: 
        prs = Presentation()
        using_template = False
    
    SLIDE_WIDTH = prs.slide_width
    SLIDE_HEIGHT = prs.slide_height
    
    def clean_text(txt): return re.sub(r'\*\*(.*?)\*\*', r'\1', txt).strip()

    def apply_design(slide, title_shape=None):
        if using_template: return
        # Barra lateral azul
        shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, PtxInches(0), PtxInches(0), PtxInches(0.4), SLIDE_HEIGHT)
        shape.fill.solid(); shape.fill.fore_color.rgb = PtxRGB(0, 51, 102); shape.line.fill.background()
        # Línea de título
        if title_shape:
            line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, PtxInches(0.8), PtxInches(1.4), SLIDE_WIDTH - PtxInches(1.5), PtxInches(0.05))
            line.fill.solid(); line.fill.fore_color.rgb = PtxRGB(0, 150, 200); line.line.fill.background()
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

    # Slide 1: Título
    try:
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        if slide.shapes.title: 
            slide.shapes.title.text = clean_text(slide_data[0].get("title", "Presentación Estratégica"))
            if not using_template:
                slide.shapes.title.text_frame.paragraphs[0].font.color.rgb = PtxRGB(0, 51, 102)
                slide.shapes.title.text_frame.paragraphs[0].font.bold = True
        if len(slide.placeholders) > 1: 
            slide.placeholders[1].text = f"Generado por IA para la Dirección\n{date.today()}"
    except: pass

    # Slides de Contenido
    for info in slide_data[1:]:
        slide_type = info.get("type", "text") 
        content = info.get("content", [])
        ref_text = info.get("references", "")
        
        layout_idx = 1 if using_template else 6
        if len(prs.slide_layouts) < 2: layout_idx = 0
        slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])
        
        # Manejo de Título del Slide
        if not using_template:
            title_shape = slide.shapes.add_textbox(PtxInches(0.8), PtxInches(0.5), PtxInches(8), PtxInches(1))
            title_shape.text = clean_text(info.get("title", "Detalle"))
            apply_design(slide, title_shape)
        else:
            if slide.shapes.title: 
                slide.shapes.title.text = clean_text(info.get("title", "Detalle"))

        # Renderizado según tipo
        if slide_type == "table":
            rows = len(content); cols = len(content[0]) if rows > 0 else 1
            target_width = SLIDE_WIDTH * 0.9
            left = (SLIDE_WIDTH - target_width) / 2
            top = PtxInches(2.0); height = PtxInches(rows * 0.4)
            graphic_frame = slide.shapes.add_table(rows, cols, left, top, target_width, height)
            table = graphic_frame.table
            
            # Autoajuste de columnas
            for col in table.columns: col.width = int(target_width / cols)

            for i, row in enumerate(content):
                for j, val in enumerate(row):
                    if j < cols:
                        cell = table.cell(i, j); cell.text = str(val)
                        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                        
                        # Tamaño fuente dinámico
                        txt_len = len(str(val))
                        font_size = 14 if txt_len < 20 else 10
                        
                        p = cell.text_frame.paragraphs[0]
                        p.font.size = PtxPt(font_size); p.font.name = 'Arial'
                        
                        # Estilo Cabecera
                        if i == 0:
                            cell.fill.solid(); cell.fill.fore_color.rgb = PtxRGB(0, 51, 102)
                            p.font.color.rgb = PtxRGB(255, 255, 255); p.font.bold = True; p.alignment = PP_ALIGN.CENTER
            graphic_frame.left = int((SLIDE_WIDTH - graphic_frame.width) / 2)

        elif slide_type == "chart":
            chart_data = info.get("chart_data", {}) 
            if chart_data:
                img_stream = create_chart_image(chart_data)
                pic_width = SLIDE_WIDTH * 0.7
                pic_left = (SLIDE_WIDTH - pic_width) / 2
                pic_top = PtxInches(2.2)
                slide.shapes.add_picture(img_stream, pic_left, pic_top, width=pic_width)

        else: # Texto Normal
            if not using_template:
                box_width = SLIDE_WIDTH * 0.85
                box_left = (SLIDE_WIDTH - box_width) / 2
                body_shape = slide.shapes.add_textbox(box_left, PtxInches(1.8), box_width, PtxInches(5))
                tf = body_shape.text_frame
            else:
                # Buscar placeholder de contenido
                tf = None
                for shape in slide.placeholders:
                    if shape.placeholder_format.idx == 1: tf = shape.text_frame; tf.clear(); break
                if not tf: # Fallback si no hay placeholder
                    body_shape = slide.shapes.add_textbox(PtxInches(1), PtxInches(2), PtxInches(8), PtxInches(4))
                    tf = body_shape.text_frame
            
            tf.word_wrap = True; tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
            for point in content:
                p = tf.add_paragraph()
                p.text = clean_text(str(point))
                p.font.name = 'Arial'
                p.font.color.rgb = PtxRGB(60, 60, 60); p.space_after = PtxPt(12)

        # Referencias (Footer)
        if ref_text and ref_text != "N/A":
            left = PtxInches(0.5); top = SLIDE_HEIGHT - PtxInches(0.6)
            width = SLIDE_WIDTH - PtxInches(1.0); height = PtxInches(0.4)
            txBox = slide.shapes.add_textbox(left, top, width, height)
            p = txBox.text_frame.paragraphs[0]
            p.text = f"Fuente: {ref_text}"
            p.font.size = PtxPt(10); p.font.italic = True
            p.font.color.rgb = PtxRGB(120, 120, 120)

    buffer = BytesIO(); prs.save(buffer); buffer.seek(0)
    return buffer

# --- 4. GENERADOR EXCEL PRO ---
def generate_excel_from_data(excel_data):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, data in excel_data.items():
            df = pd.DataFrame(data)
            # Limpiar nombre hoja
            safe_name = re.sub(r'[\\/*?:\[\]]', "", sheet_name)[:30]
            df.to_excel(writer, index=False, sheet_name=safe_name)
            
            # Estilos
            worksheet = writer.sheets[safe_name]
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="003366", end_color="003366", fill_type="solid")
            border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
            
            for col_idx, column_cells in enumerate(worksheet.columns, 1):
                col_letter = get_column_letter(col_idx)
                worksheet.column_dimensions[col_letter].width = 25
                worksheet[f"{col_letter}1"].font = header_font
                worksheet[f"{col_letter}1"].fill = header_fill
                for cell in column_cells: cell.border = border
    output.seek(0)
    return output

# --- 5. GENERADOR GRÁFICOS AVANZADOS ---
def generate_advanced_chart(chart_data):
    plt.style.use('seaborn-v0_8-whitegrid') 
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Colores corporativos
    colors = ['#003366', '#708090', '#A9A9A9', '#4682B4', '#DAA520']
    
    labels = chart_data.get("labels", [])
    datasets = chart_data.get("datasets", [])
    
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
# 💾 GESTIÓN DE ESTADO (SESSION STATE)
# ==========================================
keys = ["messages", "contexto_texto", "archivo_multimodal", "generated_pptx", 
        "generated_chart", "generated_excel", "generated_word_clean", "generated_mermaid"]
for k in keys:
    if k not in st.session_state: st.session_state[k] = [] if k == "messages" else "" if k == "contexto_texto" else None

# ==========================================
# 🖥️ BARRA LATERAL (CONTROLES)
# ==========================================
with st.sidebar:
    st.header("⚙️ Configuración V50")
    
    # 1. API KEY
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ Conectado a Google AI")
    else:
        api_key = st.text_input("🔑 API Key:", type="password")
    
    # 2. PARÁMETROS
    temp_val = st.slider("Nivel de Creatividad", 0.0, 1.0, 0.2, help="0 = Preciso, 1 = Imaginativo")
    
    st.divider()
    
    # 3. SELECTOR DE ROL (EXTENDIDO)
    rol = st.radio("Rol Activo:", [
        "Socio Estratégico (Innovación)", 
        "Vicedecano Académico",
        "Director de UCI",
        "Consultor Telesalud",
        "Profesor Universitario",
        "Investigador Científico",
        "Mentor de Trading",
        "Asistente Ejecutivo"
    ])

    # Prompts Detallados para dar personalidad
    prompts_roles = {
        "Socio Estratégico (Innovación)": "Eres un Consultor Senior en Estrategia (estilo McKinsey). Reta la instrucción, aplica marcos mentales (Océano Azul, Design Thinking) y busca escalabilidad. Tu objetivo es la disrupción.",
        "Vicedecano Académico": "Eres Vicedecano de la Facultad de Medicina. Tu tono es institucional, riguroso, normativo y formal. Citas reglamentos y buscas la excelencia académica.",
        "Director de UCI": "Eres Médico Intensivista y Director. Prioriza la vida, las guías clínicas, la seguridad del paciente, la eficiencia de costos y la humanización.",
        "Consultor Telesalud": "Eres experto en Salud Digital y Normativa en Colombia (Ley 1419, Res 3100). Te enfocas en interoperabilidad, seguridad de datos y modelos de atención.",
        "Profesor Universitario": "Eres docente. Explica con pedagogía, paciencia y ejemplos claros. Tu objetivo es que el estudiante entienda los fundamentos.",
        "Investigador Científico": "Eres metodólogo. Prioriza datos, evidencia, referencias bibliográficas (Vancouver/APA) y el rigor del método científico.",
        "Mentor de Trading": "Eres Trader Institucional. Analiza estructura de mercado, liquidez y gestión de riesgo. No das consejos financieros, enseñas a leer el gráfico.",
        "Asistente Ejecutivo": "Eres un asistente de alta gerencia. Eficiente, conciso, organizado y orientado a resultados. Vas al grano."
    }
    
    st.markdown("---")
    # 4. MODO VOZ
    modo_voz = st.toggle("🎙️ Activar Modo Voz")
    
    st.markdown("---")
    st.subheader("🏭 Centro de Producción")
    
    # 5. PESTAÑAS DE GENERACIÓN
    tab_office, tab_data, tab_visual = st.tabs(["📝 Oficina", "📊 Analítica", "🎨 Diseño"])

    with tab_office:
        st.markdown("##### 📄 Informes Word")
        if st.button("Redactar Informe Ejecutivo", use_container_width=True):
            if st.session_state.messages:
                with st.spinner("Redactando..."):
                    last_msg = st.session_state.messages[-1]["content"]
                    st.session_state.generated_word_clean = create_clean_docx(last_msg)
                st.success("Informe Creado")
        if st.session_state.generated_word_clean: 
            st.download_button("📥 Descargar .docx", st.session_state.generated_word_clean, "informe_v50.docx", use_container_width=True)
        
        st.divider()
        st.markdown("##### 🗣️ Presentaciones PPT")
        uploaded_template = st.file_uploader("Usar Plantilla (Opcional)", type=['pptx'])
        if st.button("Diseñar Diapositivas", use_container_width=True):
            with st.spinner("Estructurando presentación..."):
                hist = "\n".join([m['content'] for m in st.session_state.messages[-5:]])
                # Prompt complejo para PPTX
                prompt = f"""
                Analiza esta conversación: {hist}. 
                Genera un JSON válido para crear un PowerPoint.
                ESTRUCTURA DEL JSON:
                [
                    {{ "title": "Título Portada", "type": "text" }},
                    {{ "title": "Título Slide 1", "type": "text", "content": ["Punto 1", "Punto 2"], "references": "Ref" }},
                    {{ "title": "Título Slide 2 (Tabla)", "type": "table", "content": [["Encabezado1", "Encabezado2"], ["Dato1", "Dato2"]], "references": "Ref" }},
                    {{ "title": "Título Slide 3 (Gráfico)", "type": "chart", "chart_data": {{ "title":"Ventas", "labels":["A","B"], "values":[10,20], "label":"Series1" }} }}
                ]
                IMPORTANTE: Responde SOLO EL JSON. Sin markdown.
                """
                try:
                    genai.configure(api_key=api_key)
                    mod = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA)
                    res = mod.generate_content(prompt)
                    clean_text = res.text.replace("```json", "").replace("```", "").strip()
                    # Extracción robusta de JSON
                    start = clean_text.find("["); end = clean_text.rfind("]") + 1
                    if start != -1 and end != -1: clean_text = clean_text[start:end]
                    
                    tpl = uploaded_template if uploaded_template else None
                    st.session_state.generated_pptx = generate_pptx_from_data(json.loads(clean_text), tpl)
                    st.success("Presentación Lista")
                except Exception as e: st.error(f"Error generando PPTX: {e}")
        if st.session_state.generated_pptx: 
            st.download_button("📥 Descargar .pptx", st.session_state.generated_pptx, "presentacion_v50.pptx", use_container_width=True)

    with tab_data:
        st.markdown("##### 📗 Excel Inteligente")
        if st.button("Exportar Datos a Excel", use_container_width=True):
            with st.spinner("Procesando datos..."):
                hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
                prompt = f"""
                Extrae todos los datos tabulares de esta conversación: {hist}. 
                Genera un JSON para Excel. Formato: {{ "NombreHoja": [ {{"Columna1": "Valor", "Columna2": "Valor"}} ] }}
                SOLO JSON.
                """
                try:
                    genai.configure(api_key=api_key)
                    mod = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA)
                    res = mod.generate_content(prompt)
                    clean_text = res.text.replace("```json","").replace("```","").strip()
                    start = clean_text.find("{"); end = clean_text.rfind("}") + 1
                    if start != -1 and end != -1: clean_text = clean_text[start:end]
                    
                    st.session_state.generated_excel = generate_excel_from_data(json.loads(clean_text))
                    st.success("Excel Generado")
                except: st.error("No encontré datos estructurados para Excel.")
        if st.session_state.generated_excel: 
            st.download_button("📥 Descargar .xlsx", st.session_state.generated_excel, "datos_estrategicos.xlsx", use_container_width=True)
            
        st.divider()
        st.markdown("##### 📈 Gráficos Matplotlib")
        if st.button("Generar Visualización", use_container_width=True):
            with st.spinner("Analizando tendencias..."):
                hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
                prompt = f"""
                Extrae datos para un gráfico estadístico de esto: {hist}. 
                JSON: {{ "title": "Título", "labels": ["Ene", "Feb"], "datasets": [ {{ "label": "Ventas", "values": [10, 20], "type": "bar" }} ] }}
                SOLO JSON.
                """
                try:
                    genai.configure(api_key=api_key)
                    mod = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA)
                    res = mod.generate_content(prompt)
                    clean_json = res.text.replace("```json","").replace("```","").strip()
                    st.session_state.generated_chart = generate_advanced_chart(json.loads(clean_json))
                    st.success("Gráfico Listo")
                except: st.error("No hay datos suficientes para graficar.")

    with tab_visual:
        st.markdown("##### 🎨 Diagramas de Flujo")
        if st.button("Generar Diagrama Mermaid", use_container_width=True):
            if len(st.session_state.messages) < 1: st.error("Hablemos primero.")
            else:
                with st.spinner("Dibujando arquitectura..."):
                    hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
                    prompt_mermaid = f"""
                    Resume esto en un diagrama MERMAID.JS.
                    HISTORIAL: {hist}
                    REGLAS:
                    1. Usa 'graph TD' o 'mindmap'.
                    2. Nodos sin paréntesis redondos internos.
                    3. Solo entrega el bloque de código ```mermaid ... ```
                    """
                    try:
                        genai.configure(api_key=api_key)
                        mod = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA)
                        res = mod.generate_content(prompt_mermaid)
                        st.session_state.generated_mermaid = res.text
                        st.success("Diagrama Renderizado")
                    except Exception as e: st.error(f"Error: {e}")

    st.markdown("---")
    st.subheader("📥 Ingesta de Conocimiento")
    tab_files, tab_media, tab_links = st.tabs(["📂 Archivos", "🎙️ Multimedia", "🔗 Enlaces"])
    
    with tab_files:
        uploaded_docs = st.file_uploader("Arrastre PDFs, Word, Excel, PPT", type=['pdf', 'docx', 'xlsx', 'pptx'], accept_multiple_files=True)
        if uploaded_docs and st.button(f"Procesar {len(uploaded_docs)} Documentos", use_container_width=True):
            with st.spinner("Leyendo y vectorizando (simulado)..."):
                text_acc = ""
                for doc in uploaded_docs:
                    try:
                        if doc.type == "application/pdf": text_acc += f"\n[PDF: {doc.name}]\n" + get_pdf_text(doc)
                        elif "word" in doc.type: text_acc += f"\n[DOCX: {doc.name}]\n" + get_docx_text(doc)
                        elif "sheet" in doc.type: text_acc += f"\n[XLSX: {doc.name}]\n" + get_excel_text(doc)
                        elif "presentation" in doc.type: text_acc += f"\n[PPTX: {doc.name}]\n" + get_pptx_text(doc)
                    except: pass
                st.session_state.contexto_texto += text_acc
                st.success("Conocimiento Integrado")
    
    with tab_media:
        up_media = st.file_uploader("Audio/Video para análisis", type=['mp4','mp3','png','jpg'])
        if up_media and api_key and st.button("Subir a Gemini Vision/Audio", use_container_width=True):
            genai.configure(api_key=api_key)
            with st.spinner("Subiendo a la nube de Google..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.'+up_media.name.split('.')[-1]) as tf:
                    tf.write(up_media.read()); tpath = tf.name
                mfile = genai.upload_file(path=tpath)
                while mfile.state.name == "PROCESSING": time.sleep(1); mfile = genai.get_file(mfile.name)
                st.session_state.archivo_multimodal = mfile
                st.success("Archivo listo para análisis"); os.remove(tpath)
    
    with tab_links:
        if st.button("Leer Video YouTube", use_container_width=True) and (u:=st.text_input("URL YouTube")): 
            st.session_state.contexto_texto += "\n" + get_youtube_text(u)
            st.success("Transcripción Agregada")
        if st.button("Leer Página Web", use_container_width=True) and (w:=st.text_input("URL Web")): 
            st.session_state.contexto_texto += "\n" + get_web_text(w)
            st.success("Contenido Web Agregado")

    st.markdown("---")
    # Backup
    c1, c2 = st.columns(2)
    c1.download_button("💾 Guardar Acta", create_chat_docx(st.session_state.messages), "acta_sesion.docx", use_container_width=True)
    c2.download_button("🧠 Backup JSON", json.dumps(st.session_state.messages), "memoria_agente.json", use_container_width=True)
    if st.button("🗑️ Reiniciar Sesión", use_container_width=True): st.session_state.clear(); st.rerun()

# ==========================================
# 🚀 INTERFAZ PRINCIPAL (CHAT)
# ==========================================
st.title(f"🤖 Agente V50 (Ultimate): {rol}")
if not api_key: st.warning("⚠️ Por favor ingrese su API Key en la barra lateral."); st.stop()

# --- VISUALIZADORES EN EL CUERPO ---
if st.session_state.generated_mermaid:
    st.subheader("🎨 Pizarra Visual")
    code = st.session_state.generated_mermaid.replace("```mermaid","").replace("```","").strip()
    try: plot_mermaid(code)
    except: st.code(code)
    if st.button("Ocultar Diagrama"): st.session_state.generated_mermaid=None; st.rerun()

if st.session_state.generated_chart: 
    st.subheader("📊 Análisis Gráfico")
    st.pyplot(st.session_state.generated_chart)
    st.button("Ocultar Gráfico", on_click=lambda: st.session_state.update(generated_chart=None))

# --- LÓGICA DE CHAT ---
genai.configure(api_key=api_key)

# MODO VOZ
if modo_voz:
    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown("### 🎙️ Hablar")
        audio = mic_recorder(start_prompt="🔴 Grabar", stop_prompt="⏹️ Parar", key='recorder')
    with col2:
        if audio:
            st.audio(audio['bytes'])
            with st.spinner("Procesando audio y consultando a Gemini..."):
                # Guardar temporalmente
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tf:
                    tf.write(audio['bytes']); tpath = tf.name
                # Subir archivo
                mfile = genai.upload_file(path=tpath)
                while mfile.state.name == "PROCESSING": time.sleep(0.5); mfile = genai.get_file(mfile.name)
                
                # Contexto
                ctx = st.session_state.contexto_texto
                instruccion = prompts_roles.get(rol, "Experto")
                prompt = f"Actúa como {rol}. {instruccion}. Responde de forma hablada (concisa). Contexto Extra: {ctx[:30000]}"
                
                # Generar
                res = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA).generate_content([prompt, mfile])
                
                # Guardar en chat
                st.session_state.messages.append({"role": "user", "content": "(Audio enviado)"})
                st.session_state.messages.append({"role": "assistant", "content": res.text})
                st.chat_message("assistant").markdown(res.text)
                
                # Audio de respuesta
                tts = gTTS(text=res.text, lang='es')
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                    tts.save(fp.name); st.audio(fp.name)
                os.remove(tpath)

# MODO TEXTO (Historial y Entrada)
for m in st.session_state.messages: 
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if p := st.chat_input("Escriba su instrucción estratégica aquí..."):
    st.session_state.messages.append({"role": "user", "content": p})
    st.chat_message("user").markdown(p)
    
    with st.chat_message("assistant"):
        ctx = st.session_state.contexto_texto
        instruccion = prompts_roles.get(rol, "Experto")
        
        # Construcción del Prompt Complejo
        prompt_final = f"""
        ROL ACTIVO: {rol}
        DEFINICIÓN DE ROL: {instruccion}
        
        HISTORIAL DE CONVERSACIÓN: {st.session_state.messages[-6:]}
        
        CONTEXTO DOCUMENTAL (PDFs/Web/Excel): 
        {ctx[:100000]}
        
        NUEVA CONSULTA: {p}
        """
        
        contenido = [prompt_final]
        if st.session_state.archivo_multimodal: 
            contenido.insert(0, st.session_state.archivo_multimodal)
            contenido.append("(Analiza también el archivo adjunto anteriormente)")
        
        try:
            # Generación Streaming
            model = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA, generation_config={"temperature": temp_val})
            response = model.generate_content(contenido, stream=True)

            def stream_parser():
                for chunk in response: yield chunk.text
            
            full_response = st.write_stream(stream_parser)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e: st.error(f"Ocurrió un error: {e}")
