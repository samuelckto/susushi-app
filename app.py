import os
import mysql.connector
from flask import Flask, request, render_template, redirect, url_for, session, send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime

app = Flask(__name__)
app.secret_key = '051399_susushi_master_key'

# Configuración flexible para Local (Mac) y Nube (Aiven)
db_config = {
    'host': os.environ.get('DB_HOST', 'sushi-susushi.b.aivencloud.com'),
    'user': os.environ.get('DB_USER', 'avnadmin'),
    'password': os.environ.get('DB_PASSWORD', 'TU_PASSWORD_DE_AIVEN'), 
    'database': os.environ.get('DB_NAME', 'defaultdb'),
    'port': int(os.environ.get('DB_PORT', 28593))
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    usuario_input = request.form.get('sucursal', '').strip()
    password_input = request.form.get('password', '').strip()
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM usuarios WHERE (nombre_sucursal = %s OR username = %s) AND password_hash = %s"
        cursor.execute(query, (usuario_input, usuario_input, password_input))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            session['rol'] = user.get('rol', 'sucursal')
            session['sucursal'] = user.get('nombre_sucursal')
            return redirect(url_for('admin_dashboard') if session['rol'] == 'admin' else url_for('ver_pedido'))
        return "<h1>❌ Acceso denegado. <a href='/'>Volver</a></h1>"
    except Exception as e:
        return f"<h1>Error de DB: {str(e)}</h1>"

@app.route('/pedido')
def ver_pedido():
    if 'sucursal' not in session: return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos ORDER BY categoria ASC")
    prods = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('pedido.html', sucursal=session['sucursal'], productos=prods)

@app.route('/enviar-pedido', methods=['POST'])
def enviar_pedido():
    if 'sucursal' not in session: return redirect(url_for('index'))
    sucursal = session['sucursal']
    obs = request.form.get('observaciones', 'Sin observaciones').strip()
    ahora = datetime.now()
    fecha_str = ahora.strftime("%d/%m/%Y")
    hora_str = ahora.strftime("%H:%M:%S")
    timestamp = ahora.strftime("%Y%m%d_%H%M%S")
    
    if not os.path.exists('pedidos_pdf'): os.makedirs('pedidos_pdf')
    nombre_pdf = f"Pedido_{sucursal.replace(' ', '_')}_{timestamp}.pdf"
    ruta_pdf = os.path.join('pedidos_pdf', nombre_pdf)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        c = canvas.Canvas(ruta_pdf, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 750, "SUSUSHI - REPORTE DE INVENTARIO")
        c.setFont("Helvetica", 12)
        c.drawString(50, 730, f"Sucursal: {sucursal}")
        c.drawString(50, 715, f"Fecha: {fecha_str} | Hora: {hora_str}")
        c.line(50, 705, 550, 705)
        
        y = 680
        for key, value in request.form.items():
            if key.startswith('prod_') and value.strip() and value != "0":
                pid = key.replace('prod_', '')
                cursor.execute("SELECT nombre, unidad_medida FROM productos WHERE id = %s", (pid,))
                p = cursor.fetchone()
                if p:
                    c.drawString(50, y, f"{p['nombre']}: {value} {p['unidad_medida']}")
                    y -= 20
        
        y -= 20
        c.line(50, y+10, 550, y+10)
        c.drawString(50, y, "Observaciones:")
        c.setFont("Helvetica-Oblique", 11)
        text_obj = c.beginText(50, y-20)
        text_obj.textLines(obs)
        c.drawText(text_obj)
        c.save()
        cursor.close()
        conn.close()
        
        return f"""
        <body style="font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; background: #f0f2f5; margin: 0;">
            <div style="background: white; padding: 40px; border-radius: 20px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.05);">
                <h1 style="color: #27ae60;">✅ ¡Enviado!</h1>
                <p>Reporte de <b>{sucursal}</b> generado con éxito.</p>
                <div style="margin-top: 25px;">
                    <a href="/pedido" style="text-decoration: none; background: #3498db; color: white; padding: 12px 25px; border-radius: 10px;">Nuevo Pedido</a>
                </div>
            </div>
        </body>
        """
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/admin')
def admin_dashboard():
    if session.get('rol') != 'admin': return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos ORDER BY nombre ASC")
    prods = cursor.fetchall()
    
    lista_pdfs = []
    if os.path.exists('pedidos_pdf'):
        for f in os.listdir('pedidos_pdf'):
            if f.endswith('.pdf'):
                stats = os.stat(os.path.join('pedidos_pdf', f))
                dt = datetime.fromtimestamp(stats.st_ctime)
                lista_pdfs.append({'nombre': f, 'fecha_str': dt.strftime('%d/%m/%Y %H:%M'), 'fecha_dt': dt})
    lista_pdfs = sorted(lista_pdfs, key=lambda x: x['fecha_dt'], reverse=True)
    cursor.close()
    conn.close()
    return render_template('admin.html', productos=prods, pedidos=lista_pdfs)

@app.route('/admin/crear-usuario', methods=['POST'])
def crear_usuario():
    if session.get('rol') != 'admin': return redirect(url_for('index'))
    un, pw, suc, rol = request.form.get('username'), request.form.get('password'), request.form.get('nombre_sucursal'), request.form.get('rol')
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("INSERT INTO usuarios (username, password_hash, rol, nombre_sucursal) VALUES (%s, %s, %s, %s)", (un, pw, rol, suc))
    conn.commit(); cursor.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/agregar', methods=['POST'])
def agregar():
    if session.get('rol') != 'admin': return redirect(url_for('index'))
    n, u, c = request.form.get('nombre'), request.form.get('unidad'), request.form.get('categoria')
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("INSERT INTO productos (nombre, unidad_medida, categoria) VALUES (%s, %s, %s)", (n, u, c))
    conn.commit(); cursor.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/eliminar/<int:id>')
def eliminar_producto(id):
    if session.get('rol') != 'admin': return redirect(url_for('index'))
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM productos WHERE id = %s", (id,))
    conn.commit(); cursor.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/ver/<nombre>')
def ver_pdf(nombre):
    if session.get('rol') != 'admin': return redirect(url_for('index'))
    return send_file(os.path.join('pedidos_pdf', nombre))

@app.route('/admin/eliminar-reporte/<nombre>')
def eliminar_reporte(nombre):
    if session.get('rol') != 'admin': return redirect(url_for('index'))
    ruta = os.path.join('pedidos_pdf', nombre)
    if os.path.exists(ruta): os.remove(ruta)
    return redirect(url_for('admin_dashboard'))

@app.route('/salir')
def salir():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
