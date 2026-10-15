import streamlit as st
import time
import tempfile
import os
import random
import base64
import json
import csv
import io

from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from typing import List

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="MedTutor Studio — Ximena",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DISEÑO UI/UX AESTHETIC, MINIMALISTA Y EDITORIAL ---
css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,600;0,700;1,600&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* Tipografía Editorial para Títulos */
h1, h2, .serif-title {
    font-family: 'Cormorant Garamond', serif !important;
    letter-spacing: -0.3px;
}

/* Banner Principal con Imagen Aesthetic Superpuesta */
.hero-container {
    position: relative;
    background-image: linear-gradient(120deg, rgba(30, 27, 36, 0.82) 0%, rgba(74, 58, 75, 0.72) 100%), url('https://images.unsplash.com/photo-1516549655169-df83a0774514?auto=format&fit=crop&w=1600&q=80');
    background-size: cover;
    background-position: center;
    padding: 48px 40px;
    border-radius: 24px;
    color: #ffffff;
    margin-bottom: 32px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.12);
}

.hero-tag {
    display: inline-block;
    text-transform: uppercase;
    font-size: 0.72rem;
    letter-spacing: 2.5px;
    font-weight: 700;
    color: #f3d1dc;
    background: rgba(255, 255, 255, 0.12);
    backdrop-filter: blur(8px);
    padding: 6px 14px;
    border-radius: 99px;
    margin-bottom: 14px;
}

.hero-container h1 {
    font-size: 3.1rem;
    font-weight: 700;
    margin: 0;
    color: #ffffff;
    line-height: 1.1;
}

.hero-container p {
    font-size: 1.05rem;
    color: #e2e8f0;
    margin-top: 10px;
    max-width: 620px;
    font-weight: 400;
}

/* Tarjetas Visuales con Imagen de Cabecera */
.feature-card {
    background: var(--secondary-background-color);
    border-radius: 20px;
    overflow: hidden;
    border: 1px solid rgba(226, 232, 240, 0.12);
    margin-bottom: 24px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04);
}
.feature-card-img {
    height: 130px;
    width: 100%;
    object-fit: cover;
    opacity: 0.88;
}
.feature-card-body {
    padding: 22px 26px;
}
.feature-card-title {
    font-size: 1.25rem;
    font-weight: 700;
    margin: 0 0 6px 0;
}
.feature-card-sub {
    font-size: 0.9rem;
    opacity: 0.7;
    margin: 0;
}

/* Tarjeta de Pregunta Minimalista */
.pregunta-caja {
    background: var(--secondary-background-color);
    padding: 34px;
    border-radius: 22px;
    border-left: 5px solid #d48c9e;
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.06);
    margin-bottom: 24px;
}

/* Botones Estilizados */
.stButton>button {
    border-radius: 14px;
    font-weight: 600;
    letter-spacing: 0.3px;
    padding: 0.65rem 1.4rem;
    border: 1px solid rgba(212, 140, 158, 0.25);
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(212, 140, 158, 0.22);
    border-color: #d48c9e;
}

