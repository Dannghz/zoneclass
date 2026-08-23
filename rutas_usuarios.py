import re
from flask import Blueprint, render_template, request, redirect, url_for, session, Response
import database as db
from datetime import datetime, date

# 1. Creas el "pedazo" de aplicación (Blueprint)
usuarios_bp = Blueprint('usuarios', __name__)

@usuarios_bp.route("/mostrar_foto/<int:id>")
def mostrar_foto(id):

    cursor = db.conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT foto
        FROM usuarios
        WHERE id = %s
    """, (id,))

    usuario = cursor.fetchone()

    cursor.close()

    if not usuario or not usuario["foto"]:
        return "", 404

    return Response(
        usuario["foto"],
        mimetype="image/jpeg"
    )

@usuarios_bp.route("/mi_foto")
def mi_foto():

    if "user_id" not in session:
        return "", 401

    usuario_id = session["user_id"]

    cursor = db.conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT foto
        FROM usuarios
        WHERE id = %s
    """, (usuario_id,))

    usuario = cursor.fetchone()

    cursor.close()

    if not usuario or not usuario["foto"]:
        return "", 404

    return Response(
        usuario["foto"],
        mimetype="image/jpeg"
    )

# Menu Usuarios-------------------------------------------------------------------------------------------------------#

@usuarios_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        nombre = request.form.get("nombre", "").strip()
        edad = request.form.get("edad", "").strip()
        email = request.form.get("email", "").strip().lower()
        contrasena = request.form.get("contrasena", "")
        intereses = request.form.get("intereses", "").strip()

        rol = "USUARIO"

        errores = []

        # ==========================================
        # VALIDAR NOMBRE
        # ==========================================

        if not nombre:
            errores.append(
                "El nombre es obligatorio."
            )

        elif len(nombre) < 2:
            errores.append(
                "El nombre debe tener al menos 2 caracteres."
            )

        elif len(nombre) > 100:
            errores.append(
                "El nombre no puede superar los 100 caracteres."
            )

        elif not re.match(
            r"^[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s]+$",
            nombre
        ):
            errores.append(
                "El nombre solamente puede contener letras y espacios."
            )

        # ==========================================
        # VALIDAR EDAD
        # ==========================================

        edad_numero = None

        if not edad:
            errores.append(
                "La edad es obligatoria."
            )

        else:
            try:

                edad_numero = int(edad)

                if edad_numero < 13 or edad_numero > 100:
                    errores.append(
                        "La edad debe estar entre 13 y 100 años."
                    )

            except ValueError:
                errores.append(
                    "La edad debe ser un número entero."
                )

        # ==========================================
        # VALIDAR EMAIL
        # ==========================================

        if not email:

            errores.append(
                "El correo electrónico es obligatorio."
            )

        elif len(email) > 150:

            errores.append(
                "El correo electrónico es demasiado largo."
            )

        elif not re.match(
            r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
            email
        ):

            errores.append(
                "Ingresa un correo electrónico válido."
            )

        # ==========================================
        # COMPROBAR EMAIL EXISTENTE
        # ==========================================

        else:

            cursor = db.conexion.cursor(dictionary=True)

            cursor.execute("""
                SELECT id
                FROM usuarios
                WHERE email = %s
            """, (email,))

            email_existente = cursor.fetchone()

            cursor.close()

            if email_existente:
                errores.append(
                    "Ese correo electrónico ya está registrado."
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
        # VALIDAR INTERESES
        # ==========================================

        if not intereses:

            errores.append(
                "Debes indicar tus intereses."
            )

        elif len(intereses) < 3:

            errores.append(
                "Los intereses deben tener al menos 3 caracteres."
            )

        elif len(intereses) > 500:

            errores.append(
                "Los intereses no pueden superar los 500 caracteres."
            )

        # ==========================================
        # VALIDAR FECHA DE REGISTRO
        # ==========================================

        

        else:


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

                errores.append(
                    "La foto no tiene una extensión válida."
                )

            else:

                extension = nombre_archivo.rsplit(
                    ".",
                    1
                )[1]

                if extension not in extensiones_permitidas:

                    errores.append(
                        "La foto debe ser JPG, JPEG, PNG o WEBP."
                    )

            # ==========================================
            # MÁXIMO 5 MB
            # ==========================================

            foto.seek(0, 2)

            tamaño = foto.tell()

            foto.seek(0)

            if tamaño > 5 * 1024 * 1024:

                errores.append(
                    "La foto no puede superar los 5 MB."
                )

            # ==========================================
            # LEER FOTO SI NO TIENE ERRORES
            # ==========================================

            if not errores:

                foto_blob = foto.read()

        # ==========================================
        # SI HAY ERRORES
        # ==========================================

        if errores:

            user = {
                "nombre": nombre,
                "edad": edad,
                "email": email,
                "intereses": intereses
            }

            return render_template(
                "VisUSERT/register.html",
                user=user,
                errores=errores
            )

        # ==========================================
        # CREAR USUARIO
        # ==========================================

        try:

            cursor = db.conexion.cursor()

            cursor.execute("""
                INSERT INTO usuarios
                (
                    nombre,
                    edad,
                    email,
                    contrasena,
                    rol,
                    intereses,
                    foto
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """, (
                nombre,
                edad_numero,
                email,
                contrasena,
                rol,
                intereses,
                foto_blob
            ))

            usuario_id = cursor.lastrowid
            
            db.conexion.commit()

            cursor.close()

            session["user_id"] = usuario_id
            session["rol"] = rol

            return redirect(
                url_for("usuarios.menuUser")
            )

        except Exception as e:

            db.conexion.rollback()

            try:
                cursor.close()
            except:
                pass

            return render_template(
                "VisUSERT/register.html",
                user={
                    "nombre": nombre,
                    "edad": edad,
                    "email": email,
                    "intereses": intereses,
                },
                errores=[str(e)]
            )

    # ==========================================
    # GET
    # ==========================================

    return render_template(
        "VisUSERT/register.html",
        errores=[]
    )

# Menu Usuarios-------------------------------------------------------------------------------------------------------#

@usuarios_bp.route("/menuUser")
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


@usuarios_bp.route("/profile")
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
            email, 
            intereses
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


    cursor.close()

    return render_template(
        "VisUSERT/perfil.html",
        usuario=usuario,
        cursos=cursos
    )


@usuarios_bp.route("/editprofile/<int:id>", methods=["GET", "POST"])
def editprofile(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    # El usuario solamente puede editar su propio perfil
    if session["user_id"] != id:
        return redirect(url_for("profile"))

    cursor = db.conexion.cursor(dictionary=True)

    errores = []

    if request.method == "POST":

        nombre = request.form.get("nombre", "").strip()
        edad = request.form.get("edad", "").strip()
        email = request.form.get("email", "").strip().lower()
        intereses = request.form.get("intereses", "").strip()

        # =========================
        # VALIDAR NOMBRE
        # =========================

        if not nombre:
            errores.append("El nombre es obligatorio.")

        elif len(nombre) < 2:
            errores.append("El nombre debe tener al menos 2 caracteres.")

        elif len(nombre) > 100:
            errores.append("El nombre no puede superar los 100 caracteres.")

        elif not re.match(
            r"^[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s]+$",
            nombre
        ):
            errores.append(
                "El nombre solamente puede contener letras y espacios."
            )

        # =========================
        # VALIDAR EDAD
        # =========================

        edad_numero = None

        if not edad:

            errores.append("La edad es obligatoria.")

        else:

            try:

                edad_numero = int(edad)

                if edad_numero < 13 or edad_numero > 100:
                    errores.append(
                        "La edad debe estar entre 13 y 100 años."
                    )

            except ValueError:

                errores.append(
                    "La edad debe ser un número entero."
                )

        # =========================
        # VALIDAR EMAIL
        # =========================

        if not email:

            errores.append(
                "El correo electrónico es obligatorio."
            )

        elif len(email) > 150:

            errores.append(
                "El correo electrónico es demasiado largo."
            )

        elif not re.match(
            r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
            email
        ):

            errores.append(
                "Ingresa un correo electrónico válido."
            )

        else:

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
        # VALIDAR INTERESES
        # =========================

        if not intereses:

            errores.append(
                "Debes indicar tus intereses."
            )

        elif len(intereses) < 3:

            errores.append(
                "Los intereses deben tener al menos 3 caracteres."
            )

        elif len(intereses) > 500:

            errores.append(
                "Los intereses no pueden superar los 500 caracteres."
            )

        # =========================
        # VALIDAR FOTO
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

                errores.append(
                    "La foto no tiene una extensión válida."
                )

            else:

                extension = nombre_archivo.rsplit(".", 1)[1]

                if extension not in extensiones_permitidas:

                    errores.append(
                        "La foto debe ser JPG, JPEG, PNG o WEBP."
                    )

            # Máximo 5 MB
            foto.seek(0, 2)
            tamaño = foto.tell()
            foto.seek(0)

            if tamaño > 5 * 1024 * 1024:

                errores.append(
                    "La foto no puede superar los 5 MB."
                )

            if not errores:

                foto_blob = foto.read()

        # =========================
        # SI HAY ERRORES
        # =========================

        if errores:

            cursor.execute("""
                SELECT
                    id,
                    foto,
                    nombre,
                    edad,
                    email,
                    intereses
                FROM usuarios
                WHERE id = %s
            """, (id,))

            user = cursor.fetchone()

            # Mantener los valores escritos
            user["nombre"] = nombre
            user["edad"] = edad
            user["email"] = email
            user["intereses"] = intereses

            cursor.close()

            return render_template(
                "VisUSERT/editperfil.html",
                user=user,
                errores=errores
            )

        # =========================
        # ACTUALIZAR USUARIO
        # =========================

        if foto_blob is not None:

            cursor.execute("""
                UPDATE usuarios
                SET
                    nombre = %s,
                    edad = %s,
                    email = %s,
                    intereses = %s,
                    foto = %s
                WHERE id = %s
            """, (
                nombre,
                edad_numero,
                email,
                intereses,
                foto_blob,
                id
            ))

        else:

            cursor.execute("""
                UPDATE usuarios
                SET
                    nombre = %s,
                    edad = %s,
                    email = %s,
                    intereses = %s
                WHERE id = %s
            """, (
                nombre,
                edad_numero,
                email,
                intereses,
                id
            ))

        db.conexion.commit()

        cursor.close()

        return redirect(url_for("usuarios.profile"))

    # =========================
    # GET
    # =========================

    cursor.execute("""
        SELECT
            id,
            foto,
            nombre,
            edad,
            email,
            intereses
        FROM usuarios
        WHERE id = %s
    """, (id,))

    user = cursor.fetchone()

    cursor.close()

    if not user:
        return redirect(url_for("usuarios.profile"))

    return render_template(
        "VisUSERT/editperfil.html",
        user=user,
        errores=[]
    )

#Miscursos-------------------------------------------------------------------------------------------------------#

@usuarios_bp.route("/miscursos")
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
@usuarios_bp.route("/view_course/<int:curso_id>")
def view_course(curso_id):

    cursor = db.conexion.cursor(dictionary=True)

    # =====================================
    # TRAER CURSO + PROFESOR
    # =====================================

    cursor.execute("""
        SELECT
            cursos.*,
            usuarios.nombre AS profesor_nombre,
            usuarios.foto AS profesor_foto
        FROM cursos
        INNER JOIN usuarios
            ON usuarios.id = cursos.profesor_id
        WHERE cursos.id = %s
    """, (curso_id,))

    curso = cursor.fetchone()

    if not curso:
        cursor.close()
        return "Curso no encontrado", 404

    # =====================================
    # TRAER LECCIONES
    # =====================================

    cursor.execute("""
        SELECT *
        FROM lecciones
        WHERE curso_id = %s
        ORDER BY id ASC
    """, (curso_id,))

    lecciones = cursor.fetchall()

    cursor.close()

    # =====================================
    # SABER SI EL USUARIO ESTÁ LOGUEADO
    # =====================================

    usuario_logueado = "user_id" in session

    return render_template(
        "VisUSERT/view_course.html",
        curso=curso,
        lecciones=lecciones,
        usuario_logueado=usuario_logueado
    )

#Vistalecciones ----------------------------------------------------------------------------------------------------------#

@usuarios_bp.route("/view_lesson/<int:id>")
def view_lesson(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = db.conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM lecciones
        WHERE id = %s
    """, (id,))

    leccion = cursor.fetchone()

    if not leccion:

        cursor.close()

        return "Lección no encontrada", 404

    cursor.execute("""
        SELECT
            id,
            leccion_id,
            nombre,
            ruta,
            `orden`,
            fechaSubida
        FROM archivospdf
        WHERE leccion_id = %s
        ORDER BY `orden`, id
    """, (id,))

    archivos_pdf = cursor.fetchall()

    cursor.close()

    return render_template(
        "VisUSERT/leccion.html",
        leccion=leccion,
        archivos_pdf=archivos_pdf
    )