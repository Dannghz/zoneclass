import re
from flask import Flask, Response, render_template, redirect, url_for, request, session
import database as db
from datetime import datetime, date

app = Flask(__name__, template_folder="templates")
app.secret_key = "clave_super_secreta"
cursor = db.conexion.cursor()

# -------------------------------------------------------------------------------------------------------#

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

#-------------------------------------------------------------------------------------------------------#

from rutas_usuarios import usuarios_bp

from rutas_profesor import profesor_bp

# 2. REGISTRAS LOS ARCHIVOS EN LA APP
app.register_blueprint(usuarios_bp)

app.register_blueprint(profesor_bp)

#-------------------------------------------------------------------------------------------------------#

@app.route("/")
def logout():

    session.clear()

    return redirect(url_for("login"))


# login-------------------------------------------------------------------------------------------------------#
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        contrasena = request.form["contrasena"]

        cursor = db.conexion.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT * FROM usuarios
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

            elif user["rol"] == "USUARIO":

                return redirect(url_for("usuarios.menuUser"))

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
    if db.conexion.is_connected():
        cursor = db.conexion.cursor()
        cursor.execute("SELECT * FROM usuarios")
        myresult = cursor.fetchall()
        insertObject = []
        columnNames = [column[0] for column in cursor.description]
        for record in myresult:
            insertObject.append(dict(zip(columnNames, record)))
        cursor.close()
    return render_template("users/users.html", data=insertObject)


@app.route("/form_user", methods=["GET", "POST"])
def add_user():

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

        if edad > 120 or edad < 0:
            error = "Edad inválida"

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

            cursor = db.conexion.cursor()

            cursor.execute(
                """
            INSERT INTO usuarios (nombre,edad,email,contrasena,rol,fecha_registro)
            VALUES (%s,%s,%s,%s,%s,%s)
            """,
                (nombre,edad, email, contrasena, rol, fecha_registro),
            )

            db.conexion.commit()
            cursor.close()

            return redirect(url_for("users"))

        except Exception as e:

            db.conexion.rollback()
            return render_template("users/form.html", error=str(e))

    pass
    return render_template("users/form.html", user=None)


@app.route("/edit_user/<int:id>", methods=["GET", "POST"])
def edit_user(id):

    cursor = db.conexion.cursor(dictionary=True)

    if request.method == "POST":

        nombre = request.form["nombre"]
        edad = request.form["edad"]
        email = request.form["email"]
        contrasena = request.form["contrasena"]
        rol = request.form["rol"]
        fecha_registro = request.form["fecha_registro"]

        cursor.execute(
            """
        UPDATE usuarios
        SET nombre=%s,edad=%s,email=%s,contrasena=%s,rol=%s,fecha_registro=%s
        WHERE id=%s
        """,
            (nombre, edad, email, contrasena, rol, fecha_registro, id),
        )

        db.conexion.commit()

        return redirect(url_for("users"))

    # 🔹 ESTE ES EL PASO CLAVE
    cursor.execute("SELECT * FROM usuarios WHERE id=%s", (id,))
    user = cursor.fetchone()

    cursor.close()

    return render_template("users/form.html", user=user)


@app.route("/deleteUS/<int:id>", methods=["POST"])
def deleteUS(id):
    cursor = db.conexion.cursor()
    sql = "DELETE FROM usuarios WHERE id = %s"
    data = (id,)
    cursor.execute(sql, data)
    db.conexion.commit()
    return redirect(url_for("users"))


# COURSES--------------------------------------------------------------------------------------------------#