/* Botón Primario en Tono Rose-Mauve Aesthetic */
button[kind="primary"] {
    background: linear-gradient(135deg, #c97a8e 0%, #9b72aa 100%) !important;
    color: white !important;
    border: none !important;
}

/* Opciones de Examen Táctiles */
div[role="radiogroup"] > label {
    background: var(--secondary-background-color);
    padding: 18px 22px !important;
    border-radius: 14px !important;
    margin-bottom: 10px !important;
    border: 1px solid rgba(148, 163, 184, 0.18) !important;
    transition: all 0.2s ease;
}
div[role="radiogroup"] > label:hover {
    border-color: #d48c9e !important;
    background: rgba(212, 140, 158, 0.05);
}

/* Barra de progreso */
.stProgress > div > div > div > div {
    background-image: linear-gradient(90deg, #d48c9e 0%, #9b72aa 100%);
}

/* Píldora de Categoría */
.pill-badge {
    display: inline-block;
    background: rgba(212, 140, 158, 0.15);
    color: #d48c9e;
    padding: 5px 16px;
    border-radius: 999px;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 700;
    margin-bottom: 12px;
}

/* Perfil Lateral con Foto Real */
.profile-card {
    text-align: center;
    padding: 24px 16px;
    background: linear-gradient(180deg, rgba(212, 140, 158, 0.14) 0%, rgba(255, 255, 255, 0.01) 100%);
    border-radius: 22px;
    border: 1px solid rgba(212, 140, 158, 0.25);
    margin-bottom: 18px;
}
.profile-avatar {
    width: 130px;
    height: 130px;
    border-radius: 50%;
    object-fit: cover;
    object-position: center 55%;
    border: 3px solid #d48c9e;
    padding: 3px;
    background: white;
    box-shadow: 0 10px 25px rgba(212, 140, 158, 0.3);
}
.quote-box {
    font-family: 'Cormorant Garamond', serif;
    font-style: italic;
    font-size: 1.08rem;
    text-align: center;
    padding: 14px 18px;
    border-radius: 14px;
    background: var(--secondary-background-color);
    border-left: 3px solid #d48c9e;
    margin-bottom: 18px;
    opacity: 0.9;
}
.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    background-color: #34d399;
    border-radius: 50%;
    margin-right: 6px;
}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# --- FUNCIÓN PARA CARGAR LA FOTO DE XIMENA ---
def obtener_foto_perfil():
    posibles_nombres = [
        "ximena.jpg",
        "ximena.jpeg",
        "ximena.png",
        "WhatsApp Image 2026-10-14 at 22.42.15.jpeg"
    ]
    for nombre in posibles_nombres:
        if os.path.exists(nombre):
            with open(nombre, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
                return f"data:image/jpeg;base64,{encoded}"
    # Respaldo femenino ilustrado si aún no se sube el archivo
    return "https://api.dicebear.com/7.x/lorelei/svg?seed=Aria&backgroundColor=f8e8ee&hair=variant09&eyes=variant04&mouth=happy01"

# --- FUNCIÓN PARA LIMPIAR RESPUESTAS DE LA IA (EVITA TEXTOS RAROS EN ANALOGÍAS) ---
def extraer_texto_limpio(respuesta_ia):
    contenido = respuesta_ia.content if hasattr(respuesta_ia, "content") else respuesta_ia
    if isinstance(contenido, list):
        partes = []
        for item in contenido:
            if isinstance(item, dict) and "text" in item:
                partes.append(item["text"])
            elif isinstance(item, str):
                partes.append(item)
        return "\n".join(partes).strip()
    return str(contenido).strip()

# --- SISTEMA DE BASE DE DATOS LOCAL ---
ARCHIVO_BD = "base_datos_ximena.json"

def cargar_historial():
    if os.path.exists(ARCHIVO_BD):
        try:
            with open(ARCHIVO_BD, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def guardar_en_historial(tema, quiz_data):
    historial = cargar_historial()
    fecha = time.strftime('%d/%m %H:%M')
    nombre_unico = f"{tema} ({fecha})"
    historial[nombre_unico] = quiz_data
    with open(ARCHIVO_BD, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=4)

def borrar_del_historial(nombre_unico):
    historial = cargar_historial()
    if nombre_unico in historial:
        del historial[nombre_unico]
        with open(ARCHIVO_BD, "w", encoding="utf-8") as f:
            json.dump(historial, f, ensure_ascii=False, indent=4)

def generar_csv_anki(quiz_data):
    output = io.StringIO()
    writer = csv.writer(output)
    for q in quiz_data:
        frente = q['pregunta']
        dorso = f"<b>{q['respuesta_correcta']}</b><br><br><i>Explicación:</i><br>{q['explicacion']}"
        writer.writerow([frente, dorso])
    return output.getvalue()

# --- MODELOS DE DATOS PYDANTIC ---
class Temario(BaseModel):
    temas: List[str] = Field(description="Lista de los capítulos o subtemas principales encontrados en el documento")

parser_temario = PydanticOutputParser(pydantic_object=Temario)

class PreguntaQuiz(BaseModel):
    pregunta: str = Field(description="Pregunta médica clara o caso clínico")
    opciones: List[str] = Field(description="Exactamente 4 opciones de respuesta plausibles")
    respuesta_correcta: str = Field(description="La respuesta correcta exacta (debe ser idéntica a una de las 4 opciones)")
    explicacion: str = Field(description="Explicación médica clara de por qué es correcta y por qué se descartan las otras")

class QuizMedico(BaseModel):
    preguntas: List[PreguntaQuiz] = Field(description="Lista de preguntas generadas")

parser_quiz = PydanticOutputParser(pydantic_object=QuizMedico)

# --- VARIABLES DE ESTADO ---
defaults = {
    'texto_pdf': "",
    'lista_temas': [],
    'quiz': [],
    'errores_quiz': [],
    'indice_actual': 0,
    'puntaje': 0,
    'total_respondidas_hoy': 0,
    'respuesta_revisada': False,
    'opciones_revueltas': [],
    'bandera_puntaje': True,
    'tema_actual': "",
    'feynman_actual': "",
    'mnemo_actual': "",
    'resumen_express': ""
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def reiniciar_todo():
    st.session_state.texto_pdf = ""
    st.session_state.lista_temas = []
    st.session_state.quiz = []
    st.session_state.errores_quiz = []
    st.session_state.indice_actual = 0
    st.session_state.puntaje = 0
    st.session_state.respuesta_revisada = False
    st.session_state.opciones_revueltas = []
    st.session_state.feynman_actual = ""
    st.session_state.mnemo_actual = ""
    st.session_state.resumen_express = ""

def limpiar_ayudas_pregunta():
    st.session_state.feynman_actual = ""
    st.session_state.mnemo_actual = ""

# --- FRASES EDITORIALES PARA XIMENA ---
frases_ximena = [
    "“Cada página que estudias hoy es una vida que sabrás cuidar mañana.”",
    "“La excelencia médica se construye un capítulo a la vez. Confía en tu proceso.”",
    "“La constancia vence al cansancio. Respira hondo y continúa, Dra. Ximena.”",
    "“Estudiar medicina es un arte; hoy estás más cerca de tu meta que ayer.”"
]

# --- PANEL LATERAL (CON LA FOTO DE XIMENA) ---
with st.sidebar:
    avatar_src = obtener_foto_perfil()
    
    st.markdown(
        f'<div class="profile-card">'
        f'<img src="{avatar_src}" class="profile-avatar">'
        f'<h2 style="margin-top: 14px; margin-bottom: 2px; font-size: 1.65rem;">Ximena</h2>'
        f'<p style="color: #d48c9e; font-weight: 600; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 1.5px; margin: 0;">Medical Student • Studio</p>'
        f'</div>',
        unsafe_allow_html=True
    )
    
    st.markdown(f'<div class="quote-box">{random.choice(frases_ximena)}</div>', unsafe_allow_html=True)
    
    # CONEXIÓN CON API KEY
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.markdown('<p style="font-size: 0.8rem; opacity: 0.75; text-align: center;"><span class="status-dot"></span>Motor de Inteligencia Artificial Activo</p>', unsafe_allow_html=True)
    else:
        api_key = st.text_input("Clave de Acceso (API Key):", type="password")
        st.caption("Configura Secrets en la nube para acceso directo.")

    st.markdown("---")
    
    # MÉTRICAS DEL DÍA
    st.markdown("<p style='font-size: 0.78rem; text-transform: uppercase; letter-spacing: 1.5px; opacity: 0.6; font-weight: 700;'>Registro de Estudio</p>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Colecciones", len(cargar_historial()))
    with c2:
        st.metric("Reactivos Hoy", st.session_state.total_respondidas_hoy)

    # TEMPORIZADOR POMODORO
    with st.expander("Temporizador Pomodoro"):
        st.caption("Sesiones de enfoque profundo sin distracciones.")
        min_pomo = st.selectbox("Minutos por bloque:", [25, 45, 15], index=0)
        if st.button("Iniciar Sesión de Enfoque", use_container_width=True):
            st.toast(f"Sesión iniciada: {min_pomo} minutos de enfoque continuo.")

    if st.session_state.quiz:
        st.markdown("---")
        st.markdown("<p style='font-size: 0.78rem; text-transform: uppercase; letter-spacing: 1.5px; opacity: 0.6; font-weight: 700;'>Progreso Actual</p>", unsafe_allow_html=True)
        html_score = (
            f'<div style="background-color: var(--secondary-background-color); padding: 18px; border-radius: 16px; text-align: center; border: 1px solid rgba(212, 140, 158, 0.35);">'
            f'<h1 style="color: #d48c9e; margin: 0; font-size: 2.5rem;">{st.session_state.puntaje} / {len(st.session_state.quiz)}</h1>'
            f'<p style="margin: 4px 0 0 0; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 1px; opacity: 0.7;">Respuestas Correctas</p></div>'
        )
        st.markdown(html_score, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Finalizar y Volver al Inicio", use_container_width=True):
            reiniciar_todo()
            st.rerun()

# =====================================================================
# PANTALLA PRINCIPAL (CUANDO NO HAY UN QUIZ ACTIVO)
# =====================================================================
if not st.session_state.quiz:
    st.markdown(
        '<div class="hero-container">'
        '<span class="hero-tag">Medical Study Atelier</span>'
        '<h1>MedTutor Studio</h1>'
        '<p>Espacio privado de entrenamiento clínico, análisis visual anatómico y síntesis médica diseñado para Ximena.</p>'
        '</div>',
        unsafe_allow_html=True
    )
    
    tab_pdf, tab_imagen, tab_guardados, tab_consulta = st.tabs([
        "Presentaciones y Lecturas",
        "Atlas y Laboratorio Visual",
        "Biblioteca Guardada",
        "Consultorio Académico"
    ])
    
    # -----------------------------------------------------------------
    # PESTAÑA 1: DOCUMENTOS PDF + RESUMEN EXPRESS + CONFIGURADOR DE QUIZ
    # -----------------------------------------------------------------
    with tab_pdf:
        st.markdown(
            '<div class="feature-card">'
            '<img src="https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?auto=format&fit=crop&w=1200&q=80" class="feature-card-img">'
            '<div class="feature-card-body">'
            '<p class="feature-card-title">Estudio por Capítulos y Diapositivas</p>'
            '<p class="feature-card-sub">Carga tus presentaciones o capítulos en PDF para desglosar el temario, crear exámenes clínicos o generar hojas de repaso.</p>'
            '</div></div>',
            unsafe_allow_html=True
        )

        if not st.session_state.texto_pdf:
            archivo_subido = st.file_uploader("Selecciona o arrastra tu documento PDF", type=["pdf"], key="pdf_uploader")
            if archivo_subido is not None:
                if st.button("Analizar Documento y Extraer Índice", type="primary", use_container_width=True):
                    if not api_key:
                        st.error("Es necesario configurar la clave de acceso en el panel lateral.")
                    else:
                        with st.spinner("Analizando el contenido académico del documento..."):
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                tmp.write(archivo_subido.read())
                                tmp_path = tmp.name
                            try:
                                loader = PyPDFLoader(tmp_path)
                                paginas = loader.load()
                                st.session_state.texto_pdf = "\n".join([pagina.page_content for pagina in paginas])
                                llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.1, google_api_key=api_key)
                                prompt_temas = PromptTemplate(
                                    template="Lee este documento médico y extrae una lista de los subtemas o capítulos principales.\n\nTexto:\n{texto}\n\n{format_instructions}",
                                    input_variables=["texto"],
                                    partial_variables={"format_instructions": parser_temario.get_format_instructions()}
                                )
                                cadena_temas = prompt_temas | llm | parser_temario
                                st.session_state.lista_temas = cadena_temas.invoke({"texto": st.session_state.texto_pdf}).temas
                                st.rerun()
                            except Exception as e:
                                st.error(f"No se pudo procesar el archivo: {e}")
                            finally:
                                os.unlink(tmp_path)
        else:
            st.success("Documento procesado. Configura los parámetros de tu sesión:")
            
            with st.container(border=True):
                tema_elegido = st.selectbox("1. Módulo o capítulo a estudiar:", ["Documento Completo (Todos los temas)"] + st.session_state.lista_temas)
                
                col_cfg1, col_cfg2 = st.columns(2)
                with col_cfg1:
                    num_preguntas = st.select_slider("2. Extensión de la evaluación:", options=[5, 10, 15], value=10)
                with col_cfg2:
                    estilo_quiz = st.selectbox(
                        "3. Enfoque pedagógico:",
                        [
                            "Balanceado (Conceptos + Viñetas Clínicas)",
                            "Casos Clínicos (Formato Hospitalario / ENARM)",
                            "Fundamentos Teóricos y Definiciones"
                        ]
                    )
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button(f"Generar Evaluación ({num_preguntas} Reactivos)", type="primary", use_container_width=True):
                        with st.spinner(f"Elaborando {num_preguntas} reactivos médicos..."):
                            try:
                                llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.3, google_api_key=api_key)
                                prompt_quiz = PromptTemplate(
                                    template=(
                                        "Eres un profesor experto de la facultad de medicina. "
                                        "Basado ESTRICTAMENTE en el documento, crea exactamente {num_preguntas} preguntas de opción múltiple "
                                        "enfocadas en: {tema_especifico}.\n"
                                        "El estilo de las preguntas debe ser: {estilo}.\n"
                                        "Asegúrate de que las 4 opciones sean plausibles y la explicación sea muy didáctica.\n\n"
                                        "{format_instructions}\n\nDocumento:\n{texto}"
                                    ),
                                    input_variables=["num_preguntas", "tema_especifico", "estilo", "texto"],
                                    partial_variables={"format_instructions": parser_quiz.get_format_instructions()}
                                )
                                cadena_quiz = prompt_quiz | llm | parser_quiz
                                resultado_quiz = cadena_quiz.invoke({
                                    "num_preguntas": num_preguntas,
                                    "tema_especifico": tema_elegido,
                                    "estilo": estilo_quiz,
                                    "texto": st.session_state.texto_pdf
                                })
                                quiz_generado = [p.dict() for p in resultado_quiz.preguntas]
                                st.session_state.quiz = quiz_generado
                                st.session_state.errores_quiz = []
                                st.session_state.tema_actual = tema_elegido
                                st.session_state.indice_actual = 0
                                st.session_state.puntaje = 0
                                guardar_en_historial(tema_elegido, quiz_generado)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al generar la evaluación: {e}")
                
                with col_btn2:
                    if st.button("Crear Hoja de Síntesis (Cheat Sheet)", use_container_width=True):
                        with st.spinner("Sintetizando conceptos clave y perlas clínicas..."):
                            try:
                                llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.2, google_api_key=api_key)
                                prompt_resumen = (
                                    f"Eres un tutor médico. Crea una 'Hoja de Repaso Académica' limpia, elegante y estructurada en Markdown sobre '{tema_elegido}' "
                                    f"basada en este documento. No uses emojis. Incluye:\n"
                                    f"1. Conceptos Esenciales de Examen\n"
                                    f"2. Dos Mnemotecnias para recordar datos complejos\n"
                                    f"3. Datos Clínicos Críticos (Red Flags)\n"
                                    f"4. Tabla comparativa de síntesis.\n\nDocumento:\n{st.session_state.texto_pdf}"
                                )
                                respuesta_res = llm.invoke(prompt_resumen)
                                st.session_state.resumen_express = extraer_texto_limpio(respuesta_res)
                            except Exception as e:
                                st.error(f"Error al crear síntesis: {e}")

            if st.session_state.resumen_express:
                with st.expander("Lectura de Síntesis (Cheat Sheet)", expanded=True):
                    st.markdown(st.session_state.resumen_express)
                    st.download_button(
                        "Descargar Hoja de Síntesis (.md)",
                        data=st.session_state.resumen_express,
                        file_name=f"Sintesis_{tema_elegido.replace(' ', '_')}.md",
                        mime="text/markdown"
                    )

            if st.button("Cambiar Documento PDF"):
                reiniciar_todo()
                st.rerun()

    # -----------------------------------------------------------------
    # PESTAÑA 2: MODO VISIÓN ANATÓMICA E HISTOLOGÍA
    # -----------------------------------------------------------------
    with tab_imagen:
        st.markdown(
            '<div class="feature-card">'
            '<img src="https://images.unsplash.com/photo-1579154204601-01588f351e67?auto=format&fit=crop&w=1200&q=80" class="feature-card-img">'
            '<div class="feature-card-body">'
            '<p class="feature-card-title">Reconocimiento Visual de Anatomía e Histología</p>'
            '<p class="feature-card-sub">Sube esquemas del atlas, cortes histológicos o capturas de tus apuntes en iPad para evaluar identificación estructural y correlación clínica.</p>'
            '</div></div>',
            unsafe_allow_html=True
        )

        archivo_img = st.file_uploader("Selecciona una imagen o esquema (JPG, PNG)", type=["jpg", "jpeg", "png"])
        if archivo_img is not None:
            col_im1, col_im2 = st.columns([1, 1])
            with col_im1:
                st.image(archivo_img, caption="Lámina de estudio", use_container_width=True)
            with col_im2:
                st.markdown("#### Parámetros de Evaluación Visual")
                num_preg_img = st.select_slider("Número de reactivos:", options=[5, 8, 10], value=5)
                enfoque_img = st.radio(
                    "Enfoque del análisis:",
                    [
                        "Identificación anatómica y relaciones espaciales",
                        "Fisiología y función de las estructuras visibles",
                        "Correlación clínica y patología asociada"
                    ]
                )
                if st.button("Generar Evaluación Visual", type="primary", use_container_width=True):
                    if not api_key:
                        st.error("Configura primero la clave de acceso.")
                    else:
                        with st.spinner("Analizando estructuras médicas en la imagen..."):
                            encoded_img = base64.b64encode(archivo_img.read()).decode('utf-8')
                            llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.3, google_api_key=api_key)
                            mensaje = HumanMessage(content=[
                                {
                                    "type": "text",
                                    "text": (
                                        f"Eres un catedrático de anatomía y medicina. Analiza detenidamente esta imagen. "
                                        f"Crea exactamente {num_preg_img} preguntas de opción múltiple con enfoque en: {enfoque_img}.\n"
                                        f"{parser_quiz.get_format_instructions()}"
                                    )
                                },
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_img}"}}
                            ])
                            try:
                                respuesta = llm.invoke([mensaje])
                                texto_limpio = extraer_texto_limpio(respuesta)
                                resultado_quiz = parser_quiz.parse(texto_limpio)
                                quiz_generado = [p.dict() for p in resultado_quiz.preguntas]
                                st.session_state.quiz = quiz_generado
                                st.session_state.errores_quiz = []
                                st.session_state.tema_actual = "Evaluación Visual Anatómica"
                                st.session_state.indice_actual = 0
                                st.session_state.puntaje = 0
                                guardar_en_historial("Evaluación Visual", quiz_generado)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al analizar la imagen: {e}")

    # -----------------------------------------------------------------
    # PESTAÑA 3: BÓVEDA DE DECKS GUARDADOS + RESPALDO PORTÁTIL
    # -----------------------------------------------------------------
    with tab_guardados:
        st.markdown(
            '<div class="feature-card">'
            '<img src="https://images.unsplash.com/photo-1507842229356-51c61504d3ab?auto=format&fit=crop&w=1200&q=80" class="feature-card-img">'
            '<div class="feature-card-body">'
            '<p class="feature-card-title">Archivo Personal de Evaluaciones</p>'
            '<p class="feature-card-sub">Repasa colecciones anteriores sin necesidad de volver a procesar los documentos originales.</p>'
            '</div></div>',
            unsafe_allow_html=True
        )

        historial = cargar_historial()
        if not historial:
            st.info("Tu biblioteca está vacía por ahora. Las evaluaciones que generes se archivarán automáticamente aquí.")
        else:
            with st.container(border=True):
                deck_elegido = st.selectbox("Selecciona una colección archivada:", list(historial.keys()))
                st.caption(f"Contiene {len(historial[deck_elegido])} reactivos guardados.")
                col_jugar, col_borrar = st.columns(2)
                with col_jugar:
                    if st.button("Iniciar Práctica", type="primary", use_container_width=True):
                        st.session_state.quiz = historial[deck_elegido]
                        st.session_state.errores_quiz = []
                        st.session_state.tema_actual = deck_elegido
                        st.session_state.indice_actual = 0
                        st.session_state.puntaje = 0
                        st.rerun()
                with col_borrar:
                    if st.button("Eliminar Colección", use_container_width=True):
                        borrar_del_historial(deck_elegido)
                        st.toast("Colección eliminada del archivo.")
                        time.sleep(0.5)
                        st.rerun()

        with st.expander("Respaldo Portátil de Biblioteca (Exportar / Importar)"):
            st.caption("Guarda una copia de seguridad de tus colecciones en tu iPad o restaura un archivo previo:")
            if historial:
                json_backup = json.dumps(historial, ensure_ascii=False, indent=4)
                st.download_button(
                    "Descargar Archivo de Respaldo (.json)",
                    data=json_backup,
                    file_name="Colecciones_Ximena.json",
                    mime="application/json",
                    use_container_width=True
                )
            archivo_respaldo = st.file_uploader("Cargar archivo de respaldo (.json):", type=["json"])
            if archivo_respaldo is not None:
                if st.button("Restaurar Colecciones"):
                    datos_subidos = json.load(archivo_respaldo)
                    historial_actual = cargar_historial()
                    historial_actual.update(datos_subidos)
                    with open(ARCHIVO_BD, "w", encoding="utf-8") as f:
                        json.dump(historial_actual, f, ensure_ascii=False, indent=4)
                    st.success("Colecciones restauradas correctamente.")
                    st.rerun()

    # -----------------------------------------------------------------
    # PESTAÑA 4: CONSULTORIO DE DUDAS RÁPIDAS
    # -----------------------------------------------------------------
    with tab_consulta:
        st.markdown(
            '<div class="feature-card">'
            '<img src="https://images.unsplash.com/photo-1532938911079-1b06ac7ceec7?auto=format&fit=crop&w=1200&q=80" class="feature-card-img">'
            '<div class="feature-card-body">'
            '<p class="feature-card-title">Tutoría Académica Instantánea</p>'
            '<p class="feature-card-sub">Despeja dudas puntuales de fisiología, anatomía, histología o farmacología con explicaciones adaptadas a tu estilo.</p>'
            '</div></div>',
            unsafe_allow_html=True
        )

        duda_ximena = st.text_input("Escribe el concepto o tema que deseas comprender:")
        modo_explicacion = st.radio(
            "Modalidad de explicación:",
            [
                "Explicación Sencilla con Analogías (Método Feynman)",
                "Regla Mnemotécnica para Memorización",
                "Resumen Clínico Riguroso"
            ],
            horizontal=True
        )
        if st.button("Consultar al Tutor", type="primary"):
            if duda_ximena and api_key:
                with st.spinner("Elaborando explicación..."):
                    llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.4, google_api_key=api_key)
                    resp = llm.invoke(
                        f"Eres el tutor académico de medicina de Ximena. Responde a su consulta: '{duda_ximena}' "
                        f"utilizando el enfoque: {modo_explicacion}. Mantén un tono elegante, claro, didáctico y libre de emojis."
                    )
                    with st.container(border=True):
                        st.markdown(extraer_texto_limpio(resp))

