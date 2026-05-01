from flask import Flask, render_template, redirect, url_for,request
import database as db
from datetime import datetime, date

app = Flask(__name__, template_folder="templates")

cursor = db.conexion.cursor()



@app.route("/")
def init():
    return redirect(url_for("login"))



# USUARIOS-------------------------------------------------------------------------------------------------------#

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        contrasena = request.form["contrasena"]

        cursor = db.conexion.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM usuarios WHERE email=%s AND contrasena=%s",
            (email, contrasena),
        )

        user = cursor.fetchone()
        cursor.close()

        if user:

            # 🔥 Validar rol
            if user["rol"] == "ADMIN":
                return redirect(url_for("home"))

            elif user["rol"] == "USUARIO":
                return redirect(url_for("menuUser"))

            else:
                error = "Rol no válido"
                return render_template("VisUSERT/login.html", error=error)

        else:
            error = "Correo o contraseña incorrectos"
            return render_template("VisUSERT/login.html", error=error)

    return render_template("VisUSERT/login.html")



@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        nombre = request.form["nombre"]
        email = request.form["email"]
        contrasena = request.form["contrasena"]
        rol = request.form["rol"]
        fecha_registro = request.form["fecha_registro"]

        error = None

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
            return render_template("VisUSERT/register.html", error=error)

        try:

            cursor = db.conexion.cursor()

            cursor.execute(
                """
                INSERT INTO usuarios (nombre,email,contrasena,rol,fecha_registro)
                VALUES (%s,%s,%s,%s,%s)
                """,
                (nombre, email, contrasena, rol, fecha_registro),
            )

            db.conexion.commit()
            cursor.close()

            # 🔥 Redirige al login después de registrarse
            return redirect(url_for("login"))

        except Exception as e:
            db.conexion.rollback()
            return render_template("VisUSERT/register.html", error=str(e))

    return render_template("VisUSERT/register.html")



