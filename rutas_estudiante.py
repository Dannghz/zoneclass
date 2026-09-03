import re
import base64
from flask import Blueprint, render_template, request, redirect, url_for, session, Response, current_app
import database as db
import os
from werkzeug.utils import secure_filename
import uuid


# 1. Creas el "pedazo" de aplicación (Blueprint)
estudiante_bp = Blueprint('estudiante', __name__)

@estudiante_bp.route("/mostrar_foto/<int:profesor_id>")
def mostrar_foto(profesor_id):

    conexion = db.get_db()
    cursor = conexion.cursor(dictionary=True)



    cursor.execute("""
        SELECT estudiante.foto 
        FROM profesor
        INNER JOIN estudiante 
            ON estudiante.id = profesor.estudiante_id
        WHERE profesor.id = %s
    """, (profesor_id,))

    usuario = cursor.fetchone()

    cursor.close()

    if not usuario or not usuario["foto"]:
        return "", 404

    return Response(
        usuario["foto"],
        mimetype="image/jpeg"
    )

@estudiante_bp.route("/mi_foto")
def mi_foto():
    conexion = db.get_db()
    if "user_id" not in session:
        return "", 401

    estudiante_id = session["user_id"]

    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT foto
        FROM estudiante
        WHERE id = %s
    """, (estudiante_id,))

    usuario = cursor.fetchone()

    cursor.close()

    if not usuario or not usuario["foto"]:
        return "", 404

    return Response(
        usuario["foto"],
        mimetype="image/jpeg"
    )



# Menu Usuarios-------------------------------------------------------------------------------------------------------#

@estudiante_bp.route("/register", methods=["GET", "POST"])
def register():
    conexion = db.get_db()
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        edad = request.form.get("edad", "").strip()
        email = request.form.get("email", "").strip().lower()
        contrasena = request.form.get("contrasena", "")
        intereses = request.form.get("intereses", "").strip()

        rol = "ESTUDIANTE"
        errores = []

        # ==========================================
        # VALIDACIONES (NOMBRE, EDAD, EMAIL, CONTRASEÑA, INTERESES)
        # ==========================================
        if not nombre or len(nombre) < 2 or len(nombre) > 100:
            errores.append("Nombre inválido.")
        elif not re.match(r"^[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s]+$", nombre):
            errores.append("El nombre solamente puede contener letras y espacios.")

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

        if not email or len(email) > 150 or not re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email):
            errores.append("Ingresa un correo electrónico válido.")
        else:
            # Reconectar si el socket expiró antes de consultar
            try:
                conexion.ping(reconnect=True, attempts=3, delay=1)
                cursor = conexion.cursor(dictionary=True)
                cursor.execute("SELECT id FROM estudiante WHERE email = %s", (email,))
                email_existente = cursor.fetchone()
                cursor.close()
                if email_existente:
                    errores.append("Ese correo electrónico ya está registrado.")
            except Exception as e:
                errores.append("Error de conexión al verificar el correo.")

        if not contrasena or len(contrasena) < 5:
            errores.append("La contraseña debe tener al menos 5 caracteres.")

        if not intereses or len(intereses) < 3 or len(intereses) > 500:
            errores.append("Los intereses no son válidos.")

        # ==========================================
        # VALIDAR FOTO
        # ==========================================
        foto = request.files.get("foto")
        foto_blob = None

        if foto and foto.filename != "":
            extensiones_permitidas = {"jpg", "jpeg", "png", "webp"}
            nombre_archivo = foto.filename.lower()

            if "." not in nombre_archivo or nombre_archivo.rsplit(".", 1)[1] not in extensiones_permitidas:
                errores.append("La foto debe ser JPG, JPEG, PNG o WEBP.")

            foto.seek(0, 2)
            tamaño = foto.tell()
            foto.seek(0)

            if tamaño > 5 * 1024 * 1024:
                errores.append("La foto no puede superar los 5 MB.")

            if not errores:
                foto_blob = foto.read()

        if errores:
            return render_template(
                "VisUSERT/register.html",
                user={"nombre": nombre, "edad": edad, "email": email, "intereses": intereses},
                errores=errores
            )

        # ==========================================
        # CREAR USUARIO
        # ==========================================
        cursor = None
        try:
            # Reconectar antes de insertar por si se perdió la sesión
            conexion.ping(reconnect=True, attempts=3, delay=1)
            cursor = conexion.cursor()

            cursor.execute("""
                INSERT INTO estudiante (nombre, edad, email, contrasena, rol, intereses, foto)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (nombre, edad_numero, email, contrasena, rol, intereses, foto_blob))

            estudiante_id = cursor.lastrowid
            conexion.commit()
            cursor.close()

            session["user_id"] = estudiante_id
            session["rol"] = rol

            return redirect(url_for("estudiante.menuUser"))

        except Exception as e:
            print("================================")
            print("ERROR AL REGISTRAR ESTUDIANTE:", type(e).__name__, e)
            print("================================")

            # Controlar el rollback de forma segura según el estado de la conexión
            try:
                if conexion.is_connected():
                    conexion.rollback()
            except Exception as rollback_error:
                print("Error en rollback:", rollback_error)

            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass

            return render_template(
                "VisUSERT/register.html",
                user={"nombre": nombre, "edad": edad, "email": email, "intereses": intereses},
                errores=["No fue posible registrar el usuario por un problema de conexión o datos."]
            )

    return render_template("VisUSERT/register.html", errores=[])