# =====================================================================
# MODO EXAMEN ACTIVO
# =====================================================================
else:
    total_preguntas = len(st.session_state.quiz)
    indice = st.session_state.indice_actual
    
    st.markdown(f"<span class='pill-badge'>{st.session_state.tema_actual}</span>", unsafe_allow_html=True)
    st.progress(indice / total_preguntas, text=f"Reactivo {indice + 1} de {total_preguntas}")
    
    if indice < total_preguntas:
        pregunta_actual = st.session_state.quiz[indice]
        
        if not st.session_state.opciones_revueltas:
            opciones = pregunta_actual["opciones"].copy()
            random.shuffle(opciones)
            st.session_state.opciones_revueltas = opciones

        # TARJETA DE LA PREGUNTA
        pregunta_html = (
            f"<div class='pregunta-caja'>"
            f"<p style='font-size: 0.75rem; text-transform: uppercase; letter-spacing: 2px; color: #d48c9e; margin-bottom: 10px; font-weight: 700;'>Caso / Reactivo {indice + 1}</p>"
            f"<h2 style='margin:0; font-size:1.45rem; line-height:1.5; font-weight: 600;'>{pregunta_actual['pregunta']}</h2>"
            f"</div>"
        )
        st.markdown(pregunta_html, unsafe_allow_html=True)
        
        opcion_seleccionada = st.radio(
            "Selecciona una respuesta:",
            st.session_state.opciones_revueltas,
            index=None,
            label_visibility="collapsed"
        )
        
        if not st.session_state.respuesta_revisada:
            if st.button("Verificar Respuesta", use_container_width=True, type="primary"):
                if opcion_seleccionada:
                    st.session_state.respuesta_revisada = True
                    st.rerun()
                else:
                    st.warning("Selecciona una de las opciones antes de verificar.")
        else:
            es_correcta = (opcion_seleccionada == pregunta_actual["respuesta_correcta"])
            if es_correcta:
                st.success(f"**Respuesta Correcta.** — {pregunta_actual['respuesta_correcta']}")
                if st.session_state.bandera_puntaje:
                    st.session_state.puntaje += 1
                    st.session_state.total_respondidas_hoy += 1
            else:
                st.error(f"**Respuesta Incorrecta.** Seleccionaste: {opcion_seleccionada}")
                st.info(f"**Opción Correcta:** {pregunta_actual['respuesta_correcta']}")
                if st.session_state.bandera_puntaje:
                    st.session_state.total_respondidas_hoy += 1
                    if pregunta_actual not in st.session_state.errores_quiz:
                        st.session_state.errores_quiz.append(pregunta_actual)
            
            st.session_state.bandera_puntaje = False

            with st.expander("Fundamento Médico y Justificación", expanded=True):
                st.write(pregunta_actual["explicacion"])
            
            # HERRAMIENTAS DE APOYO EN VIVO (LIMPIAS Y SIN ERRORES DE RENDERIZADO)
            st.caption("Herramientas de profundización:")
            col_help1, col_help2 = st.columns(2)
            with col_help1:
                if st.button("Explicar con Analogía Sencilla (Feynman)", use_container_width=True):
                    with st.spinner("Generando analogía didáctica..."):
                        llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.4, google_api_key=api_key)
                        prompt_f = (
                            f"Explica este concepto médico a Ximena de manera sumamente clara usando una analogía cotidiana. "
                            f"Escribe en párrafos limpios, sin emojis y sin código HTML.\n"
                            f"Pregunta: {pregunta_actual['pregunta']}\n"
                            f"Respuesta correcta: {pregunta_actual['respuesta_correcta']}\n"
                            f"Contexto: {pregunta_actual['explicacion']}"
                        )
                        resp_f = llm.invoke(prompt_f)
                        st.session_state.feynman_actual = extraer_texto_limpio(resp_f)
            with col_help2:
                if st.button("Generar Mnemotecnia de Memoria", use_container_width=True):
                    with st.spinner("Creando recurso mnemotécnico..."):
                        llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.6, google_api_key=api_key)
                        prompt_m = (
                            f"Crea una mnemotecnia corta, elegante o un acrónimo ingenioso en español (sin emojis y sin HTML) para que Ximena recuerde siempre "
                            f"que la respuesta a '{pregunta_actual['pregunta']}' es '{pregunta_actual['respuesta_correcta']}'. "
                            f"Explicación: {pregunta_actual['explicacion']}"
                        )
                        resp_m = llm.invoke(prompt_m)
                        st.session_state.mnemo_actual = extraer_texto_limpio(resp_m)

            if st.session_state.feynman_actual:
                with st.container(border=True):
                    st.markdown("**Analogía Didáctica (Método Feynman)**")
                    st.markdown(st.session_state.feynman_actual)
            if st.session_state.mnemo_actual:
                with st.container(border=True):
                    st.markdown("**Recurso Mnemotécnico**")
                    st.markdown(st.session_state.mnemo_actual)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Siguiente Reactivo", use_container_width=True, type="primary"):
                st.session_state.indice_actual += 1
                st.session_state.respuesta_revisada = False
                st.session_state.opciones_revueltas = []
                st.session_state.bandera_puntaje = True
                limpiar_ayudas_pregunta()
                st.rerun()
                
    else:
        # =================================================================
        # PANTALLA FINAL DE RESULTADOS
        # =================================================================
        porcentaje = int((st.session_state.puntaje / total_preguntas) * 100)
        
        if porcentaje == 100:
            mensaje_final = "Dominio sobresaliente del módulo. Precisión del 100%."
        elif porcentaje >= 80:
            mensaje_final = "Excelente desempeño clínico. El tema está bien consolidado."
        else:
            mensaje_final = "Sesión completada. Se recomienda repasar los reactivos marcados para reforzar."

        html_victoria = (
            f'<div style="text-align: center; padding: 45px 30px; background-color: var(--secondary-background-color); border-radius: 24px; border: 1px solid rgba(212, 140, 158, 0.45); margin-bottom: 24px;">'
            f'<span class="pill-badge">Sesión Finalizada</span>'
            f'<h1 style="font-size: 4rem; margin: 6px 0; color: #d48c9e;">{porcentaje}%</h1>'
            f'<h3 style="margin: 8px 0; font-weight: 600;">Puntaje obtenido: {st.session_state.puntaje} de {total_preguntas} aciertos</h3>'
            f'<p style="font-size: 1.05rem; opacity: 0.75; max-width: 500px; margin: 10px auto 0 auto;">{mensaje_final}</p>'
            f'</div>'
        )
        st.markdown(html_victoria, unsafe_allow_html=True)
        
        num_errores = len(st.session_state.errores_quiz)
        if num_errores > 0:
            if st.button(f"Repasar únicamente los {num_errores} reactivos incorrectos", type="primary", use_container_width=True):
                st.session_state.quiz = st.session_state.errores_quiz.copy()
                st.session_state.errores_quiz = []
                st.session_state.indice_actual = 0
                st.session_state.puntaje = 0
                st.session_state.respuesta_revisada = False
                st.session_state.bandera_puntaje = True
                st.session_state.tema_actual = f"Repaso Selectivo: {st.session_state.tema_actual}"
                st.rerun()

        csv_anki = generar_csv_anki(st.session_state.quiz)
        st.download_button(
            label="Exportar Colección para Anki (.CSV)",
            data=csv_anki,
            file_name=f"Anki_{st.session_state.tema_actual[:20].replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Repetir Evaluación Completa", use_container_width=True):
                st.session_state.indice_actual = 0
                st.session_state.puntaje = 0
                st.session_state.errores_quiz = []
                st.session_state.respuesta_revisada = False
                st.session_state.bandera_puntaje = True
                st.rerun()
        with col2:
            if st.button("Volver al Inicio", use_container_width=True):
                reiniciar_todo()
                st.rerun()
