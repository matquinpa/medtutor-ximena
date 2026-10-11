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

st.set_page_config(page_title="MedTutor - Ximena", page_icon="🩺", layout="centered")

# --- 🎨 MAGIA CSS ---
css = """
<style>
.pregunta-caja { background: var(--secondary-background-color); padding: 30px; border-radius: 20px; border-left: 8px solid #00C9FF; box-shadow: 0 10px 20px rgba(0,0,0,0.05); margin-bottom: 25px; transition: transform 0.2s ease-in-out; }
.pregunta-caja:hover { transform: translateY(-2px); }
.stProgress > div > div > div > div { background-image: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%); }
.stButton>button { border-radius: 25px; font-weight: 600; }
.hero-banner { background: linear-gradient(135deg, #00C9FF 0%, #92FE9D 100%); padding: 30px; border-radius: 20px; text-align: center; color: white; margin-bottom: 30px; }
.hero-banner h1 { color: white; margin: 0; font-size: 2.8rem; font-weight: 800; }
.hero-banner p { color: white; margin: 5px 0 0 0; font-size: 1.2rem; }
</style>
"""
st.markdown(css, unsafe_allow_html=True)

ARCHIVO_BD = "base_datos_ximena.json"

def cargar_historial():
    if os.path.exists(ARCHIVO_BD):
        with open(ARCHIVO_BD, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_en_historial(tema, quiz_data):
    historial = cargar_historial()
    fecha = time.strftime('%d/%m/%Y %H:%M')
    nombre_unico = f"{tema} - {fecha}"
    historial[nombre_unico] = quiz_data
    with open(ARCHIVO_BD, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=4)

def borrar_del_historial(nombre_unico):
    """NUEVA FUNCIÓN: Borra un deck específico del disco duro"""
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

class Temario(BaseModel):
    temas: List[str] = Field(description="Lista de temas principales")

parser_temario = PydanticOutputParser(pydantic_object=Temario)

class PreguntaQuiz(BaseModel):
    pregunta: str = Field(description="Pregunta médica clara")
    opciones: List[str] = Field(description="Exactamente 4 opciones")
    respuesta_correcta: str = Field(description="La respuesta exacta")
    explicacion: str = Field(description="Explicación clínica detallada")

class QuizMedico(BaseModel):
    preguntas: List[PreguntaQuiz] = Field(description="Lista de preguntas")

parser_quiz = PydanticOutputParser(pydantic_object=QuizMedico)

if 'texto_pdf' not in st.session_state: st.session_state.texto_pdf = ""
if 'lista_temas' not in st.session_state: st.session_state.lista_temas = []
if 'quiz' not in st.session_state: st.session_state.quiz = []
if 'indice_actual' not in st.session_state: st.session_state.indice_actual = 0
if 'puntaje' not in st.session_state: st.session_state.puntaje = 0
if 'respuesta_revisada' not in st.session_state: st.session_state.respuesta_revisada = False
if 'opciones_revueltas' not in st.session_state: st.session_state.opciones_revueltas = []
if 'respuesta_revisada_nueva_bandera' not in st.session_state: st.session_state.respuesta_revisada_nueva_bandera = True
if 'tema_actual' not in st.session_state: st.session_state.tema_actual = ""

def reiniciar_todo():
    st.session_state.texto_pdf = ""
    st.session_state.lista_temas = []
    st.session_state.quiz = []
    st.session_state.indice_actual = 0
    st.session_state.puntaje = 0
    st.session_state.respuesta_revisada = False
    st.session_state.opciones_revueltas = []

with st.sidebar:
    st.markdown('<div style="text-align: center; padding-top: 20px;"><img src="https://api.dicebear.com/7.x/notionists/svg?seed=Ximena&backgroundColor=e2e8f0" width="120" style="border-radius: 50%; border: 4px solid #00C9FF;"><h2 style="margin-top: 15px; margin-bottom: 5px;">Hola, Ximena</h2><p style="color: #64748b; font-weight: 500; font-size: 0.9rem;">Estudiante de Medicina 🩺</p></div>', unsafe_allow_html=True)
    st.markdown("---")
    
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ Sistema IA Conectado")
    else:
        api_key = st.text_input("🔑 Google API Key:", type="password")
        st.warning("⚠️ Configura secrets.toml para ocultar esto.")

    if st.session_state.quiz:
        st.markdown("---")
        st.subheader("🎯 Tu Desempeño Hoy")
        html_score = f'<div style="background-color: var(--secondary-background-color); padding: 15px; border-radius: 15px; text-align: center; border: 1px solid #e2e8f0;"><h1 style="color: #00C9FF; margin: 0; font-size: 3rem;">{st.session_state.puntaje}</h1><p style="margin: 0; font-weight: bold;">Respuestas Correctas</p></div>'
        st.markdown(html_score, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Salir al Menú Principal", use_container_width=True):
            reiniciar_todo()
            st.rerun()

if not st.session_state.quiz:
    st.markdown('<div class="hero-banner"><h1>MedTutor AI</h1><p>Tu asistente inteligente para arrasar en la carrera</p></div>', unsafe_allow_html=True)
    tab_pdf, tab_imagen, tab_guardados = st.tabs(["📄 Documentos (PDF)", "👁️ Anatomía (Visión)", "📁 Mis Decks Guardados"])
    
    with tab_pdf:
        st.write("### 📖 Sube tus apuntes o presentaciones")
        if not st.session_state.texto_pdf:
            archivo_subido = st.file_uploader("Arrastra aquí tu PDF", type=["pdf"], key="pdf_uploader", label_visibility="collapsed")
            if archivo_subido is not None:
                if st.button("🔍 Escanear Documento", type="primary", use_container_width=True):
                    if not api_key: st.error("⚠️ Falta la API Key.")
                    else:
                        with st.spinner("🤖 Leyendo cientos de páginas en segundos..."):
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                tmp.write(archivo_subido.read())
                                tmp_path = tmp.name
                            try:
                                loader = PyPDFLoader(tmp_path)
                                paginas = loader.load()
                                st.session_state.texto_pdf = "\n".join([pagina.page_content for pagina in paginas])
                                llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.1, google_api_key=api_key)
                                prompt_temas = PromptTemplate(
                                    template="Extrae un índice de temas.\n\nTexto: {texto}\n\n{format_instructions}", 
                                    input_variables=["texto"], 
                                    partial_variables={"format_instructions": parser_temario.get_format_instructions()}
                                )
                                cadena_temas = prompt_temas | llm | parser_temario
                                st.session_state.lista_temas = cadena_temas.invoke({"texto": st.session_state.texto_pdf}).temas
                                st.rerun()
                            except Exception as e: st.error(f"Error: {e}")
                            finally: os.unlink(tmp_path)
        else:
            st.success("✅ ¡Lectura completada!")
            with st.container(border=True):
                tema_elegido = st.selectbox("Selecciona el tema a repasar:", st.session_state.lista_temas)
                if st.button(f"⚡ Iniciar Quiz: {tema_elegido}", type="primary", use_container_width=True):
                    with st.spinner(f"Diseñando preguntas exclusivas sobre {tema_elegido}..."):
                        try:
                            llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.3, google_api_key=api_key)
                            prompt_quiz = PromptTemplate(
                                template="Crea 5 preguntas de opción múltiple enfocadas en: {tema_especifico}.\n{format_instructions}\n\nDocumento:\n{texto}", 
                                input_variables=["tema_especifico", "texto"], 
                                partial_variables={"format_instructions": parser_quiz.get_format_instructions()}
                            )
                            cadena_quiz = prompt_quiz | llm | parser_quiz
                            resultado_quiz = cadena_quiz.invoke({"tema_especifico": tema_elegido, "texto": st.session_state.texto_pdf})
                            quiz_generado = [p.dict() for p in resultado_quiz.preguntas]
                            st.session_state.quiz = quiz_generado
                            st.session_state.tema_actual = tema_elegido
                            guardar_en_historial(tema_elegido, quiz_generado)
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
            if st.button("🗑️ Elegir otro documento"):
                reiniciar_todo()
                st.rerun()

    with tab_imagen:
        st.write("### 🧠 Análisis de Diagramas")
        archivo_img = st.file_uploader("Sube un esquema de anatomía o apunte", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
        if archivo_img is not None:
            st.image(archivo_img, use_container_width=True)
            if st.button("👁️ Analizar y Generar Preguntas", type="primary", use_container_width=True):
                if not api_key: st.error("⚠️ Falta la API Key.")
                else:
                    with st.spinner("Visualizando estructuras médicas..."):
                        encoded_img = base64.b64encode(archivo_img.read()).decode('utf-8')
                        llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.3, google_api_key=api_key)
                        mensaje = HumanMessage(content=[
                            {"type": "text", "text": f"Crea 5 preguntas de opción múltiple sobre esta imagen anatómica.\n{parser_quiz.get_format_instructions()}"}, 
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_img}"}}
                        ])
                        try:
                            respuesta = llm.invoke([mensaje])
                            resultado_quiz = parser_quiz.parse(respuesta.content)
                            quiz_generado = [p.dict() for p in resultado_quiz.preguntas]
                            st.session_state.quiz = quiz_generado
                            st.session_state.tema_actual = "Anatomía Visual"
                            guardar_en_historial("Anatomía Visual", quiz_generado)
                            st.rerun()
                        except Exception as e: st.error(f"Error visual: {e}")

    # --- PESTAÑA MODIFICADA CON EL BOTÓN DE BORRAR ---
    with tab_guardados:
        st.write("### 🗃️ Tu Bóveda de Estudio")
        historial = cargar_historial()
        if not historial:
            st.info("💡 Aún no tienes quizzes guardados.")
        else:
            with st.container(border=True):
                deck_elegido = st.selectbox("Selecciona un deck de tu historial:", list(historial.keys()))
                
                # Dividimos los botones en dos columnas
                col_jugar, col_borrar = st.columns(2)
                with col_jugar:
                    if st.button("▶️ Jugar este Deck", type="primary", use_container_width=True):
                        st.session_state.quiz = historial[deck_elegido]
                        st.session_state.tema_actual = deck_elegido
                        st.session_state.indice_actual = 0
                        st.session_state.puntaje = 0
                        st.rerun()
                with col_borrar:
                    if st.button("🗑️ Borrar Deck", use_container_width=True):
                        borrar_del_historial(deck_elegido)
                        st.success(f"Deck eliminado correctamente.")
                        time.sleep(1) # Pequeña pausa para que alcance a leer el mensaje de éxito
                        st.rerun()

