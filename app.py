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

# --- CONFIGURACIÓN DE PÁGINA OPTIMIZADA PARA IPAD ---
st.set_page_config(
    page_title="MedTutor Pro - Ximena",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 🎨 DISEÑO UI/UX PREMIUM (OPTIMIZADO PARA IPAD & APPLE PENCIL) ---
css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
}

/* Banner Principal Estético */
.hero-banner {
    background: linear-gradient(135deg, #0F2027 0%, #203A43 50%, #2C5364 100%);
    border-left: 8px solid #38ef7d;
    padding: 32px;
    border-radius: 24px;
    color: white;
    margin-bottom: 25px;
    box-shadow: 0 12px 28px rgba(0,0,0,0.18);
}
.hero-banner h1 {
    color: #ffffff;
    margin: 0;
    font-size: 2.5rem;
    font-weight: 800;
    letter-spacing: -0.5px;
}
.hero-banner p {
    color: #cbd5e1;
    margin: 8px 0 0 0;
    font-size: 1.1rem;
}

/* Tarjeta de Pregunta tipo UWorld / Amboss */
.pregunta-caja {
    background: var(--secondary-background-color);
    padding: 28px;
    border-radius: 22px;
    border-left: 8px solid #00d2ff;
    box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    margin-bottom: 20px;
}

/* Tarjetas de Ayuda IA (Feynman y Mnemotecnias) */
.ai-helper-box {
    background: linear-gradient(135deg, rgba(0,210,255,0.1) 0%, rgba(58,123,213,0.1) 100%);
    border: 1px solid #00d2ff;
    padding: 20px;
    border-radius: 16px;
    margin-top: 12px;
    margin-bottom: 12px;
}

/* Botones grandes y táctiles para iPad */
.stButton>button {
    border-radius: 16px;
    font-weight: 700;
    padding: 0.65rem 1.2rem;
    transition: all 0.2s ease;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 15px rgba(0,210,255,0.25);
}

/* Opciones de Radio más grandes y fáciles de tocar en iPad */
div[role="radiogroup"] > label {
    background: var(--secondary-background-color);
    padding: 16px 20px !important;
    border-radius: 14px !important;
    margin-bottom: 10px !important;
    border: 1px solid rgba(128,128,128,0.2) !important;
    transition: all 0.2s ease;
    cursor: pointer;
}
div[role="radiogroup"] > label:hover {
    border-color: #00d2ff !important;
}

/* Barra de progreso suave */
.stProgress > div > div > div > div {
    background-image: linear-gradient(90deg, #00d2ff 0%, #38ef7d 100%);
}

/* Etiquetas tipo Píldora */
.pill-badge {
    display: inline-block;
    background: rgba(56, 239, 125, 0.15);
    color: #38ef7d;
    padding: 4px 14px;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 700;
    margin-bottom: 10px;
}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

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

# --- VARIABLES DE ESTADO (SESSION STATE) ---
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

# --- FRASES MOTIVACIONALES PARA XIMENA ---
frases_ximena = [
    "¡Cada página que estudias hoy es un paciente que ayudarás mañana, Dra. Ximena! 🩺✨",
    "Respira hondo, toma agüita y confía en tu capacidad. ¡Vas increíble! 💪🧠",
    "El primer semestre es pesado, pero tú eres más fuerte. ¡Paso a paso! 🌸📚",
    "¡Orgullo futuro de la medicina! Un tema a la vez, sin presiones. 🌟👩‍⚕️"
]

# --- PANEL LATERAL (PERFIL, POMODORO Y ESTADÍSTICAS) ---
with st.sidebar:
    st.markdown(
        '<div style="text-align: center; padding-top: 10px;">'
        '<img src="https://api.dicebear.com/7.x/notionists/svg?seed=Ximena&backgroundColor=e2e8f0" width="110" style="border-radius: 50%; border: 4px solid #00d2ff;">'
        '<h2 style="margin-top: 12px; margin-bottom: 2px;">Dra. Ximena</h2>'
        '<p style="color: #94a3b8; font-weight: 600; font-size: 0.9rem;">Medicina • Panel Personal 🩺</p>'
        '</div>',
        unsafe_allow_html=True
    )
    
    st.info(random.choice(frases_ximena))
    
    # CONEXIÓN CON API KEY (CAJA FUERTE O MANUAL)
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.caption("🟢 Motor de IA: Conectado y listo")
    else:
        api_key = st.text_input("🔑 Google API Key:", type="password")
        st.caption("⚠️ Configura Secrets en Streamlit para ocultarlo.")

    st.markdown("---")
    
    # MÉTRICAS DEL DÍA
    st.subheader("📊 Tu Sesión de Hoy")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Decks Guardados", len(cargar_historial()))
    with c2:
        st.metric("Practicadas Hoy", st.session_state.total_respondidas_hoy)

    # RELOJ POMODORO RÁPIDO
    with st.expander("⏱️ Modo Concentración (Pomodoro)"):
        st.write("Estudia en bloques de 25 min sin ver el celular y descansa 5 min.")
        min_pomo = st.selectbox("Duración del bloque:", [25, 45, 15], index=0)
        if st.button("🔔 Iniciar Bloque ahora", use_container_width=True):
            st.toast(f"¡Reloj iniciado! Concéntrate durante {min_pomo} minutos, Ximena. 🩺", icon="⏱️")

    if st.session_state.quiz:
        st.markdown("---")
        st.subheader("🎯 Examen en Curso")
        html_score = (
            f'<div style="background-color: var(--secondary-background-color); padding: 15px; border-radius: 16px; text-align: center; border: 1px solid #00d2ff;">'
            f'<h1 style="color: #00d2ff; margin: 0; font-size: 2.6rem;">{st.session_state.puntaje} / {len(st.session_state.quiz)}</h1>'
            f'<p style="margin: 0; font-weight: bold;">Aciertos Actuales</p></div>'
        )
        st.markdown(html_score, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🏠 Salir al Menú Principal", use_container_width=True):
            reiniciar_todo()
            st.rerun()

# =====================================================================
# PANTALLA PRINCIPAL (CUANDO NO HAY UN QUIZ ACTIVO)
# =====================================================================
if not st.session_state.quiz:
    st.markdown(
        '<div class="hero-banner">'
        '<h1>MedTutor AI Pro 🩺</h1>'
        '<p>Estudio inteligente, simulador de casos clínicos, visión anatómica y resúmenes médicos para Ximena</p>'
        '</div>',
        unsafe_allow_html=True
    )
    
    tab_pdf, tab_imagen, tab_guardados, tab_consulta = st.tabs([
        "📄 Apuntes y Presentaciones (PDF)",
        "👁️ Laboratorio Visual (Anatomía)",
        "📁 Mi Bóveda de Decks",
        "💬 Tutor Médico 24/7"
    ])
    
    # -----------------------------------------------------------------
    # PESTAÑA 1: DOCUMENTOS PDF + RESUMEN EXPRESS + CONFIGURADOR DE QUIZ
    # -----------------------------------------------------------------
    with tab_pdf:
        if not st.session_state.texto_pdf:
            st.write("### 📖 Sube la presentación del doctor o el capítulo del libro")
            archivo_subido = st.file_uploader("Arrastra aquí tu archivo PDF", type=["pdf"], key="pdf_uploader")
            if archivo_subido is not None:
                if st.button("🔍 Analizar Documento y Extraer Temario", type="primary", use_container_width=True):
                    if not api_key:
                        st.error("⚠️ Falta configurar la API Key.")
                    else:
                        with st.spinner("🤖 Analizando diapositivas y armando tu plan de estudio..."):
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
                                st.error(f"Hubo un detalle al leer el PDF: {e}")
                            finally:
                                os.unlink(tmp_path)
        else:
            st.success("✅ ¡Documento cargado en memoria! Configura tu sesión de estudio:")
            
            with st.container(border=True):
                tema_elegido = st.selectbox("📌 1. Elige el subtema que quieres dominar ahorita:", ["🌟 Todos los temas del documento"] + st.session_state.lista_temas)
                
                col_cfg1, col_cfg2 = st.columns(2)
                with col_cfg1:
                    num_preguntas = st.select_slider("🔢 2. ¿Cuántas preguntas quieres?", options=[5, 10, 15], value=10)
                with col_cfg2:
                    estilo_quiz = st.selectbox(
                        "🩺 3. Estilo del Examen:",
                        [
                            "Mixto (Memoria + Casos Clínicos)",
                            "100% Casos Clínicos (Tipo Hospital / ENARM)",
                            "Conceptos Clave y Definiciones Directas"
                        ]
                    )
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button(f"⚡ Crear Examen ({num_preguntas} preguntas)", type="primary", use_container_width=True):
                        with st.spinner(f"Diseñando {num_preguntas} preguntas estilo '{estilo_quiz}'..."):
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
                                st.error(f"Error al generar el examen: {e}")
                
                with col_btn2:
                    if st.button("📝 Generar Hoja de Repaso Express (Cheat Sheet)", use_container_width=True):
                        with st.spinner("Sintetizando perlas clínicas y puntos clave..."):
                            try:
                                llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.2, google_api_key=api_key)
                                prompt_resumen = (
                                    f"Eres un tutor médico. Crea una 'Hoja de Repaso Express' súper clara y visual en Markdown sobre '{tema_elegido}' "
                                    f"basada en este documento. Incluye:\n"
                                    f"1. 🎯 Conceptos Clave que siempre preguntan en exámenes\n"
                                    f"2. 🧠 2 Mnemotecnias para memorizar lo más difícil\n"
                                    f"3. 🚨 Banderas Rojas / Datos Clínicos Críticos\n"
                                    f"4. 📊 Tabla comparativa (si aplica).\n\nDocumento:\n{st.session_state.texto_pdf}"
                                )
                                respuesta_res = llm.invoke(prompt_resumen)
                                st.session_state.resumen_express = respuesta_res.content
                            except Exception as e:
                                st.error(f"Error al crear resumen: {e}")

            if st.session_state.resumen_express:
                with st.expander("📋 Ver tu Hoja de Repaso Express (Cheat Sheet)", expanded=True):
                    st.markdown(st.session_state.resumen_express)
                    st.download_button(
                        "📥 Descargar Resumen en el iPad (.md)",
                        data=st.session_state.resumen_express,
                        file_name=f"Resumen_{tema_elegido.replace(' ', '_')}.md",
                        mime="text/markdown"
                    )

            if st.button("🗑️ Subir un PDF diferente"):
                reiniciar_todo()
                st.rerun()

    # -----------------------------------------------------------------
    # PESTAÑA 2: MODO VISIÓN ANATÓMICA E HISTOLOGÍA
    # -----------------------------------------------------------------
    with tab_imagen:
        st.write("### 🧠 Sube un esquema de Anatomía, Histología, Fisiología o foto de tu iPad")
        archivo_img = st.file_uploader("Sube una captura (JPG, PNG)", type=["jpg", "jpeg", "png"])
        if archivo_img is not None:
            col_im1, col_im2 = st.columns([1, 1])
            with col_im1:
                st.image(archivo_img, caption="Imagen cargada", use_container_width=True)
            with col_im2:
                st.write("#### Configura tu análisis visual:")
                num_preg_img = st.select_slider("Cantidad de preguntas visuales:", options=[5, 8, 10], value=5)
                enfoque_img = st.radio(
                    "¿Qué quieres que evalúe la IA?",
                    [
                        "Identificación anatómica y relaciones espaciales",
                        "Fisiología / Función de las estructuras mostradas",
                        "Correlación clínica (¿Qué pasa si se lesiona algo de aquí?)"
                    ]
                )
                if st.button("👁️ Generar Examen Visual", type="primary", use_container_width=True):
                    if not api_key:
                        st.error("⚠️ Falta la API Key.")
                    else:
                        with st.spinner("Escaneando estructuras médicas de tu imagen..."):
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
                                resultado_quiz = parser_quiz.parse(respuesta.content)
                                quiz_generado = [p.dict() for p in resultado_quiz.preguntas]
                                st.session_state.quiz = quiz_generado
                                st.session_state.errores_quiz = []
                                st.session_state.tema_actual = "Anatomía / Imagen Médica"
                                st.session_state.indice_actual = 0
                                st.session_state.puntaje = 0
                                guardar_en_historial("Anatomía Visual", quiz_generado)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al analizar imagen: {e}")

    # -----------------------------------------------------------------
    # PESTAÑA 3: BÓVEDA DE DECKS GUARDADOS + RESPALDO PORTÁTIL
    # -----------------------------------------------------------------
    with tab_guardados:
        st.write("### 🗃️ Tu Biblioteca de Exámenes Guardados")
        historial = cargar_historial()
        if not historial:
            st.info("💡 Todavía no tienes exámenes guardados. Cuando generes uno en PDF o Visión, se guardará aquí solito.")
        else:
            with st.container(border=True):
                deck_elegido = st.selectbox("Selecciona un examen guardado para volver a practicar:", list(historial.keys()))
                st.caption(f"Contiene {len(historial[deck_elegido])} preguntas listas.")
                col_jugar, col_borrar = st.columns(2)
                with col_jugar:
                    if st.button("▶️ Practicar este Deck", type="primary", use_container_width=True):
                        st.session_state.quiz = historial[deck_elegido]
                        st.session_state.errores_quiz = []
                        st.session_state.tema_actual = deck_elegido
                        st.session_state.indice_actual = 0
                        st.session_state.puntaje = 0
                        st.rerun()
                with col_borrar:
                    if st.button("🗑️ Eliminar de la Bóveda", use_container_width=True):
                        borrar_del_historial(deck_elegido)
                        st.toast("Deck eliminado", icon="🗑️")
                        time.sleep(0.5)
                        st.rerun()

        # SISTEMA DE RESPALDO PARA NO PERDER NADA EN LA NUBE
        with st.expander("☁️ Respaldo Portátil (Guardar o Restaurar tus Decks en tu iPad)"):
            st.caption("Descarga tu copia de seguridad por si el servidor en la nube se reinicia:")
            if historial:
                json_backup = json.dumps(historial, ensure_ascii=False, indent=4)
                st.download_button(
                    "💾 Descargar todos mis Decks (.json)",
                    data=json_backup,
                    file_name="Respaldo_Decks_Ximena.json",
                    mime="application/json",
                    use_container_width=True
                )
            archivo_respaldo = st.file_uploader("Restaurar un respaldo guardado (.json):", type=["json"])
            if archivo_respaldo is not None:
                if st.button("🔄 Restaurar Decks Ahora"):
                    datos_subidos = json.load(archivo_respaldo)
                    historial_actual = cargar_historial()
                    historial_actual.update(datos_subidos)
                    with open(ARCHIVO_BD, "w", encoding="utf-8") as f:
                        json.dump(historial_actual, f, ensure_ascii=False, indent=4)
                    st.success("¡Decks restaurados con éxito!")
                    st.rerun()

    # -----------------------------------------------------------------
    # PESTAÑA 4: CONSULTORIO DE DUDAS RÁPIDAS (FEYNMAN / MNEMOTECNIAS)
    # -----------------------------------------------------------------
    with tab_consulta:
        st.write("### 💬 Pregúntale lo que sea a tu Tutor Médico")
        st.caption("¿Un concepto de fisiología, bioquímica o anatomía no te queda claro? Escríbelo aquí:")
        duda_ximena = st.text_input("Ejemplo: 'No entiendo el potencial de acción cardíaco' o 'Hazme una mnemotecnia para las ramas de la arteria maxilar'")
        modo_explicacion = st.radio(
            "¿Cómo quieres la respuesta?",
            ["👶 Súper fácil con analogías (Método Feynman)", "🧠 Mnemotecnia creativa e inolvidable", "🩺 Explicación clínica de examen"],
            horizontal=True
        )
        if st.button("✨ Resolver mi duda", type="primary"):
            if duda_ximena and api_key:
                with st.spinner("Pensando la mejor explicación para ti..."):
                    llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.4, google_api_key=api_key)
                    resp = llm.invoke(
                        f"Eres el tutor personal de medicina de Ximena. Responde a su solicitud: '{duda_ximena}' "
                        f"usando el estilo: {modo_explicacion}. Sé claro, cálido, estructurado y usa emojis médicos."
                    )
                    st.markdown(f"<div class='ai-helper-box'>{resp.content}</div>", unsafe_allow_html=True)

# =====================================================================
# MODO EXAMEN ACTIVO (INTERFAZ INTERACTIVA CON SUPERPODERES)
# =====================================================================
else:
    total_preguntas = len(st.session_state.quiz)
    indice = st.session_state.indice_actual
    
    st.markdown(f"<span class='pill-badge'>📚 {st.session_state.tema_actual}</span>", unsafe_allow_html=True)
    st.progress(indice / total_preguntas, text=f"Pregunta {indice + 1} de {total_preguntas}")
    
    if indice < total_preguntas:
        pregunta_actual = st.session_state.quiz[indice]
        
        if not st.session_state.opciones_revueltas:
            opciones = pregunta_actual["opciones"].copy()
            random.shuffle(opciones)
            st.session_state.opciones_revueltas = opciones

        # TARJETA DE LA PREGUNTA
        pregunta_html = f"<div class='pregunta-caja'><h2 style='margin:0; font-size:1.35rem; line-height:1.5;'>🩺 {pregunta_actual['pregunta']}</h2></div>"
        st.markdown(pregunta_html, unsafe_allow_html=True)
        
        opcion_seleccionada = st.radio(
            "Selecciona la respuesta correcta:",
            st.session_state.opciones_revueltas,
            index=None,
            label_visibility="collapsed"
        )
        
        if not st.session_state.respuesta_revisada:
            if st.button("✨ Comprobar Respuesta", use_container_width=True, type="primary"):
                if opcion_seleccionada:
                    st.session_state.respuesta_revisada = True
                    st.rerun()
                else:
                    st.warning("☝️ Toca una de las opciones primero.")
        else:
            # CALIFICACIÓN DE LA PREGUNTA
            es_correcta = (opcion_seleccionada == pregunta_actual["respuesta_correcta"])
            if es_correcta:
                st.success("### ¡Excelente diagnóstico, Dra. Ximena! 🎉")
                if st.session_state.bandera_puntaje:
                    st.session_state.puntaje += 1
                    st.session_state.total_respondidas_hoy += 1
                    st.toast("¡Respuesta Correcta! +1 punto", icon="✅")
            else:
                st.error(f"### Ups, esa no era ❌ (Elegiste: {opcion_seleccionada})")
                st.info(f"💡 **Respuesta correcta:** {pregunta_actual['respuesta_correcta']}")
                if st.session_state.bandera_puntaje:
                    st.session_state.total_respondidas_hoy += 1
                    if pregunta_actual not in st.session_state.errores_quiz:
                        st.session_state.errores_quiz.append(pregunta_actual)
                    st.toast("Guardada para repaso de errores", icon="📌")
            
            st.session_state.bandera_puntaje = False

            # EXPLICACIÓN CLÍNICA BASE
            with st.expander("📖 Explicación Médica Detallada", expanded=True):
                st.write(pregunta_actual["explicacion"])
            
            # --- SUPERPODERES EN VIVO: FEYNMAN Y MNEMOTECNIA ---
            st.caption("¿Sigue confuso o difícil de memorizar? Usa tus herramientas mágicas:")
            col_help1, col_help2 = st.columns(2)
            with col_help1:
                if st.button("👶 Explícamelo Súper Fácil (Feynman)", use_container_width=True):
                    with st.spinner("Traduciendo a lenguaje súper sencillo..."):
                        llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.4, google_api_key=api_key)
                        prompt_f = (
                            f"Explica este concepto médico a Ximena como si tuviera 12 años, usando una analogía de la vida real "
                            f"súper fácil de imaginar.\nPregunta: {pregunta_actual['pregunta']}\n"
                            f"Respuesta correcta: {pregunta_actual['respuesta_correcta']}\n"
                            f"Contexto: {pregunta_actual['explicacion']}"
                        )
                        st.session_state.feynman_actual = llm.invoke(prompt_f).content
            with col_help2:
                if st.button("🧠 Créame una Mnemotecnia", use_container_width=True):
                    with st.spinner("Inventando truco de memoria..."):
                        llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.6, google_api_key=api_key)
                        prompt_m = (
                            f"Crea una mnemotecnia corta, divertida o un acrónimo ingenioso en español para que Ximena jamás olvide "
                            f"que la respuesta a '{pregunta_actual['pregunta']}' es '{pregunta_actual['respuesta_correcta']}'. "
                            f"Explicación: {pregunta_actual['explicacion']}"
                        )
                        st.session_state.mnemo_actual = llm.invoke(prompt_m).content

            if st.session_state.feynman_actual:
                st.markdown(f"<div class='ai-helper-box'><b>👶 Explicación Feynman:</b><br>{st.session_state.feynman_actual}</div>", unsafe_allow_html=True)
            if st.session_state.mnemo_actual:
                st.markdown(f"<div class='ai-helper-box'><b>🧠 Truco de Memoria:</b><br>{st.session_state.mnemo_actual}</div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Siguiente Pregunta ➡️", use_container_width=True, type="primary"):
                st.session_state.indice_actual += 1
                st.session_state.respuesta_revisada = False
                st.session_state.opciones_revueltas = []
                st.session_state.bandera_puntaje = True
                limpiar_ayudas_pregunta()
                st.rerun()
                
    else:
        # =================================================================
        # PANTALLA FINAL DE RESULTADOS Y REPASO DE ERRORES
        # =================================================================
        st.balloons()
        porcentaje = int((st.session_state.puntaje / total_preguntas) * 100)
        
        if porcentaje == 100:
            mensaje_final = "¡Perfección absoluta, futura especialista! Dominas este tema al 100%. 🏆"
        elif porcentaje >= 80:
            mensaje_final = "¡Excelente nivel clínico! Estás más que lista para el examen. 🌟"
        else:
            mensaje_final = "¡Buen entrenamiento! Repasemos las que fallaron para blindar el tema. 💪"

        html_victoria = (
            f'<div style="text-align: center; padding: 35px; background-color: var(--secondary-background-color); border-radius: 24px; border: 2px solid #00d2ff;">'
            f'<h1 style="font-size: 3.5rem; margin: 0;">🎓 {porcentaje}%</h1>'
            f'<h2 style="margin: 10px 0;">Obtuviste {st.session_state.puntaje} de {total_preguntas} aciertos</h2>'
            f'<p style="font-size: 1.15rem; color: #94a3b8;">{mensaje_final}</p>'
            f'</div>'
        )
        st.markdown(html_victoria, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # BOTÓN ESPECIAL SI TUVO ERRORES: REPASAR SOLO LAS FALLADAS
        num_errores = len(st.session_state.errores_quiz)
        if num_errores > 0:
            if st.button(f"🔥 Repasar AHORA solo las {num_errores} preguntas que fallé", type="primary", use_container_width=True):
                st.session_state.quiz = st.session_state.errores_quiz.copy()
                st.session_state.errores_quiz = []
                st.session_state.indice_actual = 0
                st.session_state.puntaje = 0
                st.session_state.respuesta_revisada = False
                st.session_state.bandera_puntaje = True
                st.session_state.tema_actual = f"Repaso de Errores: {st.session_state.tema_actual}"
                st.rerun()

        # EXPORTAR A ANKI
        csv_anki = generar_csv_anki(st.session_state.quiz)
        st.download_button(
            label="📥 Descargar este Deck para Anki (.CSV)",
            data=csv_anki,
            file_name=f"Anki_{st.session_state.tema_actual[:20].replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔁 Repetir todo este bloque", use_container_width=True):
                st.session_state.indice_actual = 0
                st.session_state.puntaje = 0
                st.session_state.errores_quiz = []
                st.session_state.respuesta_revisada = False
                st.session_state.bandera_puntaje = True
                st.rerun()
        with col2:
            if st.button("🏠 Volver al Centro de Estudio", use_container_width=True):
                reiniciar_todo()
                st.rerun()
