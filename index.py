import re
from flask import Flask, Response, render_template, redirect, url_for, request, session, flash
from werkzeug.security import generate_password_hash
import database as db
from datetime import datetime, date

app = Flask(__name__, template_folder="templates")
app.secret_key = "clave_super_secreta"

# Configura el manejo automático de conexiones por cada petición
db.init_app(app)

# ELIMINADO: cursor = db.conexion.cursor() 
# (Los cursores se deben crear DENTRO de cada función/ruta)

# -------------------------------------------------------------------------------------------------------#

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

#-------------------------------------------------------------------------------------------------------#

from rutas_estudiante import estudiante_bp

from rutas_profesor import profesor_bp

# 2. REGISTRAS LOS ARCHIVOS EN LA APP
app.register_blueprint(estudiante_bp)

app.register_blueprint(profesor_bp)

#-------------------------------------------------------------------------------------------------------#

@app.route("/")
def logout():

    session.clear()

    return redirect(url_for("cursos_publicos"))

@app.route("/colaboracion")
def colaboracion():

    if "user_id" not in session:
            return redirect(url_for("login"))
    
       
    
    return render_template("VisPUBLIC/colaboracion.html" )


# login-------------------------------------------------------------------------------------------------------#


@app.route("/cambiar-password", methods=["GET", "POST"])
def cambiar_password():
    conexion = db.get_db()

    if request.method == "POST":

        # ==========================================
        # OBTENER DATOS DEL FORMULARIO
        # ==========================================

        email = request.form.get("email", "").strip().lower()
        contrasena = request.form.get("contrasena", "")
        confirm_password = request.form.get("confirm_password", "")

        errores = []

        # ==========================================
        # VALIDAR EMAIL
        # ==========================================

        if not email:

            errores.append(
                "El correo electrónico es obligatorio."
            )

        elif not re.match(
            r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
            email
        ):

            errores.append(
                "Ingresa un correo electrónico válido."
            )

        # ==========================================
        # VALIDAR CONTRASEÑA
        # ==========================================

        if not contrasena:

            errores.append(
                "La contraseña es obligatoria."
            )

        elif len(contrasena) < 5:

            errores.append(
                "La contraseña debe tener al menos 5 caracteres."
            )

        # ==========================================
        # CONFIRMAR CONTRASEÑA
        # ==========================================

        if not confirm_password:

            errores.append(
                "Debes confirmar la contraseña."
            )

        elif contrasena != confirm_password:

            errores.append(
                "Las contraseñas no coinciden."
            )

        # ==========================================
        # SI HAY ERRORES
        # ==========================================

        if errores:

            return render_template(
                "VisPUBLIC/cambiar_password.html",
                errores=errores,
                email=email
            )

        # ==========================================
        # BUSCAR USUARIO
        # ==========================================

        try:

            
            cursor = conexion.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT id, email
                FROM estudiante
                WHERE email = %s
                """,
                (email,)
            )

            usuario = cursor.fetchone()

            cursor.close()

            # ==========================================
            # USUARIO NO EXISTE
            # ==========================================

            if not usuario:

                return render_template(
                    "VisPUBLIC/cambiar_password.html",
                    errores=[
                        "No existe una cuenta registrada con ese correo."
                    ],
                    email=email
                )

            # ==========================================
            # ACTUALIZAR CONTRASEÑA
            # ==========================================
            
            cursor =conexion.cursor()

            cursor.execute(
                """
                UPDATE estudiante
                SET contrasena = %s
                WHERE id = %s
                """,
                (
                    contrasena,
                    usuario["id"]
                )
            )

            conexion.commit()

            cursor.close()

            # ==========================================
            # CONTRASEÑA ACTUALIZADA
            # ==========================================

            return render_template(
                "VisPUBLIC/cambiar_password.html",
                errores=[],
                email=email,
                mensaje="Contraseña actualizada correctamente."
            )

        except Exception as e:

            print(
                "ERROR AL CAMBIAR CONTRASEÑA:",
                e
            )

            try:
                conexion.rollback()
            except:
                pass

            try:
                cursor.close()
            except:
                pass

            return render_template(
                "VisPUBLIC/cambiar_password.html",
                errores=[str(e)],
                email=email
            )

    # ==========================================
    # GET
    # ==========================================

    return render_template(
        "VisPUBLIC/cambiar_password.html",
        errores=[]
    )




# login-------------------------------------------------------------------------------------------------------#

@app.route("/economico")
def economico():

    if "user_id" not in session:
            return redirect(url_for("login"))
    
       
    
    return render_template("VisPUBLIC/colabEconomica.html")


# login-------------------------------------------------------------------------------------------------------#
@app.route("/cursos")
def cursos_publicos():

    conexion = db.get_db()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute(
            """
            SELECT
        cursos.*,
        COUNT(DISTINCT lecciones.id) AS total_lecciones,
        COUNT(DISTINCT inscripciones.estudiante_id) AS total_estudiantes
            FROM cursos
        LEFT JOIN lecciones
        ON cursos.id = lecciones.curso_id
        LEFT JOIN inscripciones
        ON cursos.id = inscripciones.curso_id
        GROUP BY cursos.id
            """
        )

    cursos = cursor.fetchall()
    cursor.close()

    return render_template(
        "VisPUBLIC/cursos.html",
        cursos=cursos
    )
# login-------------------------------------------------------------------------------------------------------#
@app.route("/login", methods=["GET", "POST"])
def login():
    conexion = db.get_db()
    if request.method == "POST":

        email = request.form["email"]
        contrasena = request.form["contrasena"]

        cursor =conexion.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT * FROM estudiante
            WHERE email=%s
            AND contrasena=%s
            """,
            (email, contrasena),
        )

        user = cursor.fetchone()

        cursor.close()

        if user:

            # 🔥 GUARDAR SESIÓN
            session["user_id"] = user["id"]
            session["nombre"] = user["nombre"]
            session["rol"] = user["rol"]

            # 🔥 REDIRECCIONES
            if user["rol"] == "ADMIN":

                return redirect(url_for("home"))

            elif user["rol"] == "ESTUDIANTE":

                return redirect(url_for("estudiante.menuUser"))

            elif user["rol"] == "PROFESOR":
            
                return redirect(url_for("profesor.menuInstru"))
        else:

            error = "Correo o contraseña incorrectos"

            return render_template("VisUSERT/login.html", error=error)

    return render_template("VisUSERT/login.html")