@app.route("/courses", methods=["GET"])
def courses():
    if db.conexion.is_connected():
        cursor = db.conexion.cursor()
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

    cursor = db.conexion.cursor(dictionary=True)

    # 🔹 Traer instructores para el select
    cursor.execute("""
    SELECT id, nombre
    FROM usuarios
    WHERE rol = 'PROFESOR'
    """)

    profesores = cursor.fetchall()

    if request.method == "POST":

        titulo = request.form["titulo"]
        descripcion = request.form["descripcion"]
        contenido = request.form["contenido"]
        profesor_id = request.form["profesor_id"]
        fecha_creacion = request.form["fecha_creacion"]

        error = None

        fecha = datetime.strptime(fecha_creacion, "%Y-%m-%d").date()

        if fecha > date.today():
            error = "No se permiten fechas futuras"

        if error:
            return render_template("courses/form.html", error=error, profesores=None)

        try:

            cursor.execute(
                """
            INSERT INTO cursos (titulo, descripcion, contenido, profesor_id, fecha_creacion)
            VALUES (%s,%s,%s,%s,%s)
            """,
                (titulo, descripcion, contenido, profesor_id, fecha_creacion),
            )

            db.conexion.commit()

            return redirect(url_for("courses"))

        except Exception as e:

            db.conexion.rollback()
            return render_template(
                "courses/form.html", error=str(e), profesores=profesores
            )

    return render_template("courses/form.html", profesores=profesores)


@app.route("/edit_course/<int:id>", methods=["GET", "POST"])
def edit_course(id):

    cursor = db.conexion.cursor(dictionary=True)

    # traer instructores
    cursor.execute("""
    SELECT id, nombre
    FROM usuarios
    WHERE rol='PROFESOR'
    """)
    profesores = cursor.fetchall()

    if request.method == "POST":

        titulo = request.form["titulo"]
        descripcion = request.form["descripcion"]
        contenido = request.form["contenido"]
        profesor_id = request.form["profesor_id"]
        fecha_creacion = request.form["fecha_creacion"]

        error = None

        fecha = datetime.strptime(fecha_creacion, "%Y-%m-%d").date()

        if fecha > date.today():
            error = "No se permiten fechas futuras"

        if error:
            return render_template(
                "courses/form.html", error=error, profesores=profesores
            )

        cursor.execute(
            """
        UPDATE cursos
        SET titulo=%s, descripcion=%s, contenido=%s, profesor_id=%s, fecha_creacion=%s
        WHERE id=%s
        """,
            (titulo, descripcion, contenido, profesor_id, fecha_creacion, id),
        )

        db.conexion.commit()

        return redirect(url_for("courses"))

    # traer curso a editar
    cursor.execute("SELECT * FROM cursos WHERE id=%s", (id,))
    curso = cursor.fetchone()

    cursor.close()

    return render_template("courses/form.html", curso=curso, profesores=profesores)


@app.route("/deleteCUR/<string:id>", methods=["POST"])
def deleteCUR(id):
    cursor = db.conexion.cursor()
    sql = "DELETE FROM cursos WHERE id = %s"
    data = (id,)
    cursor.execute(sql, data)
    db.conexion.commit()
    return redirect(url_for("courses"))


# LESSONS--------------------------------------------------------------------------------------------------#


@app.route("/lessons", methods=["GET"])
def lessons():
    if db.conexion.is_connected():
        cursor = db.conexion.cursor()
        cursor.execute("SELECT * FROM lecciones")
        myresult = cursor.fetchall()
        insertObject = []
        columnNames = [column[0] for column in cursor.description]
        for record in myresult:
            insertObject.append(dict(zip(columnNames, record)))
        cursor.close()
    return render_template("lessons/lessons.html", data=insertObject)


@app.route("/form_lesson", methods=["GET", "POST"])
def add_lesson():

    cursor = db.conexion.cursor(dictionary=True)

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
        url_recurso = request.form["url_recurso"]

        try:

            cursor.execute(
                """
            INSERT INTO lecciones (curso_id,titulo,vistaPreviaCon,contenido,url_recurso)
            VALUES (%s,%s,%s,%s,%s)
            """,
                (curso_id, titulo, vistaPreviaCon, contenido, url_recurso),
            )

            db.conexion.commit()

            return redirect(url_for("lessons"))

        except Exception as e:

            db.conexion.rollback()
            return render_template("lessons/form.html", cursos=cursos)

    return render_template("lessons/form.html", cursos=cursos)


