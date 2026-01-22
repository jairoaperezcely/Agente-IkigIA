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
# 🧠 MEMORIA MAESTRA (AQUÍ ENTRENA A SU AGENTE)
# ==========================================
# Escriba aquí todo lo que quiere que el Agente sepa SIEMPRE sobre usted.
MEMORIA_MAESTRA = """
# ==========================================
# 🧠 MEMORIA MAESTRA (PERFIL HOLÍSTICO V3.0)
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

MIS ÁREAS DE INTERÉS ACTUALES:
1. Salud Digital con Propósito: Telesalud, Telemedicina e IA, pero siempre con visión bioética y social.
2. Gestión Académica y Hospitalaria: Liderazgo de equipos de alto rendimiento.
3. Trading e Inversiones: Estoy en proceso de aprendizaje activo sobre mercados financieros.

INSTRUCCIONES PARA EL ASISTENTE (CÓMO DEBES RESPONDER):
1. TONO: Estratégico, Empático y Visionario. Combina la rigurosidad científica (Epidemiología) con la sensibilidad humana (Bioética/Humanización).
2. VISIÓN SISTÉMICA: Cuando hablemos de salud, no te quedes en lo clínico; considera el impacto en el paciente, la familia y el sistema de salud.
3. FORMATO: Respuestas estructuradas que aporten valor inmediato. Usa tablas para comparar estrategias o conceptos.
4. MODO APRENDIZ (TRADING): Si pregunto sobre Trading, asume que estoy aprendiendo: explícame conceptos técnicos con claridad, usando analogías si es útil, y ayúdame a analizar riesgos.
5. RIGOR: Cita normatividad colombiana y evidencia científica cuando sea pertinente.
"""

# ==========================================
# CONFIGURACIÓN GLOBAL
# ==========================================
st.set_page_config(page_title="Agente IkigAI V42", page_icon="🧠", layout="wide")
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
# FUNCIONES DE LECTURA (CON CACHÉ)
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
    except Exception as e: return f"Error Excel: {e}"

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
    except Exception as e: return f"Error PPTX: {e}"

# ==========================================
# FUNCIONES DE GENERACIÓN (OUTPUT)
# ==========================================