else:
    total_preguntas = len(st.session_state.quiz)
    indice = st.session_state.indice_actual
    
    st.markdown(f"**📚 Tema:** {st.session_state.tema_actual}")
    st.progress(indice / total_preguntas, text=f"Pregunta {indice + 1} de {total_preguntas}")
    
    if indice < total_preguntas:
        pregunta_actual = st.session_state.quiz[indice]
        
        if not st.session_state.opciones_revueltas:
            opciones = pregunta_actual["opciones"].copy()
            random.shuffle(opciones)
            st.session_state.opciones_revueltas = opciones

        pregunta_html = f"<div class='pregunta-caja'><h2 style='margin:0; font-size:1.4rem;'>🤔 {pregunta_actual['pregunta']}</h2></div>"
        st.markdown(pregunta_html, unsafe_allow_html=True)
        
        with st.container(border=True):
            opcion_seleccionada = st.radio("Selecciona tu respuesta:", st.session_state.opciones_revueltas, index=None, label_visibility="collapsed")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if not st.session_state.respuesta_revisada:
            if st.button("✨ Comprobar Respuesta", use_container_width=True, type="primary"):
                if opcion_seleccionada:
                    st.session_state.respuesta_revisada = True
                    st.rerun()
                else:
                    st.warning("☝️ Selecciona una opción primero.")
        else:
            if opcion_seleccionada == pregunta_actual["respuesta_correcta"]:
                st.success("## ¡Correcto! 🎉")
                st.toast('¡Excelente respuesta!', icon='✅')
                if st.session_state.respuesta_revisada_nueva_bandera:
                    st.session_state.puntaje += 1
            else:
                st.error("## Incorrecto ❌")
                st.info(f"**La respuesta correcta era:** {pregunta_actual['respuesta_correcta']}")
                st.toast('Sigue intentando, ¡tú puedes!', icon='💪')
            
            with st.expander("📚 Leer explicación médica detallada", expanded=True):
                st.write(pregunta_actual["explicacion"])
            
            if st.button("Siguiente Pregunta ⏭️", use_container_width=True):
                st.session_state.indice_actual += 1
                st.session_state.respuesta_revisada = False
                st.session_state.opciones_revueltas = []
                st.rerun()
                
            st.session_state.respuesta_revisada_nueva_bandera = False 
            
    else:
        st.balloons()
        html_victoria = '<div style="text-align: center; padding: 40px; background-color: var(--secondary-background-color); border-radius: 20px; border: 2px solid #00C9FF;"><h1 style="font-size: 4rem; margin: 0;">🎓</h1><h2 style="margin: 10px 0;">¡Bloque Completado!</h2><p style="font-size: 1.2rem; color: gray;">Has terminado esta sesión de estudio.</p></div>'
        st.markdown(html_victoria, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        csv_anki = generar_csv_anki(st.session_state.quiz)
        st.download_button(
            label="📥 Exportar a Anki (Flashcards CSV)",
            data=csv_anki,
            file_name=f"Anki_Deck_{st.session_state.tema_actual.replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔁 Repetir este bloque", use_container_width=True):
                st.session_state.indice_actual = 0
                st.session_state.puntaje = 0
                st.session_state.respuesta_revisada = False
                st.rerun()
        with col2:
            if st.button("🏠 Ir al Menú Principal", use_container_width=True, type="primary"):
                reiniciar_todo()
                st.rerun()