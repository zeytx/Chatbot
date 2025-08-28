

import sqlite3
import requests
import threading
import time
import os
from pyngrok import ngrok

# Configurar el token de autenticación de ngrok
ngrok.set_auth_token("API-KEY)

# Clave API de OpenAI
api_key = "API-KEY"

# Crear el archivo app.py mejorado para Streamlit
app_content = f'''
import streamlit as st
import requests
import sqlite3
import os
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Asistente Virtual Jessi",
    page_icon="🤖",
    layout="wide"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-header {{
        text-align: center;
        color: #2E86AB;
        padding: 1rem 0;
    }}
    .chat-message {{
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-radius: 10px;
    }}
    .user-message {{
        background-color: #E3F2FD;
        margin-left: 2rem;
    }}
    .assistant-message {{
        background-color: #F5F5F5;
        margin-right: 2rem;
    }}
</style>
""", unsafe_allow_html=True)

# Conectar a la base de datos SQLite
@st.cache_resource
def init_database():
    conn = sqlite3.connect('chat_history.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
        )
    """)
    conn.commit()
    return conn, c

conn, c = init_database()

# Tu clave de API de OpenAI
api_key = "{api_key}"

def crear_nueva_sesion():
    """Crea una nueva sesión de chat"""
    session_name = f"Chat {{datetime.now().strftime('%Y-%m-%d %H:%M')}}"
    c.execute('INSERT INTO chat_sessions (session_name) VALUES (?)', (session_name,))
    conn.commit()
    return c.lastrowid

def guardar_chat(session_id, role, content):
    """Guarda un mensaje de chat en la base de datos"""
    c.execute('INSERT INTO chats (session_id, role, content) VALUES (?, ?, ?)', 
              (session_id, role, content))
    conn.commit()

def obtener_respuesta(conversation_history):
    """Obtiene una respuesta del modelo GPT-3.5-turbo"""
    try:
        headers = {{
            "Content-Type": "application/json",
            "Authorization": f"Bearer {{api_key}}"
        }}
        data = {{
            "model": "gpt-3.5-turbo",
            "messages": conversation_history,
            "temperature": 0.7,
            "max_tokens": 1000
        }}
        response = requests.post("https://api.openai.com/v1/chat/completions", 
                               json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"Error {{response.status_code}}: {{response.text}}"
    except Exception as e:
        return f"Error de conexión: {{str(e)}}"

def cargar_sesiones():
    """Carga todas las sesiones de chat"""
    c.execute('SELECT id, session_name, created_at FROM chat_sessions ORDER BY created_at DESC')
    return c.fetchall()

def cargar_historial_sesion(session_id):
    """Carga el historial de una sesión específica"""
    c.execute('SELECT role, content, timestamp FROM chats WHERE session_id = ? ORDER BY timestamp', 
              (session_id,))
    return c.fetchall()

def eliminar_sesion(session_id):
    """Elimina una sesión y todos sus mensajes"""
    c.execute('DELETE FROM chats WHERE session_id = ?', (session_id,))
    c.execute('DELETE FROM chat_sessions WHERE id = ?', (session_id,))
    conn.commit()

# Inicializar estado de la sesión
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = None
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = [
        {{"role": "system", "content": "Eres un asistente AI útil y amable llamado Jessi."}}
    ]
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Título principal
st.markdown('<h1 class="main-header">🤖 Asistente Virtual - Jessi</h1>', unsafe_allow_html=True)

# Barra lateral
with st.sidebar:
    st.header("📝 Gestión de Chats")
    
    # Botón para nuevo chat
    if st.button("➕ Nuevo Chat", use_container_width=True):
        st.session_state.current_session_id = crear_nueva_sesion()
        st.session_state.conversation_history = [
            {{"role": "system", "content": "Eres un asistente AI útil y amable llamado Jessi."}}
        ]
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    # Lista de sesiones guardadas
    st.subheader("💬 Chats Guardados")
    sesiones = cargar_sesiones()
    
    if sesiones:
        for session_id, session_name, created_at in sesiones:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if st.button(session_name, key=f"session_{{session_id}}", use_container_width=True):
                    st.session_state.current_session_id = session_id
                    # Cargar historial de la sesión
                    historial = cargar_historial_sesion(session_id)
                    st.session_state.conversation_history = [
                        {{"role": "system", "content": "Eres un asistente AI útil y amable llamado Jessi."}}
                    ]
                    st.session_state.messages = []
                    for role, content, timestamp in historial:
                        st.session_state.conversation_history.append({{"role": role, "content": content}})
                        st.session_state.messages.append({{"role": role, "content": content}})
                    st.rerun()
            
            with col2:
                if st.button("🗑️", key=f"delete_{{session_id}}", help="Eliminar chat"):
                    eliminar_sesion(session_id)
                    if st.session_state.current_session_id == session_id:
                        st.session_state.current_session_id = None
                        st.session_state.conversation_history = [
                            {{"role": "system", "content": "Eres un asistente AI útil y amable llamado Jessi."}}
                        ]
                        st.session_state.messages = []
                    st.rerun()
    else:
        st.info("No hay chats guardados")

# Área principal de chat
if st.session_state.current_session_id:
    st.subheader(f"💬 Sesión Activa: {{st.session_state.current_session_id}}")
else:
    st.subheader("💬 Chat Temporal")
    st.info("Inicia un nuevo chat para guardar la conversación")

# Mostrar historial de conversación
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        if message['role'] == 'user':
            user_html = f"""
<div class="chat-message user-message">
    <strong>🧑 Tú:</strong> {{message['content']}}
</div>
"""
            st.markdown(user_html, unsafe_allow_html=True)
        elif message['role'] == 'assistant':
            assistant_html = f"""
<div class="chat-message assistant-message">
    <strong>🤖 Jessi:</strong> {{message['content']}}
</div>
"""
            st.markdown(assistant_html, unsafe_allow_html=True)

# Entrada de texto para nuevo mensaje
st.divider()

# Input del usuario
user_input = st.chat_input("💬 Escribe tu mensaje aquí...")

# Procesar mensaje del usuario
if user_input:
    # Si no hay sesión activa, crear una nueva
    if not st.session_state.current_session_id:
        st.session_state.current_session_id = crear_nueva_sesion()
    
    # Agregar mensaje del usuario
    st.session_state.conversation_history.append({{"role": "user", "content": user_input}})
    st.session_state.messages.append({{"role": "user", "content": user_input}})
    guardar_chat(st.session_state.current_session_id, "user", user_input)
    
    # Mostrar mensaje del usuario inmediatamente
    user_html = f"""
<div class="chat-message user-message">
    <strong>🧑 Tú:</strong> {{user_input}}
</div>
"""
    st.markdown(user_html, unsafe_allow_html=True)
    
    # Obtener respuesta del asistente
    with st.spinner("🤔 Pensando..."):
        bot_response = obtener_respuesta(st.session_state.conversation_history)
    
    # Agregar respuesta del asistente
    st.session_state.conversation_history.append({{"role": "assistant", "content": bot_response}})
    st.session_state.messages.append({{"role": "assistant", "content": bot_response}})
    guardar_chat(st.session_state.current_session_id, "assistant", bot_response)
    
    # Mostrar respuesta del asistente
    assistant_html = f"""
<div class="chat-message assistant-message">
    <strong>🤖 Jessi:</strong> {{bot_response}}
</div>
"""
    st.markdown(assistant_html, unsafe_allow_html=True)
    
    # Recargar para actualizar el historial
    st.rerun()

# Información en el pie de página
st.divider()
st.markdown("---")
st.markdown("💡 **Consejos:** Puedes crear múltiples chats y alternar entre ellos. Todos tus chats se guardan automáticamente.")
'''

# Escribir el archivo app.py
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_content)