# Menu Usuarios-------------------------------------------------------------------------------------------------------#

@estudiante_bp.route("/menuUser")
def menuUser():
    conexion = db.get_db()
    if "user_id" not in session:
        return redirect(url_for("login"))

    estudiante_id = session["user_id"]

    cursor = conexion.cursor(dictionary=True)

    # 🔥 TODOS LOS CURSOS


    # 🔥 CURSOS INSCRITOS
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
    
    return render_template("VisUSERT/menu.html", cursos=cursos)

# Perfil USERS-------------------------------------------------------------------------------------------------------#


@estudiante_bp.route("/profile")
def profile():
    conexion = db.get_db()
    if "user_id" not in session:
        return redirect(url_for("login"))

    estudiante_id = session["user_id"]

    cursor = conexion.cursor(dictionary=True)

    # Datos del usuario
    cursor.execute("""
        SELECT
            id,
            foto,
            nombre,
            edad,
            email, 
            intereses
        FROM estudiante
        WHERE id = %s
    """, (estudiante_id,))

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
        WHERE inscripciones.estudiante_id = %s
        GROUP BY cursos.id
    """, (estudiante_id,))

    cursos = cursor.fetchall()


    cursor.close()

    return render_template(
        "VisUSERT/perfil.html",
        usuario=usuario,
        cursos=cursos
    )




@estudiante_bp.route("/editprofile/<int:id>", methods=["GET", "POST"])
def editprofile(id):
    conexion = db.get_db()

    if "user_id" not in session:
        return redirect(url_for("estudiante.login"))  # Cambiado a 'usuarios.login'

    # El usuario solamente puede editar su propio perfil
    if session["user_id"] != id:
        return redirect(url_for("estudiante.profile"))  # Cambiado a 'usuarios.profile'

    cursor = conexion.cursor(dictionary=True)
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
        elif not re.match(r"^[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s]+$", nombre):
            errores.append("El nombre solamente puede contener letras y espacios.")

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
                    errores.append("La edad debe estar entre 13 y 100 años.")
            except ValueError:
                errores.append("La edad debe ser un número entero.")

        # =========================
        # VALIDAR EMAIL
        # =========================

        if not email:
            errores.append("El correo electrónico es obligatorio.")
        elif len(email) > 150:
            errores.append("El correo electrónico es demasiado largo.")
        elif not re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email):
            errores.append("Ingresa un correo electrónico válido.")
        else:
            cursor.execute("""
                SELECT id
                FROM estudiante
                WHERE email = %s
                AND id != %s
            """, (email, id))

            email_existente = cursor.fetchone()
            if email_existente:
                errores.append("Ese correo electrónico ya está registrado por otro estudiante.")

        # =========================
        # VALIDAR INTERESES
        # =========================

        if not intereses:
            errores.append("Debes indicar tus intereses.")
        elif len(intereses) < 3:
            errores.append("Los intereses deben tener al menos 3 caracteres.")
        elif len(intereses) > 500:
            errores.append("Los intereses no pueden superar los 500 caracteres.")

        # =========================
        # VALIDAR FOTO
        # =========================

        foto = request.files.get("foto")
        foto_blob = None

        if foto and foto.filename != "":
            extensiones_permitidas = {"jpg", "jpeg", "png", "webp"}
            nombre_archivo = foto.filename.lower()

            if "." not in nombre_archivo:
                errores.append("La foto no tiene una extensión válida.")
            else:
                extension = nombre_archivo.rsplit(".", 1)[1]
                if extension not in extensiones_permitidas:
                    errores.append("La foto debe ser JPG, JPEG, PNG o WEBP.")

            # Validar tamaño (máximo 5 MB)
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
            cursor.execute("""
                SELECT id, foto, nombre, edad, email, intereses
                FROM estudiante
                WHERE id = %s
            """, (id,))

            user = cursor.fetchone()
            cursor.close()

            if not user:
                return redirect(url_for("estudiante.profile"))

            # Mantener los valores ingresados por el usuario
            user["nombre"] = nombre
            user["edad"] = edad
            user["email"] = email
            user["intereses"] = intereses

            # Convertir foto BLOB a Base64 si existe para renderizar en HTML
            if user.get("foto") and isinstance(user["foto"], bytes):
                user["foto"] = base64.b64encode(user["foto"]).decode("utf-8")

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
                UPDATE estudiante
                SET
                    nombre = %s,
                    edad = %s,
                    email = %s,
                    intereses = %s,
                    foto = %s
                WHERE id = %s
            """, (nombre, edad_numero, email, intereses, foto_blob, id))
        else:
            cursor.execute("""
                UPDATE estudiante
                SET
                    nombre = %s,
                    edad = %s,
                    email = %s,
                    intereses = %s
                WHERE id = %s
            """, (nombre, edad_numero, email, intereses, id))

        conexion.commit()
        cursor.close()

        return redirect(url_for("estudiante.profile"))

    # =========================
    # GET
    # =========================

    cursor.execute("""
        SELECT id, foto, nombre, edad, email, intereses
        FROM estudiante
        WHERE id = %s
    """, (id,))

    user = cursor.fetchone()
    cursor.close()

    if not user:
        return redirect(url_for("estudiante.profile"))

    # Convertir foto BLOB a Base64 para mostrarla en el HTML
    if user.get("foto") and isinstance(user["foto"], bytes):
        user["foto"] = base64.b64encode(user["foto"]).decode("utf-8")

    return render_template(
        "VisUSERT/editperfil.html",
        user=user,
        errores=[]
    )