# 1. WORD ACTA
def create_chat_docx(messages):
    doc = docx.Document()
    for section in doc.sections:
        section.top_margin = Cm(2.54); section.bottom_margin = Cm(2.54)
    
    header = doc.sections[0].header
    p = header.paragraphs[0]
    p.text = f"CONFIDENCIAL | {date.today()}"
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    t = doc.add_heading('BITÁCORA DE SESIÓN', 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("_" * 40).alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    def clean_chat(txt): 
        txt = re.sub(r'^#+\s*', '', txt, flags=re.MULTILINE)
        return txt.replace("**", "").replace("__", "").replace("`", "").strip()

    for msg in messages:
        role = "USUARIO" if msg["role"] == "user" else "ASISTENTE"
        p_head = doc.add_paragraph()
        run = p_head.add_run(f"[{role}]")
        run.bold = True
        run.font.color.rgb = RGBColor(0, 51, 102) if role == "ASISTENTE" else RGBColor(80, 80, 80)
        p_msg = doc.add_paragraph(clean_chat(msg["content"]))
        p_msg.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_paragraph("")
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# 2. WORD DOCUMENTO PRO (APA)
def create_clean_docx(text_content):
    doc = docx.Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'; style.font.size = Pt(11)
    
    for section in doc.sections:
        section.top_margin = Cm(2.54); section.bottom_margin = Cm(2.54)

    for _ in range(3): doc.add_paragraph("")
    title = doc.add_paragraph("INFORME EJECUTIVO")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = title.runs[0]
    run_title.bold = True; run_title.font.size = Pt(24); run_title.font.color.rgb = RGBColor(0, 51, 102)
    doc.add_paragraph("__________________________________________________").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"\nFecha: {date.today().strftime('%d/%m/%Y')}").alignment = WD_ALIGN_PARAGRAPH.CENTER
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
    table_buffer = []; in_table = False; is_biblio = False

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
                
                if "referencia" in clean_title.lower() or "bibliografía" in clean_title.lower():
                    is_biblio = True
                else: is_biblio = False

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
                if is_biblio:
                    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    p.paragraph_format.left_indent = Cm(1.27) 
                    p.paragraph_format.first_line_indent = Cm(-1.27)
                else: p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p.paragraph_format.space_after = Pt(6)

    if in_table and table_buffer: build_word_table(table_buffer)
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# 3. PPTX PRO (STRICT GEOMETRY)
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
        shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, PtxInches(0), PtxInches(0), PtxInches(0.4), SLIDE_HEIGHT)
        shape.fill.solid(); shape.fill.fore_color.rgb = PtxRGB(0, 51, 102); shape.line.fill.background()
        if title_shape:
            line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, PtxInches(0.8), PtxInches(1.4), SLIDE_WIDTH - PtxInches(1.5), PtxInches(0.05))
            line.fill.solid(); line.fill.fore_color.rgb = PtxRGB(0, 150, 200); line.line.fill.background()
            title_shape.text_frame.word_wrap = True 
            title_shape.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
            title_shape.text_frame.paragraphs[0].font.name = 'Arial'
            title_shape.text_frame.paragraphs[0].font.bold = True
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
            slide.shapes.title.text = clean_text(slide_data[0].get("title", "Presentación"))
            slide.shapes.title.text_frame.word_wrap = True
            slide.shapes.title.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
            if not using_template:
                slide.shapes.title.text_frame.paragraphs[0].font.color.rgb = PtxRGB(0, 51, 102)
                slide.shapes.title.text_frame.paragraphs[0].font.bold = True
        if len(slide.placeholders) > 1: slide.placeholders[1].text = f"{date.today()}"
    except: slide = prs.slides.add_slide(prs.slide_layouts[6])

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
            if slide.shapes.title: 
                slide.shapes.title.text = clean_text(info.get("title", "Detalle"))
                slide.shapes.title.text_frame.word_wrap = True
                slide.shapes.title.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE

        if slide_type == "table":
            rows = len(content); cols = len(content[0]) if rows > 0 else 1
            target_width = SLIDE_WIDTH * 0.9
            left = (SLIDE_WIDTH - target_width) / 2
            top = PtxInches(2.0); height = PtxInches(rows * 0.4)
            graphic_frame = slide.shapes.add_table(rows, cols, left, top, target_width, height)
            table = graphic_frame.table
            single_col_width = int(target_width / cols)
            for col in table.columns: col.width = single_col_width

            for i, row in enumerate(content):
                for j, val in enumerate(row):
                    if j < cols:
                        cell = table.cell(i, j); cell.text = str(val)
                        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                        txt_len = len(str(val))
                        font_size = 14
                        if txt_len > 50: font_size = 10
                        elif txt_len > 20: font_size = 12
                        p = cell.text_frame.paragraphs[0]
                        p.font.size = PtxPt(font_size); p.font.name = 'Arial'
                        if i == 0:
                            cell.fill.solid(); cell.fill.fore_color.rgb = PtxRGB(0, 51, 102)
                            p.font.color.rgb = PtxRGB(255, 255, 255); p.font.bold = True; p.alignment = PP_ALIGN.CENTER
            graphic_frame.left = int((SLIDE_WIDTH - graphic_frame.width) / 2)

        elif slide_type == "chart":
            chart_data = info.get("chart_data", {}) 
            if chart_data:
                img_stream = create_chart_image(chart_data)
                pic_width = SLIDE_WIDTH * 0.65
                pic_left = (SLIDE_WIDTH - pic_width) / 2
                pic_top = PtxInches(2.2)
                slide.shapes.add_picture(img_stream, pic_left, pic_top, width=pic_width)

        else:
            if not using_template:
                box_width = SLIDE_WIDTH * 0.85
                box_left = (SLIDE_WIDTH - box_width) / 2
                body_shape = slide.shapes.add_textbox(box_left, PtxInches(1.8), box_width, PtxInches(5))
                tf = body_shape.text_frame
            else:
                for shape in slide.placeholders:
                    if shape.placeholder_format.idx == 1: tf = shape.text_frame; tf.clear(); break
            
            tf.word_wrap = True; tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
            for point in content:
                p = tf.add_paragraph()
                p.text = clean_text(str(point))
                p.font.name = 'Arial'
                p.font.color.rgb = PtxRGB(60, 60, 60); p.space_after = PtxPt(12)

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

# 4. EXCEL PRO
def generate_excel_from_data(excel_data):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, data in excel_data.items():
            df = pd.DataFrame(data)
            df.to_excel(writer, index=False, sheet_name=sheet_name[:30])
            worksheet = writer.sheets[sheet_name[:30]]
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="003366", end_color="003366", fill_type="solid")
            border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
            for col_idx, column_cells in enumerate(worksheet.columns, 1):
                col_letter = get_column_letter(col_idx)
                worksheet.column_dimensions[col_letter].width = 22
                worksheet[f"{col_letter}1"].font = header_font
                worksheet[f"{col_letter}1"].fill = header_fill
                for cell in column_cells: cell.border = border
    output.seek(0)
    return output