@app.route("/menuUser")
def menuUser():
    return render_template("VisUSERT/menu.html")


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

            cursor = db.conexion.cursor()

            cursor.execute(
                """
            INSERT INTO usuarios (nombre,email,contrasena,rol,fecha_registro)
            VALUES (%s,%s,%s,%s,%s)
            """,
                (nombre, email, contrasena, rol, fecha_registro),
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
        email = request.form["email"]
        contrasena = request.form["contrasena"]
        rol = request.form["rol"]
        fecha_registro = request.form["fecha_registro"]

        cursor.execute(
            """
        UPDATE usuarios
        SET nombre=%s,email=%s,contrasena=%s,rol=%s,fecha_registro=%s
        WHERE id=%s
        """,
            (nombre, email, contrasena, rol, fecha_registro, id),
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
    cursor.execute(
        """
    SELECT id, nombre
    FROM usuarios
    WHERE rol = 'PROFESOR'
    """
    )

    profesores = cursor.fetchall()

    if request.method == "POST":

        titulo = request.form["titulo"]
        descripcion = request.form["descripcion"]
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
            INSERT INTO cursos (titulo, descripcion, profesor_id, fecha_creacion)
            VALUES (%s,%s,%s,%s)
            """,
                (titulo, descripcion, profesor_id, fecha_creacion),
            )

            db.conexion.commit()

            return redirect(url_for("courses"))

        except Exception as e:

            db.conexion.rollback()
            return render_template("courses/form.html", error=str(e), profesores=profesores)

    return render_template("courses/form.html", profesores=profesores)


@app.route("/edit_course/<int:id>", methods=["GET", "POST"])
def edit_course(id):

    cursor = db.conexion.cursor(dictionary=True)

    # traer instructores
    cursor.execute(
        """
    SELECT id, nombre
    FROM usuarios
    WHERE rol='PROFESOR'
    """
    )
    profesores = cursor.fetchall()

    if request.method == "POST":

        titulo = request.form["titulo"]
        descripcion = request.form["descripcion"]
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
        SET titulo=%s, descripcion=%s, profesor_id=%s, fecha_creacion=%s
        WHERE id=%s
        """,
            (titulo, descripcion, profesor_id, fecha_creacion, id),
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
    cursor.execute(
        """
    SELECT id, titulo
    FROM cursos
    """
    )

    cursos = cursor.fetchall()

    if request.method == "POST":

        curso_id = request.form["curso_id"]
        titulo = request.form["titulo"]
        contenido = request.form["contenido"]
        url_recurso = request.form["url_recurso"]

        try:

            cursor.execute(
                """
            INSERT INTO lecciones (curso_id,titulo,contenido,url_recurso)
            VALUES (%s,%s,%s,%s)
            """,
                (curso_id, titulo, contenido, url_recurso),
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
    cursor.execute(
        """
    SELECT id, titulo
    FROM cursos
    """
    )

    cursos = cursor.fetchall()

    if request.method == "POST":

        curso_id = request.form["curso_id"]
        titulo = request.form["titulo"]
        contenido = request.form["contenido"]
        url_recurso = request.form["url_recurso"]

        cursor.execute(
            """
        UPDATE lecciones SET curso_id=%s,titulo=%s,contenido=%s,url_recurso=%s
        
        """,
            (curso_id, titulo, contenido, url_recurso),
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


# LESSON_NOTES-----------------------------------------------------------------------------------------------#


@app.route("/lesson_notes", methods=["GET"])
def lesson_notes():
    if db.conexion.is_connected():
        cursor = db.conexion.cursor()
        cursor.execute("SELECT * FROM nota_leccion")
        myresult = cursor.fetchall()
        insertObject = []
        columnNames = [column[0] for column in cursor.description]
        for record in myresult:
            insertObject.append(dict(zip(columnNames, record)))
        cursor.close()
    return render_template("notes/lesson_notes.html", data=insertObject)


@app.route("/form_notes", methods=["GET", "POST"])
def add_notes():

    cursor = db.conexion.cursor(dictionary=True)

    # 🔹 LECCIONES
    cursor.execute("SELECT id, titulo FROM lecciones")
    lecciones = cursor.fetchall()

    # 🔹 USUARIOS
    cursor.execute("SELECT id, nombre FROM usuarios")
    users = cursor.fetchall()

    if request.method == "POST":

        lecciones_id = request.form["lecciones_id"]
        usuarios_id = request.form["usuarios_id"]
        notas = request.form["notas"]
        estado = request.form["estado"]
        fecha_registro = request.form["fecha_registro"]

        print(lecciones_id, usuarios_id, notas, estado, fecha_registro)

        error = None

        fecha = datetime.strptime(fecha_registro, "%Y-%m-%d").date()

        if fecha > date.today():
            error = "No se permiten fechas futuras"

        if error:
            return render_template(
                "notes/form.html", error=error, lecciones=lecciones, users=users
            )

        try:
            cursor.execute(
                """
                INSERT INTO nota_leccion 
                (lecciones_id, usuarios_id, notas, estado, fecha_registro)
                VALUES (%s,%s,%s,%s,%s)
            """,
                (lecciones_id, usuarios_id, notas, estado, fecha_registro),
            )

            db.conexion.commit()
            cursor.close()

            return redirect(url_for("lesson_notes"))

        except Exception as e:
            db.conexion.rollback()
            return render_template(
                "notes/form.html", error=str(e), lecciones=lecciones, users=users
            )

    return render_template("notes/form.html", lecciones=lecciones, users=users)


@app.route("/edit_notes/<int:id>", methods=["GET", "POST"])
def edit_notes(id):

    cursor = db.conexion.cursor(dictionary=True)

    # 🔹 selects
    cursor.execute("SELECT id, titulo FROM lecciones")
    lecciones = cursor.fetchall()

    cursor.execute("SELECT id, nombre FROM usuarios")
    users = cursor.fetchall()

    if request.method == "POST":

        lecciones_id = request.form["lecciones_id"]
        usuarios_id = request.form["usuarios_id"]
        notas = request.form["notas"]
        estado = request.form["estado"]
        fecha_registro = request.form["fecha_registro"]

        error = None

        fecha = datetime.strptime(fecha_registro, "%Y-%m-%d").date()

        if fecha > date.today():
            error = "No se permiten fechas futuras"

        if error:
            return render_template(
                "notes/form.html",
                error=error,
                lecciones=lecciones,
                users=users,
            )

        cursor.execute("""UPDATE nota_leccion SET lecciones_id=%s, usuarios_id=%s, notas=%s, estado=%s, fecha_registro=%s WHERE id=%s """,
            (lecciones_id, usuarios_id, notas, estado, fecha_registro, id),
        )

        db.conexion.commit()

        return redirect(url_for("lesson_notes"))

    # 🔹 traer dato
    cursor.execute("SELECT * FROM nota_leccion WHERE id=%s", (id,))
    nota_lesson = cursor.fetchone()

    cursor.close()

    return render_template(
        "notes/form.html", lecciones=lecciones, users=users, nota_lesson=nota_lesson
    )


@app.route("/deleteLES/<string:id>", methods=["POST"])
def deleteNOT(id):
    cursor = db.conexion.cursor()
    sql = "DELETE FROM nota_leccion WHERE id = %s"
    data = (id,)
    cursor.execute(sql, data)
    db.conexion.commit()
    return redirect(url_for("lesson_notes"))


# PROGRESS------------------------------------------------------------------------------------------------#


@app.route("/course_progress", methods=["GET"])
def course_progress():
    if db.conexion.is_connected():
        cursor = db.conexion.cursor()
        cursor.execute("SELECT * FROM progreso_curso")
        myresult = cursor.fetchall()
        insertObject = []
        columnNames = [column[0] for column in cursor.description]
        for record in myresult:
            insertObject.append(dict(zip(columnNames, record)))
        cursor.close()
    return render_template("course_progress/course_progress.html", data=insertObject)


@app.route("/form_progres", methods=["GET", "POST"])
def add_prog():

    cursor = db.conexion.cursor(dictionary=True)
    
    cursor.execute("SELECT id, nombre FROM usuarios")
    users = cursor.fetchall()

    # 🔹 LECCIONES
    cursor.execute("SELECT id, titulo FROM cursos")
    lecciones = cursor.fetchall()


    if request.method == "POST":

        usuario_id = request.form["usuario_id"]
        curso_id = request.form["curso_id"]
        progreso = request.form["progreso"]
        nota_final = request.form["nota_final"]
        estado = request.form["estado"]
        fecha_actualizacion = request.form["fecha_actualizacion"]

        error = None

        fecha = datetime.strptime(fecha_actualizacion, "%Y-%m-%d").date()

        if fecha > date.today():
            error = "No se permiten fechas futuras"

        if error:
            return render_template(
                "notes/form.html",
                error=error,
                lecciones=lecciones,
                users=users,
            )

        try:
            cursor.execute(
                """
                INSERT INTO progreso_curso 
                (usuario_id, curso_id, progreso, nota_final, estado ,fecha_actualizacion)
                VALUES (%s,%s,%s,%s,%s,%s)
            """,
                (usuario_id, curso_id, progreso, nota_final, estado ,fecha_actualizacion),
            )
            db.conexion.commit()
            cursor.close()

            return redirect(url_for("course_progress"))

        except Exception as e:
            db.conexion.rollback()
            return render_template(
                "course_progress/form.html", error=str(e), lecciones=lecciones, users=users
            )

    return render_template("course_progress/form.html", lecciones=lecciones, users=users)

@app.route("/edit_progress/<int:id>", methods=["GET", "POST"])
def edit_prog(id):

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
        progreso = request.form["progreso"]
        nota_final = request.form["nota_final"]
        estado = request.form["estado"]
        fecha_actualizacion = request.form["fecha_actualizacion"]

        error = None

        fecha = datetime.strptime(fecha_actualizacion, "%Y-%m-%d").date()

        if fecha > date.today():
            error = "No se permiten fechas futuras"

        if error:
            return render_template(
                "notes/form.html",
                error=error,
                lecciones=lecciones,
                users=users,
            )

        cursor.execute("""UPDATE progreso_curso  SET usuario_id=%s,curso_id=%s, progreso =%s, nota_final=%s, estado=%s, fecha_actualizacion=%s WHERE id=%s """,
            (usuario_id, curso_id, progreso, nota_final, estado ,fecha_actualizacion,id),
        )

        db.conexion.commit()

        return redirect(url_for("course_progress"))

    # 🔹 traer dato
    cursor.execute("SELECT * FROM progreso_curso WHERE id=%s", (id,))
    nota_lesson = cursor.fetchone()

    cursor.close()

    return render_template(
        "course_progress/form.html", lecciones=lecciones, users=users, nota_lesson=nota_lesson
    )

@app.route("/deletePRO/<string:id>", methods=["POST"])
def deletePRO(id):
    cursor = db.conexion.cursor()
    sql = "DELETE FROM progreso_curso WHERE id = %s"
    data = (id,)
    cursor.execute(sql, data)
    db.conexion.commit()
    return redirect(url_for("course_progress"))


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
        fechaRevision= request.form["fechaRevision"]

        error = None

        fecha = datetime.strptime(fechaEnvio, "%Y-%m-%d").date()

        if fecha > date.today():
            error = "No se permiten fechas futuras"
            
        fecha = datetime.strptime(fechaRevision , "%Y-%m-%d").date()

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
                (usuario_id, curso_id, estado, documentoPDF ,fechaEnvio,fechaRevision),
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
        fechaRevision= request.form["fechaRevision"]

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
        
        cursor.execute("""UPDATE validacion_instructores  SET usuario_id=%s,curso_id=%s,estado=%s, documentoPDF=%s, fechaEnvio=%s,  fechaRevision=%s WHERE id=%s """,
            (usuario_id, curso_id, estado,documentoPDF ,fechaEnvio, fechaRevision,id),
        )

        db.conexion.commit()

        return redirect(url_for("instructor_validation"))

    # 🔹 traer dato
    cursor.execute("SELECT * FROM validacion_instructores WHERE id=%s", (id,))
    nota_lesson = cursor.fetchone()

    cursor.close()

    return render_template(
        "instructor/form.html", lecciones=lecciones, users=users, nota_lesson=nota_lesson
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
        fecha_inscripcion= request.form["fecha_inscripcion"]
       
        error = None

        fecha = datetime.strptime(fecha_inscripcion, "%Y-%m-%d").date()

        if fecha > date.today():
            error = "No se permiten fechas futuras"
        

        if error:
            return render_template(
                "registro/form.html", lecciones=lecciones, users=users, 
                error=error
                
            )

        try:
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

            return redirect(url_for("registration"))

        except Exception as e:
            db.conexion.rollback()
            return render_template(
                "registro/form.html",error=str(e), lecciones=lecciones, users=users, 
            )

    return render_template("registro/form.html", lecciones=lecciones, users=users )

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
        fecha_inscripcion = request.form["fecha_inscripcion"]

        error = None

        fecha = datetime.strptime( fecha_inscripcion, "%Y-%m-%d").date()

        if fecha > date.today():
            error = "No se permiten fechas futuras"
            
        if error:
            return render_template(
                "registro/form.html",
                error=error,
                lecciones=lecciones,
                users=users,
            )
        
        cursor.execute("""UPDATE inscripciones  SET usuario_id=%s,curso_id=%s, fecha_inscripcion=%s WHERE id=%s """,
            (usuario_id, curso_id, fecha_inscripcion,id),
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
        codigo_certificado  = request.form["codigo_certificado "]
        fecha_emision = request.form["fecha_emision"]
        urlCertificado = request.form["urlCertificado"]
        


        error = None

        fecha = datetime.strptime(fecha_emision,"%Y-%m-%d").date()

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
                (usuario_id, curso_id, codigo_certificado , fecha_emision ,urlCertificado ),
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
        codigo_certificado  = request.form["codigo_certificado "]
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
        
        cursor.execute("""UPDATE certificados  SET usuario_id=%s,curso_id=%s,codigo_certificado=%s, fecha_emision=%s, urlCertificado=%s WHERE id=%s """,
            (usuario_id, curso_id, codigo_certificado ,fecha_emision ,urlCertificado,id),
        )

        db.conexion.commit()

        return redirect(url_for("certificates"))

    # 🔹 traer dato
    cursor.execute("SELECT * FROM certificados WHERE id=%s", (id,))
    nota_lesson = cursor.fetchone()

    cursor.close()

    return render_template(
        "certificates/form.html", lecciones=lecciones, users=users, nota_lesson=nota_lesson
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

if __name__ == "__main__":
    app.run(debug=True)