# ADMIN-------------------------------------------------------------------------------------------------------#


@app.route("/admin")
def home():
    return render_template("admin/index.html")



# USERS-------------------------------------------------------------------------------------------------------#


@app.route("/users", methods=["GET"])
def users():
    conexion = db.get_db()
    if conexion.is_connected():
        cursor =conexion.cursor()
        cursor.execute("SELECT * FROM estudiante")
        myresult = cursor.fetchall()
        insertObject = []
        columnNames = [column[0] for column in cursor.description]
        for record in myresult:
            insertObject.append(dict(zip(columnNames, record)))
        cursor.close()
    return render_template("users/users.html", data=insertObject)


@app.route("/form_user", methods=["GET", "POST"])
def add_user():
    conexion = db.get_db()
    if request.method == "POST":

       
        nombre = request.form["nombre"]
        edad = request.form["edad"]
        email = request.form["email"]
        contrasena = request.form["contrasena"]
        rol = request.form["rol"]
        fecha_registro = request.form["fecha_registro"]

        error = None
    

        # VALIDACIONES
        if len(nombre) < 3:
            error = "Nombre muy corto"


           

        

        if not email or "@" not in email:
            error = "Email inválido"

        if len(contrasena) < 5:
            error = "Contraseña muy corta"

            

        fecha = datetime.strptime(fecha_registro, "%Y-%m-%d").date()

        if fecha > date.today():
            error = "No se permiten fechas futuras"

        if error:
            return render_template("users/form.html", error=error)

        try:

            cursor = conexion.cursor()

            cursor.execute(
                """
            INSERT INTO estudiante (nombre,edad,email,contrasena,rol,fecha_registro)
            VALUES (%s,%s,%s,%s,%s,%s)
            """,
                (nombre,edad, email, contrasena, rol, fecha_registro),
            )

            conexion.commit()
            cursor.close()

            return redirect(url_for("users"))

        except Exception as e:

            conexion.rollback()
            return render_template("users/form.html", error=str(e))

    pass
    return render_template("users/form.html", user=None)


