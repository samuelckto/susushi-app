import os
import mysql.connector
from flask import Flask, request, render_template, redirect, url_for, session, send_file, flash
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
import io

app = Flask(__name__)
# Usamos tu clave secreta de preferencia
app.secret_key = os.environ.get('SECRET_KEY', '051399_susushi_master_key')

# Configuración de la base de datos (Sincronizada con Aiven)
db_config = {
    'host': os.environ.get('DB_HOST', 'sushi-susushi.b.aivencloud.com'),
    'user': os.environ.get('DB_USER', 'avnadmin'),
    'password': os.environ.get('DB_PASSWORD', 'AVNS_–8nH3Gb3NGrKBRAI5Ln'), # Clave real de Aiven
    'database': os.environ.get('DB_NAME', 'defaultdb'),
    'port': int(os.environ.get('DB_PORT', 28593))
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# --- RUTAS DE NAVEGACIÓN ---

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    # 'sucursal' es el nombre del input en tu login.html
    usuario_input = request.form.get('sucursal', '').strip()
    password_input = request.form.get('password', '').strip()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Consulta usando las columnas reales de tu tabla 'usuarios'
        query = "SELECT * FROM usuarios WHERE (username = %s OR nombre_sucursal = %s) AND password_hash = %s"
        cursor.execute(query, (usuario_input, usuario_input, password_input))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['rol'] = user['rol']
            session['sucursal'] = user.get('nombre_sucursal', 'Admin')
            
            if session['rol'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('ver_pedido'))
            
        return "<h1>❌ Acceso denegado. <a href='/'>Volver</a></h1>"
    except Exception as e:
        return f"<h1>Error de DB: {str(e)}</h1>"

# --- PANEL DE SUCURSAL (PEDIDOS) ---

@app.route('/pedido')
def ver_pedido():
    if 'username' not in session: return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos ORDER BY categoria ASC")
    prods = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('pedido.html', sucursal=session.get('sucursal'), productos=prods)

# --- PANEL DE ADMINISTRACIÓN ---

@app.route('/admin')
def admin_dashboard():
    if session.get('rol') != 'admin': return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # Cargar productos
    cursor.execute("SELECT * FROM productos ORDER BY nombre ASC")
    prods = cursor.fetchall()
    
    # Lógica para listar PDFs de reportes (si los guardas en disco)
    lista_pdfs = []
    if os.path.exists('pedidos_pdf'):
        for f in os.listdir('pedidos_pdf'):
            if f.endswith('.pdf'):
                lista_pdfs.append({'nombre': f})
                
    cursor.close()
    conn.close()
    return render_template('admin.html', productos=prods, pedidos=lista_pdfs, user=session['username'])

@app.route('/salir')
def salir():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Render usa el puerto que le asigne el entorno
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port))
