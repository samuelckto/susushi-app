import os
import mysql.connector
from flask import Flask, request, render_template, redirect, url_for, session, send_file, flash
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
import io

app = Flask(__name__)

# Clave secreta
app.secret_key = os.environ.get('SECRET_KEY', '051399_susushi_master_key')

# Configuración de base de datos (SIN contraseña hardcodeada)
db_config = {
    'host': os.environ.get('DB_HOST', 'sushi-susushi.b.aivencloud.com'),
    'user': os.environ.get('DB_USER', 'avnadmin'),
    'password': os.environ.get('DB_PASSWORD'),  # 🔐 SOLO variable de entorno
    'database': os.environ.get('DB_NAME', 'defaultdb'),
    'port': int(os.environ.get('DB_PORT', 28593))
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# ------------------ RUTAS ------------------

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario_input = request.form.get('sucursal', '').strip()
        password_input = request.form.get('password', '').strip()
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            query = """
            SELECT * FROM usuarios 
            WHERE (username = %s OR nombre_sucursal = %s) 
            AND password_hash = %s
            """
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
                
            flash("❌ Acceso denegado. Revisa tus credenciales.")
        except Exception as e:
            return f"<h1>Error de DB: {str(e)}</h1>"

    return render_template('login.html')

@app.route('/pedido')
def ver_pedido():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos ORDER BY categoria ASC")
    prods = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('pedido.html', sucursal=session.get('sucursal'), productos=prods)

@app.route('/admin')
def admin_dashboard():
    if session.get('rol') != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos ORDER BY nombre ASC")
    prods = cursor.fetchall()
    
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
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