@app.route("/edit_lesson/<int:id>", methods=["GET", "POST"])
def edit_lesson(id):

    cursor = db.conexion.cursor(dictionary=True)

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
        url_recurso = request.form["url_recurso"]

        cursor.execute(
            """
        UPDATE lecciones SET curso_id=%s,titulo=%s,vistaPreviaCon=%s,contenido=%s,url_recurso=%s
        
        """,
            (curso_id, titulo, vistaPreviaCon, contenido, url_recurso),
        )

        db.conexion.commit()

        return redirect(url_for("lessons"))

    cursor.execute("SELECT * FROM lecciones WHERE id=%s", (id,))
    lesson = cursor.fetchone()

    cursor.close()

    return render_template("lessons/form.html", cursos=cursos, lesson=lesson)


@app.route("/deleteLEST/<string:id>", methods=["POST"])
def deleteLES(id):
    cursor = db.conexion.cursor()
    sql = "DELETE FROM lecciones WHERE id = %s"
    data = (id,)
    cursor.execute(sql, data)
    db.conexion.commit()
    return redirect(url_for("lessons"))





# VALIDATION-----------------------------------------------------------------------------------------------#


@app.route("/instructor_validation", methods=["GET"])
def instructor_validation():
    if db.conexion.is_connected():
        cursor = db.conexion.cursor()
        cursor.execute("SELECT * FROM validacion_instructores")
        myresult = cursor.fetchall()
        insertObject = []
        columnNames = [column[0] for column in cursor.description]
        for record in myresult:
            insertObject.append(dict(zip(columnNames, record)))
        cursor.close()
    return render_template("instructor/instructor_validation.html", data=insertObject)


@app.route("/form_valid", methods=["GET", "POST"])
def add_valid():

    cursor = db.conexion.cursor(dictionary=True)

    cursor.execute("SELECT id, nombre FROM usuarios")
    users = cursor.fetchall()

    # 🔹 LECCIONES
    cursor.execute("SELECT id, titulo FROM cursos")
    lecciones = cursor.fetchall()

    if request.method == "POST":

        usuario_id = request.form["usuario_id"]
        curso_id = request.form["curso_id"]
        estado = request.form["estado"]
        documentoPDF = request.form["documentoPDF"]
        fechaEnvio = request.form["fechaEnvio"]
        fechaRevision = request.form["fechaRevision"]

        error = None

        fecha = datetime.strptime(fechaEnvio, "%Y-%m-%d").date()

        if fecha > date.today():
            error = "No se permiten fechas futuras"

        fecha = datetime.strptime(fechaRevision, "%Y-%m-%d").date()

        if fecha < date.today():
            error = "solo se permite fechas futuras"

        if error:
            return render_template(
                "instructor/form.html",
                error=error,
                lecciones=lecciones,
                users=users,
            )

        try:
            cursor.execute(
                """
                INSERT INTO validacion_instructores 
                (usuario_id, curso_id, estado,documentoPDF ,fechaEnvio,fechaRevision)
                VALUES (%s,%s,%s,%s,%s,%s)
            """,
                (usuario_id, curso_id, estado, documentoPDF, fechaEnvio, fechaRevision),
            )
            db.conexion.commit()
            cursor.close()

            return redirect(url_for("instructor_validation"))

        except Exception as e:
            db.conexion.rollback()
            return render_template(
                "instructor/form.html", error=str(e), lecciones=lecciones, users=users
            )

    return render_template("instructor/form.html", lecciones=lecciones, users=users)