print("✅ Archivo app.py creado exitosamente")

# Función para ejecutar Streamlit en un hilo separado
def run_streamlit():
    import subprocess
    import sys
    
    # Ejecutar Streamlit
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py", "--server.port=8501", "--server.headless=true"], 
                   capture_output=False)

# Iniciar Streamlit en un hilo separado
print("🚀 Iniciando servidor Streamlit...")
streamlit_thread = threading.Thread(target=run_streamlit, daemon=True)
streamlit_thread.start()

# Esperar un momento para que el servidor se inicie
time.sleep(3)

# Crear túnel público con ngrok
print("🌐 Creando túnel público con ngrok...")
try:
    public_url = ngrok.connect(8501)
    print(f"✅ ¡Aplicación disponible públicamente en: {public_url}")
    print(f"🔗 URL: {public_url}")
    print("\n" + "="*50)
    print("🎉 ¡Tu chatbot está listo!")
    print("📱 Puedes compartir la URL con cualquier persona")
    print("💾 Todos los chats se guardan automáticamente")
    print("="*50)
    
    # Mantener el túnel activo
    input("\n⏸️  Presiona Enter para detener la aplicación...")
    
except Exception as e:
    print(f"❌ Error al crear el túnel: {e}")
    print("💡 Intenta ejecutar las celdas nuevamente")

finally:
    # Cerrar conexiones
    try:
        ngrok.disconnect(public_url)
        ngrok.kill()
    except:
        pass
    print("🛑 Aplicación detenida")