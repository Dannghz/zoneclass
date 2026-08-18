import re
from flask import Flask, Response, render_template, redirect, url_for, request, session
import database as db
from datetime import datetime, date

app = Flask(__name__, template_folder="templates")
app.secret_key = "clave_super_secreta"
cursor = db.conexion.cursor()

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/")
def logout():
 
    session.clear()

    return redirect(url_for("login"))

@app.route("/foto/<int:id>")
def mostrar_foto(id):

    cursor = db.conexion.cursor(dictionary=True)

    cursor.execute(
        "SELECT foto FROM usuarios WHERE id = %s",
        (id,)
    )

    usuario = cursor.fetchone()

    cursor.close()

    if usuario and usuario["foto"]:
        return Response(usuario["foto"], mimetype="image/jpeg")

    return "", 404
# login-------------------------------------------------------------------------------------------------------#



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

                return redirect(url_for("menuUser"))

            elif user["rol"] == "PROFESOR":
            
                return redirect(url_for("menuInstru"))
        else:

            error = "Correo o contraseña incorrectos"

            return render_template("VisUSERT/login.html", error=error)

    return render_template("VisUSERT/login.html")

# Registro-------------------------------------------------------------------------------------------------------#

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        nombre = request.form["nombre"]
        edad = request.form["edad"]
        email = request.form["email"]
        contrasena = request.form["contrasena"]
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
                INSERT INTO usuarios (nombre,edad,email,contrasena,fecha_registro)
                VALUES (%s,%s,%s,%s,%s)
                """,
                (nombre, edad, email, contrasena,  fecha_registro),
            )

            db.conexion.commit()
            cursor.close()

            # 🔥 Redirige al login después de registrarse
            return redirect(url_for("login"))

        except Exception as e:
            db.conexion.rollback()
            return render_template("VisUSERT/register.html", error=str(e))

    return render_template("VisUSERT/register.html")

# Menu Usuarios-------------------------------------------------------------------------------------------------------#

@app.route("/menuUser")
def menuUser():

    if "user_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["user_id"]

    cursor = db.conexion.cursor(dictionary=True)

    # 🔥 TODOS LOS CURSOS


    # 🔥 CURSOS INSCRITOS
    cursor.execute(
        """
        SELECT
    cursos.*,
    COUNT(DISTINCT lecciones.id) AS total_lecciones,
    COUNT(DISTINCT inscripciones.usuario_id) AS total_estudiantes
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
    
    return render_template("VisUSERT/menu.html", cursos=cursos)

# Perfil USERS-------------------------------------------------------------------------------------------------------#


@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["user_id"]

    cursor = db.conexion.cursor(dictionary=True)

    # Datos del usuario
    cursor.execute("""
        SELECT
            id,
            foto,
            nombre,
            edad,
            email
        FROM usuarios
        WHERE id = %s
    """, (usuario_id,))

    usuario = cursor.fetchone()

    # Cursos inscritos
    cursor.execute("""
        SELECT
            cursos.*,
            COUNT(DISTINCT lecciones.id) AS total_lecciones
        FROM cursos
        INNER JOIN inscripciones
            ON cursos.id = inscripciones.curso_id
        LEFT JOIN lecciones
            ON cursos.id = lecciones.curso_id
        WHERE inscripciones.usuario_id = %s
        GROUP BY cursos.id
    """, (usuario_id,))

    cursos = cursor.fetchall()

    cursor.execute("""
         select
            inscripciones.intereses
         FROM inscripciones
         WHERE usuario_id = %s
        """, (usuario_id,))
    
    interes = cursor.fetchone()

    cursor.close()

    return render_template(
        "VisUSERT/perfil.html",
        usuario=usuario,
        cursos=cursos,
        interes=interes
    )