@app.route("/edit_validation/<int:id>", methods=["GET", "POST"])
def edit_valid(id):

    cursor = db.conexion.cursor(dictionary=True)

    # 🔹 LECCIONES
    cursor.execute("SELECT id, titulo FROM cursos")
    lecciones = cursor.fetchall()

    # 🔹 USUARIOS
    cursor.execute("SELECT id, nombre FROM usuarios")
    users = cursor.fetchall()

    if request.method == "POST":

        usuario_id = request.form["usuario_id"]
        curso_id = request.form["curso_id"]
        estado = request.form["estado"]
        documentoPDF = request.form["documentoPDF"]
        fechaEnvio = request.form["fechaEnvio"]
        fechaRevision = request.form["fechaRevision"]

        error = None

        fecha = datetime.strptime(fechaEnvio, "%Y-%m-%d").date()

        if fecha > date.today():
            error = "No se permiten fechas futuras"

        fecha = datetime.strptime(fechaRevision, "%Y-%m-%d").date()

        if fecha < date.today():
            error = "solo se permite fechas futuras"

        if error:
            return render_template(
                "instructor/form.html",
                error=error,
                lecciones=lecciones,
                users=users,
            )

        cursor.execute(
            """UPDATE validacion_instructores  SET usuario_id=%s,curso_id=%s,estado=%s, documentoPDF=%s, fechaEnvio=%s,  fechaRevision=%s WHERE id=%s """,
            (usuario_id, curso_id, estado, documentoPDF, fechaEnvio, fechaRevision, id),
        )

        db.conexion.commit()

        return redirect(url_for("instructor_validation"))

    # 🔹 traer dato
    cursor.execute("SELECT * FROM validacion_instructores WHERE id=%s", (id,))
    nota_lesson = cursor.fetchone()

    cursor.close()

    return render_template(
        "instructor/form.html",
        lecciones=lecciones,
        users=users,
        nota_lesson=nota_lesson,
    )


@app.route("/deleteVALID/<string:id>", methods=["POST"])
def deleteVALID(id):
    cursor = db.conexion.cursor()
    sql = "DELETE FROM alidacion_instructores WHERE id = %s"
    data = (id,)
    cursor.execute(sql, data)
    db.conexion.commit()
    return redirect(url_for("instructor_validation"))


# REGISTRATION---------------------------------------------------------------------------------------------#


@app.route("/enrollments", methods=["GET"])
def registration():
    if db.conexion.is_connected():
        cursor = db.conexion.cursor()
        cursor.execute("SELECT * FROM inscripciones")
        myresult = cursor.fetchall()
        insertObject = []
        columnNames = [column[0] for column in cursor.description]
        for record in myresult:
            insertObject.append(dict(zip(columnNames, record)))
        cursor.close()
    return render_template("registro/Enrollments.html", data=insertObject)


@app.route("/form_enrollments", methods=["GET", "POST"])
def add_regis():

    cursor = db.conexion.cursor(dictionary=True)

    cursor.execute("SELECT id, nombre FROM usuarios")
    users = cursor.fetchall()

    # 🔹 LECCIONES
    cursor.execute("SELECT id, titulo FROM cursos")
    lecciones = cursor.fetchall()

    if request.method == "POST":

        usuario_id = request.form["usuario_id"]
        curso_id = request.form["curso_id"]
        intereses = request.form["intereses"]
        fecha_inscripcion = request.form["fecha_inscripcion"]

        error = None

        fecha = datetime.strptime(fecha_inscripcion, "%Y-%m-%d").date()

        if fecha > date.today():
            error = "No se permiten fechas futuras"

        if error:
            return render_template(
                "registro/form.html", lecciones=lecciones, users=users, error=error
            )

        try:
            cursor.execute(
                """
                INSERT INTO inscripciones
                (usuario_id, curso_id, intereses, fecha_inscripcion)
                VALUES (%s,%s,%s,%s)
            """,
                (usuario_id, curso_id, intereses, fecha_inscripcion),
            )
            db.conexion.commit()
            cursor.close()

            return redirect(url_for("registration"))

        except Exception as e:
            db.conexion.rollback()
            return render_template(
                "registro/form.html",
                error=str(e),
                lecciones=lecciones,
                users=users,
            )

    return render_template("registro/form.html", lecciones=lecciones, users=users)