@app.route("/edit_user/<int:id>", methods=["GET", "POST"])
def edit_user(id):
    conexion = db.get_db()
    cursor = conexion.cursor(dictionary=True)

    if request.method == "POST":

        nombre = request.form.get("nombre", "").strip()
        edad = request.form.get("edad", "").strip()
        email = request.form.get("email", "").strip()
        contrasena = request.form.get("contrasena", "")
        rol = request.form.get("rol", "").strip()
        fecha_registro = request.form.get("fecha_registro", "").strip()

        cursor.execute("""
            UPDATE estudiante
            SET nombre = %s,
                edad = %s,
                email = %s,
                contrasena = %s,
                rol = %s,
                fecha_registro = %s
            WHERE id = %s
        """, (
            nombre,
            edad,
            email,
            contrasena,
            rol,
            fecha_registro,
            id
        ))

        conexion.commit()
        cursor.close()

        return redirect(url_for("users"))

    cursor.execute("""
        SELECT *
        FROM estudiante
        WHERE id = %s
    """, (id,))

    user = cursor.fetchone()

    cursor.close()

    if not user:
        return "Usuario no encontrado", 404

    return render_template(
        "users/form.html",
        user=user
    )


@app.route("/deleteUS/<int:id>", methods=["POST"])
def deleteUS(id):
    conexion = db.get_db()
    cursor = conexion.cursor()
    sql = "DELETE FROM estudiante WHERE id = %s"
    data = (id,)
    cursor.execute(sql, data)
    conexion.commit()
    return redirect(url_for("users"))


# COURSES--------------------------------------------------------------------------------------------------#


@app.route("/courses", methods=["GET"])
def courses():
    conexion = db.get_db()
    if conexion.is_connected():
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM cursos")
        myresult = cursor.fetchall()
        insertObject = []
        columnNames = [column[0] for column in cursor.description]
        for record in myresult:
            insertObject.append(dict(zip(columnNames, record)))
        cursor.close()
    return render_template("courses/courses.html", data=insertObject)


@app.route("/form_course", methods=["GET", "POST"])
def add_course():
    conexion = db.get_db()
    cursor = conexion.cursor(dictionary=True)

    # 🔹 Traer instructores para el select
    cursor.execute("""
    SELECT id, nombre
    FROM estudiante
    WHERE rol = 'PROFESOR'
    """)

    profesores = cursor.fetchall()

    if request.method == "POST":

        titulo = request.form["titulo"]
        descripcion = request.form["descripcion"]
        contenido = request.form["contenido"]
        profesor_id = request.form["profesor_id"]
       
        error = None

       
        if error:
            return render_template("courses/form.html", error=error, profesores=None)

        try:

            cursor.execute(
                """
            INSERT INTO cursos (titulo, descripcion, contenido, profesor_id)
            VALUES (%s,%s,%s,%s)
            """,
                (titulo, descripcion, contenido, profesor_id),
            )

            conexion.commit()

            return redirect(url_for("courses"))

        except Exception as e:

            conexion.rollback()
            return render_template(
                "courses/form.html", error=str(e), profesores=profesores
            )

    return render_template("courses/form.html", profesores=profesores)