@app.route("/editprofile/<int:id>", methods=["GET", "POST"])
def editprofile(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    # Seguridad: el usuario solamente puede editar su propio perfil
    if session["user_id"] != id:
        return redirect(url_for("profile"))

    cursor = db.conexion.cursor(dictionary=True)

    errores = []

    if request.method == "POST":

        # Obtener datos y quitar espacios innecesarios
        nombre = request.form.get("nombre", "").strip()
        edad = request.form.get("edad", "").strip()
        email = request.form.get("email", "").strip().lower()
        intereses = request.form.get("intereses", "").strip()

        # =========================
        # VALIDACIÓN NOMBRE
        # =========================

        if not nombre:
            errores.append("El nombre es obligatorio.")

        elif len(nombre) < 2:
            errores.append("El nombre debe tener al menos 2 caracteres.")

        elif len(nombre) > 100:
            errores.append("El nombre no puede superar los 100 caracteres.")

        elif not re.match(r"^[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s]+$", nombre):
            errores.append("El nombre solamente puede contener letras y espacios.")

        # =========================
        # VALIDACIÓN EDAD
        # =========================

        edad_numero = None

        if not edad:
            errores.append("La edad es obligatoria.")

        else:
            try:
                edad_numero = int(edad)

                if edad_numero < 13 or edad_numero > 100:
                    errores.append("La edad debe estar entre 13 y 100 años.")

            except ValueError:
                errores.append("La edad debe ser un número entero.")

        # =========================
        # VALIDACIÓN EMAIL
        # =========================

        if not email:
            errores.append("El correo electrónico es obligatorio.")

        elif len(email) > 150:
            errores.append("El correo electrónico es demasiado largo.")

        elif not re.match(
            r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
            email
        ):
            errores.append("Ingresa un correo electrónico válido.")

        else:
            # Verificar que el correo no pertenezca a otro usuario
            cursor.execute("""
                SELECT id
                FROM usuarios
                WHERE email = %s
                AND id != %s
            """, (email, id))

            email_existente = cursor.fetchone()

            if email_existente:
                errores.append(
                    "Ese correo electrónico ya está registrado por otro usuario."
                )

        # =========================
        # VALIDACIÓN INTERESES
        # =========================

        if not intereses:
            errores.append("Debes indicar tus intereses.")

        elif len(intereses) < 3:
            errores.append("Los intereses deben tener al menos 3 caracteres.")

        elif len(intereses) > 500:
            errores.append("Los intereses no pueden superar los 500 caracteres.")

        # =========================
        # VALIDACIÓN FOTO
        # =========================

        foto = request.files.get("foto")

        foto_blob = None

        if foto and foto.filename != "":

            extensiones_permitidas = {
                "jpg",
                "jpeg",
                "png",
                "webp"
            }

            nombre_archivo = foto.filename.lower()

            if "." not in nombre_archivo:
                errores.append("La foto no tiene una extensión válida.")

            else:
                extension = nombre_archivo.rsplit(".", 1)[1]

                if extension not in extensiones_permitidas:
                    errores.append(
                        "La foto debe ser JPG, JPEG, PNG o WEBP."
                    )

            # Validar tamaño máximo: 5 MB
            foto.seek(0, 2)
            tamaño = foto.tell()
            foto.seek(0)

            if tamaño > 5 * 1024 * 1024:
                errores.append("La foto no puede superar los 5 MB.")

            if not errores:
                foto_blob = foto.read()

        # =========================
        # SI HAY ERRORES
        # =========================

        if errores:

            # Volver a obtener los datos actuales
            cursor.execute("""
                SELECT
                    id,
                    foto,
                    nombre,
                    edad,
                    email
                FROM usuarios
                WHERE id = %s
            """, (id,))

            user = cursor.fetchone()

            # Obtener intereses actuales
            cursor.execute("""
                SELECT intereses
                FROM inscripciones
                WHERE usuario_id = %s
                LIMIT 1
            """, (id,))

            inscripcion = cursor.fetchone()

            cursor.close()

            # Mantener lo que el usuario escribió en el formulario
            user["nombre"] = nombre
            user["edad"] = edad
            user["email"] = email

            interes_actual = intereses

            return render_template(
                "VisUSERT/editperfil.html",
                user=user,
                interes=interes_actual,
                errores=errores
            )

        # =========================
        # ACTUALIZAR USUARIO
        # =========================

        if foto_blob is not None:

            cursor.execute("""
                UPDATE usuarios
                SET nombre = %s,
                    edad = %s,
                    email = %s,
                    foto = %s
                WHERE id = %s
            """, (
                nombre,
                edad_numero,
                email,
                foto_blob,
                id
            ))

        else:

            cursor.execute("""
                UPDATE usuarios
                SET nombre = %s,
                    edad = %s,
                    email = %s
                WHERE id = %s
            """, (
                nombre,
                edad_numero,
                email,
                id
            ))

        # =========================
        # ACTUALIZAR INTERESES
        # =========================

        cursor.execute("""
            UPDATE inscripciones
            SET intereses = %s
            WHERE usuario_id = %s
        """, (
            intereses,
            id
        ))

        db.conexion.commit()

        cursor.close()

        return redirect(url_for("profile"))

    # =========================
    # GET
    # =========================

    cursor.execute("""
        SELECT
            id,
            foto,
            nombre,
            edad,
            email
        FROM usuarios
        WHERE id = %s
    """, (id,))

    user = cursor.fetchone()

    if not user:
        cursor.close()
        return redirect(url_for("profile"))

    # Obtener intereses
    cursor.execute("""
        SELECT intereses
        FROM inscripciones
        WHERE usuario_id = %s
        LIMIT 1
    """, (id,))

    inscripcion = cursor.fetchone()

    interes = ""

    if inscripcion:
        interes = inscripcion.get("intereses") or ""

    cursor.close()

    return render_template(
        "VisUSERT/editperfil.html",
        user=user,
        interes=interes,
        errores=[]
    )

#Miscursos-------------------------------------------------------------------------------------------------------#

@app.route("/miscursos")
def miscursos():

    if "user_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["user_id"]

    cursor = db.conexion.cursor(dictionary=True)

    cursor.execute("""
            SELECT
                cursos.*,
                COUNT(DISTINCT lecciones.id) AS total_lecciones
            FROM cursos
            INNER JOIN inscripciones
                ON cursos.id = inscripciones.curso_id
            LEFT JOIN lecciones
                ON cursos.id = lecciones.curso_id
            WHERE inscripciones.usuario_id = %s
            GROUP BY cursos.id
        """, (usuario_id,))

    cursos = cursor.fetchall()

    cursor.close()

    return render_template(
        "VisUSERT/miscursos.html",
        cursos=cursos
    )

#VistaCursos ----------------------------------------------------------------------------------------------------------#
@app.route("/view_course/<int:curso_id>")
def view_course(curso_id):

    cursor = db.conexion.cursor(dictionary=True)

    # =====================================
    # TRAER CURSO + NOMBRE DEL PROFESOR
    # =====================================
    cursor.execute(
        """
        SELECT 
            cursos.*,
            usuarios.nombre AS profesor_nombre

        FROM cursos

        INNER JOIN usuarios
        ON usuarios.id = cursos.profesor_id

        WHERE cursos.id=%s
        """,
        (curso_id,),
    )

    curso = cursor.fetchone()

    # =====================================
    # TRAER LECCIONES DEL CURSO
    # =====================================
    cursor.execute(
        """
        SELECT *
        FROM lecciones
        WHERE curso_id=%s
        """,
        (curso_id,),
    )

    lecciones = cursor.fetchall()

    cursor.close()

    return render_template(
        "VisUSERT/view_course.html",
        curso=curso,
        lecciones=lecciones,
    )

#Vistalecciones ----------------------------------------------------------------------------------------------------------#

@app.route("/view_lesson/<int:id>")
def view_lesson(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = db.conexion.cursor(dictionary=True)

    # Obtener la información de la lección
    cursor.execute("""
        SELECT *
        FROM lecciones
        WHERE id = %s
    """, (id,))

    leccion = cursor.fetchone()

    if not leccion:
        cursor.close()
        return "Lección no encontrada", 404

    # Obtener los archivos PDF de esa lección
    cursor.execute("""
        SELECT *
        FROM archivospdf
        WHERE leccion_id = %s
        ORDER BY id
    """, (id,))

    archivos_pdf = cursor.fetchall()

    cursor.close()

    return render_template(
        "VisUSERT/leccion.html",
        leccion=leccion,
        archivos_pdf=archivos_pdf
    )

# Menu Instructores-------------------------------------------------------------------------------------------------------#

@app.route("/menuInstru")
def menuInstru():

    if "user_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["user_id"]

    cursor = db.conexion.cursor(dictionary=True)

    # 🔥 TODOS LOS CURSOS
    cursor.execute("""
    SELECT
    cursos.*,
    COUNT(DISTINCT lecciones.id) AS total_lecciones,
    COUNT(DISTINCT inscripciones.usuario_id) AS total_estudiantes
    FROM cursos
    LEFT JOIN lecciones
        ON cursos.id = lecciones.curso_id
    LEFT JOIN inscripciones
        ON cursos.id = inscripciones.curso_id
    WHERE cursos.profesor_id = %s
    GROUP BY cursos.id
    """, (usuario_id,),)

    profe = cursor.fetchall()
    # 🔥 CURSOS INSCRITOS
    cursor.execute(
        """
        SELECT
    cursos.*,
    COUNT(DISTINCT lecciones.id) AS total_lecciones,
    COUNT(DISTINCT inscripciones.usuario_id) AS total_estudiantes
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
    
    return render_template("VisINSTRU/menuInstru.html", cursos=cursos, profe=profe)

# Perfil USERS-------------------------------------------------------------------------------------------------------#


@app.route("/instruprofile")
def instruprofile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["user_id"]

    cursor = db.conexion.cursor(dictionary=True)


    # Datos del usuario
    cursor.execute("""
        SELECT
            usuarios.foto,
            usuarios.nombre,
            usuarios.edad,
            usuarios.email,
            COUNT(cursos.id) AS total_cursos
        FROM usuarios
        LEFT JOIN cursos ON usuarios.id = cursos.profesor_id
        WHERE usuarios.id = %s
        GROUP BY usuarios.id
    """, (usuario_id,))

    usuario = cursor.fetchone()

    # Cursos inscritos
    cursor.execute("""
        SELECT
            cursos.*,
            COUNT(DISTINCT lecciones.id) AS total_lecciones
        FROM cursos
        INNER JOIN inscripciones
            ON cursos.id = inscripciones.curso_id
        LEFT JOIN lecciones
            ON cursos.id = lecciones.curso_id
        WHERE inscripciones.usuario_id = %s
        GROUP BY cursos.id
    """, (usuario_id,))

    cursos = cursor.fetchall()

    cursor.execute("""
     select
        inscripciones.intereses
     FROM inscripciones
     WHERE usuario_id = %s
    """, (usuario_id,))

    interes = cursor.fetchone()

    cursor.close()

    return render_template(
        "VisINSTRU/insprofile.html",
        usuario=usuario,
        cursos=cursos,
        interes=interes
    )

#Miscursos-------------------------------------------------------------------------------------------------------#

@app.route("/insmiscursos")
def insmiscursos():

    if "user_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["user_id"]

    cursor = db.conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT
        cursos.*,
        COUNT(DISTINCT lecciones.id) AS total_lecciones
        FROM cursos
        LEFT JOIN lecciones
            ON cursos.id = lecciones.curso_id
        WHERE cursos.profesor_id = %s
        GROUP BY cursos.id
        """, (usuario_id,),)
    
    profe = cursor.fetchall()
    
    cursor.execute("""
            SELECT
                cursos.*,
                COUNT(DISTINCT lecciones.id) AS total_lecciones
            FROM cursos
            INNER JOIN inscripciones
                ON cursos.id = inscripciones.curso_id
            LEFT JOIN lecciones
                ON cursos.id = lecciones.curso_id
            WHERE inscripciones.usuario_id = %s
            GROUP BY cursos.id
        """, (usuario_id,))

    cursos = cursor.fetchall()

    cursor.close()

    return render_template(
        "VisINSTRU/insmiscursos.html",
        cursos=cursos, profe=profe
    )

#VistaCursos ----------------------------------------------------------------------------------------------------------#
@app.route("/insviewcourse/<int:curso_id>")
def insviewcourse(curso_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["user_id"]

    cursor = db.conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            cursos.*,
            usuarios.nombre AS profesor_nombre
        FROM cursos
        INNER JOIN usuarios
            ON usuarios.id = cursos.profesor_id
        WHERE cursos.id = %s
    """, (curso_id,))

    curso = cursor.fetchone()

    if curso is None:
        cursor.close()
        return "Curso no encontrado", 404

    puede_editar = curso["profesor_id"] == usuario_id

    cursor.execute("""
        SELECT *
        FROM lecciones
        WHERE curso_id = %s
    """, (curso_id,))

    lecciones = cursor.fetchall()

    cursor.close()

    return render_template(
        "VisINSTRU/insviewcourse.html",
        curso=curso,
        lecciones=lecciones,
        puede_editar=puede_editar
    )
# ADMIN-------------------------------------------------------------------------------------------------------#

@app.route("/editcourse/<int:id>", methods=["GET", "POST"])
def editcourse(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["user_id"]

    cursor = db.conexion.cursor(dictionary=True)

    # Verificar que el curso pertenece al profesor
    cursor.execute("""
        SELECT *
        FROM cursos
        WHERE id = %s
        AND profesor_id = %s
    """, (id, usuario_id))

    curso = cursor.fetchone()

    if curso is None:
        cursor.close()
        return "No tienes permiso para editar este curso.", 403

    if request.method == "POST":

        titulo = request.form["titulo"]
        descripcion = request.form["descripcion"]
        contenido = request.form["contenido"]
        fecha_creacion = request.form["fecha_creacion"]

        try:

            cursor.execute("""
                UPDATE cursos
                SET titulo = %s,
                    descripcion = %s,
                    contenido = %s,
                    fecha_creacion = %s
                WHERE id = %s
            """, (titulo, descripcion, contenido, fecha_creacion, id))

            db.conexion.commit()

            cursor.close()

            return redirect(url_for("insviewcourse", curso_id=id))

        except Exception as e:

            db.conexion.rollback()

            cursor.close()

            return f"Error: {e}"

    cursor.close()

    return render_template("VisINSTRU/editarCurse.html", curso=curso)
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


# ----------------------------------------------------------------------------------------------------------#
@app.route("/enroll_course/<int:curso_id>", methods=["POST"])
def enroll_course(curso_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["user_id"]

    cursor = db.conexion.cursor(dictionary=True)

    # =====================================
    # VALIDAR SI YA ESTÁ INSCRITO
    # =====================================
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

        return redirect(url_for("menuUser"))

    # =====================================
    # INSERTAR INSCRIPCIÓN
    # =====================================
    cursor.execute(
        """
        INSERT INTO inscripciones
        (usuario_id, curso_id, fecha_inscripcion)

        VALUES (%s,%s,CURDATE())
        """,
        (usuario_id, curso_id),
    )

    # =====================================
    # CREAR PROGRESO AUTOMÁTICO
    # =====================================
    cursor.execute(
        """
        INSERT INTO progreso_curso
        (
            usuario_id,
            curso_id,
            progreso,
            nota_final,
            estado,
            fecha_actualizacion
        )

        VALUES (%s,%s,%s,%s,%s,CURDATE())
        """,
        (
            usuario_id,
            curso_id,
            0,
            0,
            "PENDIENTE",
        ),
    )

    # =====================================
    # TRAER LECCIONES DEL CURSO
    # =====================================
    cursor.execute(
        """
        SELECT id
        FROM lecciones
        WHERE curso_id=%s
        """,
        (curso_id,),
    )

    lecciones = cursor.fetchall()

    # =====================================
    # CREAR NOTAS AUTOMÁTICAS
    # =====================================
    for lesson in lecciones:

        cursor.execute(
            """
            INSERT INTO nota_leccion
            (
                lecciones_id,
                usuarios_id,
                notas,
                estado,
                fecha_registro
            )

            VALUES (%s,%s,%s,%s,CURDATE())
            """,
            (
                lesson["id"],
                usuario_id,
                0,
                "PENDIENTE",
            ),
        )

    db.conexion.commit()

    cursor.close()

    return redirect(url_for("menuUser"))


# ----------------------------------------------------------------------------------------------------------#



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
            return redirect(url_for("menuUser"))    
        
        if "rol" in session and session["rol"] == "PROFESOR":
            return redirect(url_for("menuInstru"))

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
        return redirect(url_for("menuUser"))    
           
    if "rol" in session and session["rol"] == "PROFESOR":
        return redirect(url_for("menuInstru"))
   


# ----------------------------------------------------------------------------------------------------------#
if __name__ == "__main__":
    app.run(debug=True)
