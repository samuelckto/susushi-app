import os
from flask import Flask, render_template, request, redirect, session
import pymysql

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

# =========================
# VARIABLES DE ENTORNO
# =========================

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT", 3306))

# =========================
# CONEXIÓN A MYSQL
# =========================

def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        cursorclass=pymysql.cursors.DictCursor
    )

# =========================
# LOGIN
# =========================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        connection = get_connection()
        with connection.cursor() as cursor:
            sql = "SELECT * FROM usuarios WHERE username=%s AND password_hash=%s"
            cursor.execute(sql, (username, password))
            user = cursor.fetchone()
        connection.close()

        if user:
            session["user"] = user["username"]
            return redirect("/dashboard")
        else:
            return "Usuario o contraseña incorrectos"

    return render_template("login.html")

# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    return render_template("dashboard.html")

# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# =========================
# RENDER PORT FIX
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