# 5. GRÁFICO PRO
def generate_advanced_chart(chart_data):
    plt.style.use('seaborn-v0_8-whitegrid') 
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ['#003366', '#708090', '#A9A9A9', '#4682B4']
    labels = chart_data.get("labels", [])
    datasets = chart_data.get("datasets", [])
    for i, ds in enumerate(datasets):
        color = colors[i % len(colors)]
        if len(ds["values"]) == len(labels):
            if ds.get("type") == "line": ax.plot(labels, ds["values"], label=ds["label"], marker='o', color=color, linewidth=2.5)
            else: 
                bars = ax.bar(labels, ds["values"], label=ds["label"], color=color, alpha=0.9)
                ax.bar_label(bars, padding=3, fmt='%.1f')
    ax.legend(frameon=False)
    ax.set_title(chart_data.get("title", "Análisis"), fontsize=14, fontweight='bold', color='#333333')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False); ax.spines['left'].set_visible(False)
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
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
# ESTADO
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
# BARRA LATERAL (V42 - DEFINITIVA)
# ==========================================
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # --- AUTO LOGIN ---
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ Login Automático")
    else:
        api_key = st.text_input("🔑 API Key:", type="password")
    
    # --- GOOGLE SEARCH (Super Poder Opcional) ---
    usar_google_search = st.toggle("🌐 Búsqueda Google (En Vivo)")
    
    temp_val = st.slider("Creatividad", 0.0, 1.0, 0.2)
    st.divider()
    
    rol = st.radio("Rol:", [
        "Socio Estratégico (Innovación)", 
        "Vicedecano Académico",
        "Director de UCI",
        "Consultor Telesalud",
        "Profesor Universitario",
        "Investigador Científico",
        "Mentor de Trading",
        "Asistente Personal"
    ])

    prompts_roles = {
        "Socio Estratégico (Innovación)": """
            Eres un Consultor Senior en Estrategia y Transformación (estilo McKinsey/IDEO).
            TU MISIÓN: No solo obedezcas la instrucción; RETALA y MEJÓRALA.
            1. Aplica marcos mentales: Océano Azul, Design Thinking, Kotter (Gestión del Cambio).
            2. Busca la escalabilidad y la diferenciación radical.
            3. Si el usuario pide algo básico, entrégalo, pero añade una sección de "Visión Disruptiva".
            4. CITAS APA: Siempre que des datos, usa formato APA (Autor, Año). Incluye una sección de 'Referencias Bibliográficas' al final.
            ACTITUD: Proactiva, visionaria y analítica.
        """,
        "Vicedecano Académico": "Eres Vicedecano. Tu tono es institucional, riguroso, normativo y formal. Citas reglamentos y buscas la excelencia académica.",
        "Director de UCI": "Eres Médico Intensivista. Prioriza la vida, las guías clínicas, la seguridad del paciente y la toma de decisiones basada en evidencia.",
        "Consultor Telesalud": "Eres experto en Salud Digital, Leyes (Colombia) y Tecnología. Conoces la normativa de habilitación y protección de datos.",
        "Profesor Universitario": "Eres docente. Explica con pedagogía, paciencia y ejemplos claros. Tu objetivo es que el estudiante entienda los fundamentos.",
        "Investigador Científico": "Eres metodólogo. Prioriza datos, referencias bibliográficas (Vancouver/APA) y el rigor del método científico.",
        "Mentor de Trading": "Eres Trader Institucional. Analiza estructura de mercado, liquidez y gestión de riesgo. No das consejos financieros, enseñas a leer el mercado.",
        "Asistente Personal": "Eres un asistente ejecutivo eficiente, conciso y organizado. Vas directo al grano."
    }
    
    st.markdown("---")
    modo_voz = st.toggle("🎙️ Modo Voz")
    
    st.markdown("---")
    st.subheader("🏭 Centro de Producción")
    
    tab_office, tab_data, tab_visual = st.tabs(["📝 Oficina", "📊 Analítica", "🎨 Diseño"])

    with tab_office:
        st.markdown("##### 📄 Informes")
        if st.button("Generar Word (Elegante)", use_container_width=True):
            if st.session_state.messages:
                last_msg = st.session_state.messages[-1]["content"]
                st.session_state.generated_word_clean = create_clean_docx(last_msg)
                st.success("¡Listo!")
        if st.session_state.generated_word_clean: 
            st.download_button("📥 Bajar Informe", st.session_state.generated_word_clean, "informe_ejecutivo.docx", use_container_width=True)
        
        st.divider()
        st.markdown("##### 🗣️ Presentaciones")
        uploaded_template = st.file_uploader("Plantilla PPTX", type=['pptx'])
        if st.button("Generar PPTX (Multimedia)", use_container_width=True):
            with st.spinner("Diseñando..."):
                hist = "\n".join([m['content'] for m in st.session_state.messages[-5:]])
                prompt = f"""
                Analiza: {hist}. Genera JSON para PPTX.
                TIPOS DE SLIDE (usa el campo 'type'):
                1. 'text': Para puntos normales.
                2. 'table': Si hay datos comparativos (Matriz de listas).
                3. 'chart': Si hay estadísticas (Bar Chart).
                
                CAMPO 'references': Si usas datos, agrega la cita APA breve (ej: 'Minsalud, 2024') en este campo. Si no, pon 'N/A'.
                
                FORMATOS:
                - TEXT: {{'type':'text', 'title':'T', 'content':['A','B'], 'references':'Autor (Año)'}}
                - TABLE: {{'type':'table', 'title':'T', 'content':[['H1','H2'],['V1','V2']], 'references':'Autor (Año)'}}
                - CHART: {{'type':'chart', 'title':'T', 'chart_data': {{'labels':['A','B'], 'values':[10,20], 'label':'Ventas'}}, 'references':'Autor (Año)'}}
                
                IMPORTANTE: Responde SOLO el JSON.
                """
                try:
                    # CONFIGURACIÓN DINÁMICA DE HERRAMIENTAS
                    tools_config = []
                    if usar_google_search:
                        tools_config = [{'google_search_retrieval': {}}]
                    
                    genai.configure(api_key=api_key)
                    
                    # --- AQUÍ INYECTAMOS LA MEMORIA MAESTRA ---
                    # El system_instruction es la clave del entrenamiento
                    mod = genai.GenerativeModel(
                        MODELO_USADO, 
                        tools=tools_config,
                        system_instruction=MEMORIA_MAESTRA
                    )
                    res = mod.generate_content(prompt)
                    
                    clean_text = res.text
                    if "```json" in clean_text:
                        clean_text = clean_text.replace("```json", "").replace("```", "").strip()
                    elif "```" in clean_text:
                        clean_text = clean_text.replace("```", "").strip()
                        
                    start = clean_text.find("["); end = clean_text.rfind("]") + 1
                    if start != -1 and end != -1: clean_text = clean_text[start:end]
                    
                    tpl = uploaded_template if uploaded_template else None
                    st.session_state.generated_pptx = generate_pptx_from_data(json.loads(clean_text), tpl)
                    st.success("¡Listo!")
                except Exception as e: st.error(f"Error: {e}")
        if st.session_state.generated_pptx: 
            st.download_button("📥 Bajar PPTX", st.session_state.generated_pptx, "presentacion.pptx", use_container_width=True)

    with tab_data:
        st.markdown("##### 📗 Excel")
        if st.button("Generar Excel (Pro)", use_container_width=True):
            with st.spinner("Calculando..."):
                hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
                prompt = f"Analiza: {hist}. JSON Excel: {{'Hoja1': [{{'ColumnaA':'Dato1', 'ColumnaB':'Dato2'}}]}}"
                try:
                    genai.configure(api_key=api_key)
                    mod = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA)
                    res = mod.generate_content(prompt)
                    clean_text = res.text.replace("```json","").replace("```","").strip()
                    start = clean_text.find("{"); end = clean_text.rfind("}") + 1
                    if start != -1 and end != -1: clean_text = clean_text[start:end]
                    st.session_state.generated_excel = generate_excel_from_data(json.loads(clean_text))
                    st.success("¡Listo!")
                except: st.error("Error Excel.")
        if st.session_state.generated_excel: 
            st.download_button("📥 Bajar Excel", st.session_state.generated_excel, "datos_pro.xlsx", use_container_width=True)
            
        st.divider()
        st.markdown("##### 📈 Gráficos")
        if st.button("Generar Gráfico", use_container_width=True):
            with st.spinner("Graficando..."):
                hist = "\n".join([m['content'] for m in st.session_state.messages[-10:]])
                prompt = f"Datos de: {hist}. JSON: {{'title':'T','labels':['A'],'datasets':[{{'label':'L','values':[1],'type':'bar'}}]}}"
                try:
                    genai.configure(api_key=api_key)
                    mod = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA)
                    res = mod.generate_content(prompt)
                    clean_json = res.text.replace("```json","").replace("```","").strip()
                    st.session_state.generated_chart = generate_advanced_chart(json.loads(clean_json))
                    st.success("¡Listo!")
                except: st.error("Sin datos.")

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
                        genai.configure(api_key=api_key)
                        mod = genai.GenerativeModel(MODELO_USADO, system_instruction=MEMORIA_MAESTRA)
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
        if st.button("Leer YT", use_container_width=True) and (u:=st.text_input("Link YT")): st.session_state.contexto_texto=get_youtube_text(u);st.success("OK")
        if st.button("Leer Web", use_container_width=True) and (w:=st.text_input("Link Web")): st.session_state.contexto_texto=get_web_text(w);st.success("OK")

    st.markdown("---")
    if st.session_state.messages:
        c1, c2 = st.columns(2)
        c1.download_button("💾 Chat", create_chat_docx(st.session_state.messages), "acta.docx", use_container_width=True)
        c2.download_button("🧠 Backup", json.dumps(st.session_state.messages), "mem.json", use_container_width=True)
    uploaded_memory = st.file_uploader("Cargar Backup", type=['json'])
    if uploaded_memory and st.button("Restaurar", use_container_width=True): st.session_state.messages = json.load(uploaded_memory); st.rerun()
    if st.button("🗑️ Borrar Todo", use_container_width=True): st.session_state.clear(); st.rerun()

