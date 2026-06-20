from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql

app = Flask(__name__)
app.secret_key = "practice_secret_key"


def get_db():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="repair_service_db",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )


@app.route("/")
def index():
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        login = request.form["login"].strip()
        password = request.form["password"].strip()
        full_name = request.form["full_name"].strip()
        phone = request.form["phone"].strip()
        email = request.form["email"].strip()

        if len(password) < 8:
            flash("Пароль должен быть не менее 8 символов")
            return redirect("/register")

        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE login = %s", (login,))
            existing_user = cursor.fetchone()

            if existing_user:
                flash("Пользователь с таким логином уже существует")
                return redirect("/register")

            password_hash = generate_password_hash(password)

            cursor.execute("""
                INSERT INTO users (login, password_hash, full_name, phone, email, role)
                VALUES (%s, %s, %s, %s, %s, 'user')
            """, (login, password_hash, full_name, phone, email))

            db.commit()

        db.close()
        flash("Регистрация выполнена успешно")
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_value = request.form["login"].strip()
        password = request.form["password"].strip()

        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE login = %s", (login_value,))
            user = cursor.fetchone()
        db.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["full_name"] = user["full_name"]

            if user["role"] == "admin":
                return redirect("/admin")

            return redirect("/dashboard")

        flash("Неверный логин или пароль")
        return redirect("/login")

    return render_template("login.html")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()

    if request.method == "POST":
        device_type = request.form["device_type"].strip()
        problem_description = request.form["problem_description"].strip()
        contact_method = request.form["contact_method"].strip()

        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO requests 
                (user_id, status_id, device_type, problem_description, contact_method)
                VALUES (%s, 1, %s, %s, %s)
            """, (session["user_id"], device_type, problem_description, contact_method))
            db.commit()

        flash("Заявка создана")

    with db.cursor() as cursor:
        cursor.execute("""
            SELECT requests.id, requests.device_type, requests.problem_description,
                   requests.contact_method, requests.created_at, statuses.name AS status_name
            FROM requests
            JOIN statuses ON requests.status_id = statuses.id
            WHERE requests.user_id = %s
            ORDER BY requests.id DESC
        """, (session["user_id"],))
        requests_list = cursor.fetchall()

    db.close()

    return render_template("dashboard.html", requests_list=requests_list)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/login")

    db = get_db()

    if request.method == "POST":
        request_id = request.form["request_id"]
        status_id = request.form["status_id"]

        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE requests SET status_id = %s WHERE id = %s",
                (status_id, request_id)
            )
            db.commit()

        flash("Статус заявки обновлен")

    with db.cursor() as cursor:
        cursor.execute("""
            SELECT requests.id, users.full_name, requests.device_type,
                   requests.problem_description, requests.contact_method,
                   requests.created_at, statuses.name AS status_name
            FROM requests
            JOIN users ON requests.user_id = users.id
            JOIN statuses ON requests.status_id = statuses.id
            ORDER BY requests.id DESC
        """)
        all_requests = cursor.fetchall()

        cursor.execute("SELECT * FROM statuses")
        statuses = cursor.fetchall()

    db.close()

    return render_template("admin.html", all_requests=all_requests, statuses=statuses)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/create-admin")
def create_admin():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE login = 'admin'")
        admin_user = cursor.fetchone()

        if not admin_user:
            password_hash = generate_password_hash("admin12345")
            cursor.execute("""
                INSERT INTO users (login, password_hash, full_name, phone, email, role)
                VALUES ('admin', %s, 'Администратор системы', '89990000000', 
                        'admin@example.com', 'admin')
            """, (password_hash,))
            db.commit()

    db.close()
    return "Администратор создан. Логин: admin, пароль: admin12345"


if __name__ == "__main__":
    app.run(debug=True)