@app.route("/edit_enrollments/<int:id>", methods=["GET", "POST"])
def edit_regis(id):

    cursor = db.conexion.cursor(dictionary=True)

    # 🔹 LECCIONES
    cursor.execute("SELECT id, titulo FROM cursos")
    lecciones = cursor.fetchall()

    # 🔹 USUARIOS
    cursor.execute("SELECT id, nombre FROM usuarios")
    users = cursor.fetchall()

    if request.method == "POST":

        usuario_id = request.form["usuario_id"]
        curso_id = request.form["curso_id"]
        intereses = request.form["intereses"]
        fecha_inscripcion = request.form["fecha_inscripcion"]

        error = None

        fecha = datetime.strptime(fecha_inscripcion, "%Y-%m-%d").date()

        if fecha > date.today():
            error = "No se permiten fechas futuras"

        if error:
            return render_template(
                "registro/form.html",
                error=error,
                lecciones=lecciones,
                users=users,
            )

        cursor.execute(
            """UPDATE inscripciones  SET usuario_id=%s,curso_id=%s, intereses=%s, fecha_inscripcion=%s WHERE id=%s """,
            (usuario_id, curso_id, intereses, fecha_inscripcion, id),
        )

        db.conexion.commit()

        return redirect(url_for("registration"))

    # 🔹 traer dato
    cursor.execute("SELECT * FROM inscripciones WHERE id=%s", (id,))
    nota_lesson = cursor.fetchone()

    cursor.close()

    return render_template(
        "registro/form.html", lecciones=lecciones, users=users, nota_lesson=nota_lesson
    )


@app.route("/deleteREGIS/<string:id>", methods=["POST"])
def deleteREGIS(id):
    cursor = db.conexion.cursor()
    sql = "DELETE FROM inscripciones WHERE id = %s"
    data = (id,)
    cursor.execute(sql, data)
    db.conexion.commit()
    return redirect(url_for("registration"))


# CERTIFICATES----------------------------------------------------------------------------------------------#


@app.route("/certificates", methods=["GET"])
def certificates():
    if db.conexion.is_connected():
        cursor = db.conexion.cursor()
        cursor.execute("SELECT * FROM certificados")
        myresult = cursor.fetchall()
        insertObject = []
        columnNames = [column[0] for column in cursor.description]
        for record in myresult:
            insertObject.append(dict(zip(columnNames, record)))
        cursor.close()
    return render_template("certificates/certificates.html", data=insertObject)


@app.route("/form_cert", methods=["GET", "POST"])
def add_cert():

    cursor = db.conexion.cursor(dictionary=True)

    cursor.execute("SELECT id, nombre FROM usuarios")
    users = cursor.fetchall()

    # 🔹 LECCIONES
    cursor.execute("SELECT id, titulo FROM cursos")
    lecciones = cursor.fetchall()

    if request.method == "POST":

        usuario_id = request.form["usuario_id"]
        curso_id = request.form["curso_id"]
        codigo_certificado = request.form["codigo_certificado "]
        fecha_emision = request.form["fecha_emision"]
        urlCertificado = request.form["urlCertificado"]

        error = None

        fecha = datetime.strptime(fecha_emision, "%Y-%m-%d").date()

        if fecha > date.today():
            error = "No se permiten fechas futuras"

        if error:
            return render_template(
                "certificates/form.html",
                error=error,
                lecciones=lecciones,
                users=users,
            )

        try:
            cursor.execute(
                """
                INSERT INTO certificados 
                (usuario_id, curso_id, codigo_certificado ,fecha_emision ,urlCertificado )
                VALUES (%s,%s,%s,%s,%s)
            """,
                (
                    usuario_id,
                    curso_id,
                    codigo_certificado,
                    fecha_emision,
                    urlCertificado,
                ),
            )
            db.conexion.commit()
            cursor.close()

            return redirect(url_for("certificates"))

        except Exception as e:
            db.conexion.rollback()
            return render_template(
                "certificates/form.html", error=str(e), lecciones=lecciones, users=users
            )

    return render_template("certificates/form.html", lecciones=lecciones, users=users)