# ==========================================
# CHAT Y VISUALIZADORES
# ==========================================
st.title(f"🤖 Agente V42: {rol}")
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

# --- CONFIGURACIÓN DINÁMICA DEL MODELO ---
tools_config = []
if usar_google_search:
    tools_config = [{'google_search_retrieval': {}}]

genai.configure(api_key=api_key)

# AQUI SE CARGA LA MEMORIA MAESTRA
model = genai.GenerativeModel(
    MODELO_USADO, 
    tools=tools_config, 
    system_instruction=MEMORIA_MAESTRA, # <--- EL CEREBRO DE SU AGENTE
    generation_config={"temperature": temp_val}
)

# --- INTERFAZ DE CHAT (STREAMING EN TEXTO) ---
if modo_voz:
    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown("### 🎙️ Hablar")
        audio = mic_recorder(start_prompt="🔴 Grabar", stop_prompt="⏹️ Parar", key='recorder')
    with col2:
        if audio:
            st.audio(audio['bytes'])
            with st.spinner("Procesando audio..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tf:
                    tf.write(audio['bytes']); tpath = tf.name
                mfile = genai.upload_file(path=tpath)
                while mfile.state.name == "PROCESSING": time.sleep(0.5); mfile = genai.get_file(mfile.name)
                
                ctx = st.session_state.contexto_texto
                instruccion = prompts_roles.get(rol, "Experto")
                prompt = f"Rol: {rol}. INSTRUCCIONES: {instruccion}. Responde BREVE (audio). Contexto: {ctx[:50000]}"
                
                res = model.generate_content([prompt, mfile])
                st.chat_message("assistant").markdown(res.text)
                st.session_state.messages.append({"role": "user", "content": "Audio enviado"})
                st.session_state.messages.append({"role": "assistant", "content": res.text})
                
                tts = gTTS(text=res.text, lang='es')
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                    tts.save(fp.name); st.audio(fp.name)
                os.remove(tpath)
else:
    for m in st.session_state.messages: st.chat_message(m["role"]).markdown(m["content"])
    if p := st.chat_input("Instrucción..."):
        st.session_state.messages.append({"role": "user", "content": p})
        st.chat_message("user").markdown(p)
        with st.chat_message("assistant"):
            ctx = st.session_state.contexto_texto
            instruccion = prompts_roles.get(rol, "Experto")
            prompt = f"Rol: {rol}. PERFIL: {instruccion}. Historial: {st.session_state.messages[-5:]}. Consulta: {p}"
            if ctx: prompt += f"\nDOCS: {ctx[:500000]}"
            con = [prompt]
            if st.session_state.archivo_multimodal: 
                con.insert(0, st.session_state.archivo_multimodal); con.append("(Analiza el archivo).")
            
            try:
                # --- STREAMING ACTIVADO (EFECTO EN VIVO) ---
                response = model.generate_content(con, stream=True)
                def stream_parser():
                    for chunk in response: yield chunk.text
                full_response = st.write_stream(stream_parser)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e: st.error(f"Error: {e}")