#Miscursos-------------------------------------------------------------------------------------------------------#

@estudiante_bp.route("/miscursos")
def miscursos():
    conexion = db.get_db()

    if "user_id" not in session:
        return redirect(url_for("login"))

    estudiante_id = session["user_id"]

    cursor = conexion.cursor(dictionary=True)

    cursor.execute("""
            SELECT
                cursos.*,
                COUNT(DISTINCT lecciones.id) AS total_lecciones
            FROM cursos
            INNER JOIN inscripciones
                ON cursos.id = inscripciones.curso_id
            LEFT JOIN lecciones
                ON cursos.id = lecciones.curso_id
            WHERE inscripciones.estudiante_id = %s
            GROUP BY cursos.id
        """, (estudiante_id,))

    cursos = cursor.fetchall()

    cursor.close()

    return render_template(
        "VisUSERT/miscursos.html",
        cursos=cursos
    )

#VistaCursos ----------------------------------------------------------------------------------------------------------#
@estudiante_bp.route("/view_course/<int:curso_id>")
def view_course(curso_id):
    conexion = db.get_db()

    cursor = conexion.cursor(dictionary=True)

    # =====================================
    # TRAER CURSO + PROFESOR
    # =====================================

    cursor.execute("""
        SELECT
            cursos.*,
            estudiante.nombre AS profesor_nombre,
            estudiante.foto AS profesor_foto
        FROM cursos
        LEFT JOIN profesor
            ON profesor.id = cursos.profesor_id
        LEFT JOIN estudiante
            ON estudiante.id = profesor.estudiante_id
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

    estudiante_logueado = "user_id" in session

    return render_template(
        "VisUSERT/view_course.html",
        curso=curso,
        lecciones=lecciones,
        usuario_logueado=estudiante_logueado
    )

#Vistalecciones ----------------------------------------------------------------------------------------------------------#

@estudiante_bp.route("/view_lesson/<int:id>")
def view_lesson(id):
    conexion = db.get_db()

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = conexion.cursor(dictionary=True)

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


#----------------------------------------------------------------------------------------------------------#

@estudiante_bp.route("/profesor", methods=["GET", "POST"])
def profesor():

    conexion = db.get_db()

    if "user_id" not in session:
        return redirect(url_for("login"))

    estudiante_id = session["user_id"]

    cursor = conexion.cursor(dictionary=True)

    # ==========================================
    # VERIFICAR SI EL ESTUDIANTE YA SE POSTULÓ
    # ==========================================

    cursor.execute("""
        SELECT id
        FROM profesor
        WHERE estudiante_id = %s
        LIMIT 1
    """, (estudiante_id,))

    postulacion_existente = cursor.fetchone()

    # ==========================================
    # SI YA EXISTE, NO PERMITIR POSTULARSE OTRA VEZ
    # ==========================================

    if postulacion_existente:

        cursor.close()

        return render_template(
            "VisUSERT/profesor.html",
            ya_postulado=True,
            profesor=None,
            errores=[]
        )

    errores = []

    # ==========================================
    # POST
    # ==========================================

    if request.method == "POST":

        titulo_obtenido = request.form.get(
            "titulo_obtenido", ""
        ).strip()

        institucion_educativa = request.form.get(
            "institucion_educativa", ""
        ).strip()

        nivel_estudios = request.form.get(
            "nivel_estudios", ""
        ).strip()

        # ARCHIVOS
        diploma_pdf = request.files.get(
            "ruta_diploma_pdf"
        )

        acta_pdf = request.files.get(
            "ruta_acta_pdf"
        )

        # ==========================================
        # VALIDACIONES
        # ==========================================

        if not titulo_obtenido:
            errores.append("El título es obligatorio.")

        if not institucion_educativa:
            errores.append(
                "La institución educativa es obligatoria."
            )

        if not nivel_estudios:
            errores.append(
                "El nivel de estudios es obligatorio."
            )

        if not diploma_pdf or diploma_pdf.filename == "":
            errores.append(
                "Debes subir el diploma."
            )

        if not acta_pdf or acta_pdf.filename == "":
            errores.append(
                "Debes subir el acta."
            )

        # Aquí continúa el resto de tu código
        # para guardar los PDFs e insertar la solicitud.
        # ==========================================
        # FUNCIÓN PARA GUARDAR PDF
        # ==========================================

        def guardar_pdf(archivo, carpeta):

            if not archivo or archivo.filename == "":
                return None

            nombre_original = secure_filename(
                archivo.filename
            )

            if "." not in nombre_original:

                errores.append(
                    f"El archivo '{nombre_original}' "
                    "no tiene una extensión válida."
                )

                return None

            extension = nombre_original.rsplit(
                ".",
                1
            )[1].lower()

            if extension != "pdf":

                errores.append(
                    f"El archivo '{nombre_original}' "
                    "debe ser PDF."
                )

                return None

            # ==========================================
            # VALIDAR TAMAÑO MÁXIMO 10 MB
            # ==========================================

            archivo.seek(0, 2)

            tamaño = archivo.tell()

            archivo.seek(0)

            if tamaño > 10 * 1024 * 1024:

                errores.append(
                    f"El archivo '{nombre_original}' "
                    "supera el máximo de 10 MB."
                )

                return None

            # ==========================================
            # CREAR NOMBRE ÚNICO
            # ==========================================

            nombre_unico = f"{uuid.uuid4()}.pdf"

            # ==========================================
            # CARPETA FÍSICA
            # ==========================================

            upload_folder = os.path.join(
                current_app.root_path,
                "static",
                "uploads",
                carpeta
            )

            os.makedirs(
                upload_folder,
                exist_ok=True
            )

            ruta_fisica = os.path.join(
                upload_folder,
                nombre_unico
            )

            # Guardar archivo físicamente
            archivo.save(ruta_fisica)

            # Ruta que guardarás en la BD
            ruta_bd = (
                f"uploads/{carpeta}/{nombre_unico}"
            )

            return ruta_bd

        # ==========================================
        # VALIDAR PDFs ANTES DE GUARDARLOS
        # ==========================================

        if not errores:

            ruta_diploma = guardar_pdf(
                diploma_pdf,
                "documentos"
            )

            ruta_acta = guardar_pdf(
                acta_pdf,
                "documentos"
            )

        # ==========================================
        # SI HAY ERRORES
        # ==========================================

        if errores:

            cursor.close()

            return render_template(
                "VisUSERT/profesor.html",

                profesor={
                    "titulo_obtenido": titulo_obtenido,
                    "institucion_educativa": institucion_educativa,
                    "nivel_estudios": nivel_estudios
                },

                errores=errores
            )

        # ==========================================
        # INSERTAR EN BASE DE DATOS
        # ==========================================
        cursor.execute("""
            SELECT id
            FROM profesor
            WHERE estudiante_id = %s
            LIMIT 1
        """, (estudiante_id,))

        if cursor.fetchone():

            cursor.close()

            return render_template(
                "VisUSERT/profesor.html",
                ya_postulado=True,
                profesor=None,
                errores=[]
            )
        
        cursor.execute("""

            INSERT INTO profesor (
                estudiante_id,
                titulo_obtenido,
                institucion_educativa,
                nivel_estudios,
                ruta_diploma_pdf,
                ruta_acta_pdf
            )

            VALUES (%s, %s, %s, %s, %s, %s)

        """, (

            estudiante_id,
            titulo_obtenido,
            institucion_educativa,
            nivel_estudios,
            ruta_diploma,
            ruta_acta

        ))

        # IMPORTANTE:
        # Usar la misma conexión que abriste arriba
        conexion.commit()

        cursor.close()

        return redirect(
            url_for("colaboracion")
        )

    # ==========================================
    # GET
    # ==========================================

    cursor.close()

    return render_template(
        "VisUSERT/profesor.html",
        profesor=None,
        errores=[]
    )
    