@app.route("/edit_course/<int:id>", methods=["GET", "POST"])
def edit_course(id):

    conexion = db.get_db()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, nombre
        FROM estudiante
        WHERE rol = 'PROFESOR'
    """)

    profesores = cursor.fetchall()

    if request.method == "POST":

        titulo = request.form["titulo"]
        descripcion = request.form["descripcion"]
        contenido = request.form["contenido"]
        profesor_id = request.form["profesor_id"]

        try:

            cursor.execute("""
                UPDATE cursos
                SET titulo=%s,
                    descripcion=%s,
                    contenido=%s,
                    profesor_id=%s
                WHERE id=%s
            """, (
                titulo,
                descripcion,
                contenido,
                profesor_id,
                id
            ))

            conexion.commit()

            return redirect(url_for("courses"))

        except Exception as e:

            conexion.rollback()
            return str(e), 500

    cursor.execute(
        "SELECT * FROM cursos WHERE id=%s",
        (id,)
    )

    curso = cursor.fetchone()

    cursor.close()

    return render_template(
        "courses/form.html",
        curso=curso,
        profesores=profesores
    )

@app.route("/deleteCUR/<int:id>", methods=["POST"])
def deleteCUR(id):

    conexion = db.get_db()
    cursor = conexion.cursor()

    try:
        sql = "DELETE FROM cursos WHERE id = %s"
        cursor.execute(sql, (id,))
        conexion.commit()

    except Exception as e:
        conexion.rollback()
        return str(e), 500

    finally:
        cursor.close()

    return redirect(url_for("courses"))


# LESSONS--------------------------------------------------------------------------------------------------#


@app.route("/lessons", methods=["GET"])
def lessons():
    conexion = db.get_db()

    if conexion.is_connected():
    
        cursor = conexion.cursor(dictionary=True)
    
        cursor.execute("""
                SELECT
                    l.id,
                    l.curso_id,
                    c.titulo AS curso_titulo,
                    l.titulo,
                    l.vistaPreviaCon,
                    l.contenido
                FROM lecciones l
                INNER JOIN cursos c
                    ON l.curso_id = c.id
            """)

        insertObject = cursor.fetchall()
    
        cursor.close()
    return render_template("lessons/lessons.html", data=insertObject)


@app.route("/form_lesson", methods=["GET", "POST"])
def add_lesson():
    conexion = db.get_db()
    cursor = conexion.cursor(dictionary=True)

    # 🔹 Traer instructores para el select
    cursor.execute("""
    SELECT id, titulo
    FROM cursos
    """)

    cursos = cursor.fetchall()

    if request.method == "POST":

        curso_id = request.form["curso_id"]
        titulo = request.form["titulo"]
        vistaPreviaCon = request.form["vistaPreviaCon"]
        contenido = request.form["contenido"]

        try:

            cursor.execute(
                """
            INSERT INTO lecciones (curso_id,titulo,vistaPreviaCon,contenido)

            VALUES (%s,%s,%s,%s)
            """,
                (curso_id, titulo, vistaPreviaCon, contenido),
            )

            conexion.commit()

            return redirect(url_for("lessons"))

        except Exception as e:

            conexion.rollback()
            return render_template("lessons/form.html", cursos=cursos)

    return render_template("lessons/form.html", cursos=cursos)


@app.route("/edit_lesson/<int:id>", methods=["GET", "POST"])
def edit_lesson(id):

    conexion = db.get_db()
    cursor = conexion.cursor(dictionary=True)

    # Traer cursos para el select
    cursor.execute("""
        SELECT id, titulo
        FROM cursos
    """)

    cursos = cursor.fetchall()

    if request.method == "POST":

        curso_id = request.form["curso_id"]
        titulo = request.form["titulo"]
        vistaPreviaCon = request.form["vistaPreviaCon"]
        contenido = request.form["contenido"]

        try:

            cursor.execute(
                """
                UPDATE lecciones
                SET curso_id=%s,
                    titulo=%s,
                    vistaPreviaCon=%s,
                    contenido=%s
                WHERE id=%s
                """,
                (
                    curso_id,
                    titulo,
                    vistaPreviaCon,
                    contenido,
                    id
                ),
            )

            conexion.commit()

            return redirect(url_for("lessons"))

        except Exception as e:

            conexion.rollback()
            return str(e), 500

        finally:

            cursor.close()

    # Traer lección a editar
    cursor.execute(
        "SELECT * FROM lecciones WHERE id=%s",
        (id,)
    )

    lesson = cursor.fetchone()

    cursor.close()

    return render_template(
        "lessons/form.html",
        cursos=cursos,
        lesson=lesson
    )


@app.route("/deleteLEST/<int:id>", methods=["POST"])
def deleteLES(id):
    conexion = db.get_db()
    cursor = conexion.cursor()
    sql = "DELETE FROM lecciones WHERE id = %s"
    data = (id,)
    cursor.execute(sql, data)
    conexion.commit()
    return redirect(url_for("lessons"))


# REGISTRATION---------------------------------------------------------------------------------------------#


@app.route("/enrollments", methods=["GET"])
def registration():

    conexion = db.get_db()

    if conexion.is_connected():

        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                i.id,
                i.estudiante_id,
                e.nombre AS estudiante_nombre,
                i.curso_id,
                c.titulo AS curso_titulo,
                i.intereses,
                i.fecha_inscripcion

            FROM inscripciones i

            INNER JOIN estudiante e
                ON i.estudiante_id = e.id

            INNER JOIN cursos c
                ON i.curso_id = c.id
        """)

        insertObject = cursor.fetchall()

        cursor.close()

    return render_template(
        "registro/Enrollments.html",
        data=insertObject
    )