@app.route("/edit_cert/<int:id>", methods=["GET", "POST"])
def edit_cert(id):

    cursor = db.conexion.cursor(dictionary=True)

    # 🔹 LECCIONES
    cursor.execute("SELECT id, titulo FROM cursos")
    lecciones = cursor.fetchall()

    # 🔹 USUARIOS
    cursor.execute("SELECT id, nombre FROM usuarios")
    users = cursor.fetchall()

    if request.method == "POST":

        usuario_id = request.form["usuario_id"]
        curso_id = request.form["curso_id"]
        fecha_emision = request.form["fecha_emision"]
        codigo_certificado = request.form["codigo_certificado "]
        urlCertificado = request.form["urlCertificado"]

        error = None

        fecha = datetime.strptime(fecha_emision, "%Y-%m-%d").date()

        if fecha > date.today():
            error = "No se permiten fechas futuras"

        if error:
            return render_template(
                "certificates/form.html",
                error=error,
                lecciones=lecciones,
                users=users,
            )

        cursor.execute(
            """UPDATE certificados  SET usuario_id=%s,curso_id=%s,codigo_certificado=%s, fecha_emision=%s, urlCertificado=%s WHERE id=%s """,
            (
                usuario_id,
                curso_id,
                codigo_certificado,
                fecha_emision,
                urlCertificado,
                id,
            ),
        )

        db.conexion.commit()

        return redirect(url_for("certificates"))

    # 🔹 traer dato
    cursor.execute("SELECT * FROM certificados WHERE id=%s", (id,))
    nota_lesson = cursor.fetchone()

    cursor.close()

    return render_template(
        "certificates/form.html",
        lecciones=lecciones,
        users=users,
        nota_lesson=nota_lesson,
    )


@app.route("/deleteCERT/<string:id>", methods=["POST"])
def deleteCERT(id):
    cursor = db.conexion.cursor()
    sql = "DELETE FROM certificados WHERE id = %s"
    data = (id,)
    cursor.execute(sql, data)
    db.conexion.commit()
    return redirect(url_for("certificates"))



# ----------------------------------------------------------------------------------------------------------#

@app.route("/regis/<int:curso_id>", methods=["POST"])
def regis(curso_id):

    # 🔥 usuario logueado
    usuario_id = session["user_id"]

    # 🔥 fecha automática
    fecha_inscripcion = date.today()

    cursor = db.conexion.cursor()

    # 🔥 verificar si ya está inscrito
    cursor.execute(
        """
        SELECT * FROM inscripciones
        WHERE usuario_id=%s
        AND curso_id=%s
        """,
        (usuario_id, curso_id),
    )

    existe = cursor.fetchone()

    if existe:

        cursor.close()

        if "rol" in session and session["rol"] == "USUARIO":
            return redirect(url_for("usuarios.menuUser"))    
        
        if "rol" in session and session["rol"] == "PROFESOR":
            return redirect(url_for("profesor.menuInstru"))

    # 🔥 insertar inscripción automática
    cursor.execute(
        """
        INSERT INTO inscripciones
        (usuario_id, curso_id, fecha_inscripcion)

        VALUES (%s,%s,%s)
        """,
        (usuario_id, curso_id, fecha_inscripcion),
    )

    db.conexion.commit()

    cursor.close()

    if "rol" in session and session["rol"] == "USUARIO":
        return redirect(url_for("usuarios.menuUser"))    
           
    if "rol" in session and session["rol"] == "PROFESOR":
        return redirect(url_for("profesor.menuInstru"))
   


# ----------------------------------------------------------------------------------------------------------#
if __name__ == "__main__":
    app.run(debug=True)