@app.route("/form_enrollments", methods=["GET", "POST"])
def add_regis():
    conexion = db.get_db()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute("SELECT id, nombre FROM estudiante")
    users = cursor.fetchall()

    # 🔹 LECCIONES
    cursor.execute("SELECT id, titulo FROM cursos")
    lecciones = cursor.fetchall()

    if request.method == "POST":

        estudiante_id = request.form["estudiante_id"]
        curso_id = request.form["curso_id"]

        error = None

        
        if error:
            return render_template(
                "registro/form.html", lecciones=lecciones, users=users, error=error
            )

        try:
            cursor.execute(
                """
                INSERT INTO inscripciones
                (estudiante_id, curso_id)
                VALUES (%s,%s)
            """,
                (estudiante_id, curso_id)
            ),
            conexion.commit()
            cursor.close()

            return redirect(url_for("registration"))

        except Exception as e:
            conexion.rollback()
            return render_template(
                "registro/form.html",
                error=str(e),
                lecciones=lecciones,
                users=users,
            )

    return render_template("registro/form.html", lecciones=lecciones, users=users)


@app.route("/edit_enrollments/<int:id>", methods=["GET", "POST"])
def edit_regis(id):
    conexion = db.get_db()
    cursor = conexion.cursor(dictionary=True)

    # 🔹 LECCIONES
    cursor.execute("SELECT id, titulo FROM cursos")
    lecciones = cursor.fetchall()

    # 🔹 USUARIOS
    cursor.execute("SELECT id, nombre FROM estudiante")
    users = cursor.fetchall()

    if request.method == "POST":

        estudiante_id = request.form["estudiante_id"]
        curso_id = request.form["curso_id"]
        
        error = None

       
        if error:
            return render_template(
                "registro/form.html",
                error=error,
                lecciones=lecciones,
                users=users,
            )

        cursor.execute(
            """UPDATE inscripciones  SET estudiante_id=%s,curso_id=%s WHERE id=%s """,
            (estudiante_id, curso_id, id),
        )

        conexion.commit()

        return redirect(url_for("registration"))

    # 🔹 traer dato
    cursor.execute("SELECT * FROM inscripciones WHERE id=%s", (id,))
    nota_lesson = cursor.fetchone()

    cursor.close()

    return render_template(
        "registro/form.html", lecciones=lecciones, users=users, nota_lesson=nota_lesson
    )


@app.route("/deleteREGIS/<int:id>", methods=["POST"])
def deleteREGIS(id):
    conexion = db.get_db()
    cursor = conexion.cursor()
    sql = "DELETE FROM inscripciones WHERE id = %s"
    data = (id,)
    cursor.execute(sql, data)
    conexion.commit()
    return redirect(url_for("registration"))


# CERTIFICATES----------------------------------------------------------------------------------------------#




# ----------------------------------------------------------------------------------------------------------#

@app.route("/regis/<int:curso_id>", methods=["POST"])
def regis(curso_id):
    conexion = db.get_db()
    # 🔥 usuario logueado
    estudiante_id = session["user_id"]

    # 🔥 fecha automática
    fecha_inscripcion = date.today()

    cursor = conexion.cursor()

    # 🔥 verificar si ya está inscrito
    cursor.execute(
        """
        SELECT * FROM inscripciones
        WHERE estudiante_id=%s
        AND curso_id=%s
        """,
        (estudiante_id, curso_id),
    )

    existe = cursor.fetchone()

    if existe:

        cursor.close()

        if "rol" in session and session["rol"] == "ESTUDIANTE":
            return redirect(url_for("estudiante.menuUser"))    
        
        if "rol" in session and session["rol"] == "PROFESOR":
            return redirect(url_for("profesor.menuInstru"))

    # 🔥 insertar inscripción automática
    cursor.execute(
        """
        INSERT INTO inscripciones
        (estudiante_id, curso_id, fecha_inscripcion)

        VALUES (%s,%s,%s)
        """,
        (estudiante_id, curso_id, fecha_inscripcion),
    )

    conexion.commit()

    cursor.close()

    if "rol" in session and session["rol"] == "ESTUDIANTE":
        return redirect(url_for("estudiante.menuUser"))    
           
    if "rol" in session and session["rol"] == "PROFESOR":
        return redirect(url_for("profesor.menuInstru"))
   


# ----------------------------------------------------------------------------------------------------------#
if __name__ == "__main__":
    app.run(debug=True)
