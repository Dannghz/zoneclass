from flask import Blueprint, render_template, request, redirect, url_for, session, Response
import database as db
from datetime import datetime, date 
import os
import uuid
from werkzeug.utils import secure_filename

# 1. Creas el "pedazo" de aplicación (Blueprint)
profesor_bp = Blueprint('profesor', __name__)

# Menu Instructores-------------------------------------------------------------------------------------------------------#

@profesor_bp.route("/menuInstru")
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


@profesor_bp.route("/instruprofile")
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
            usuarios.intereses,
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

    

    cursor.close()

    return render_template(
        "VisINSTRU/insprofile.html",
        usuario=usuario,
        cursos=cursos,
    )

#Edit profile-------------------------------------------------------------------------------------------------------#
@profesor_bp.route("/insEditprofile/<int:id>", methods=["GET", "POST"])
def insEditprofile(id):

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
                "VisINSTRU/insEditperfil.html",
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

        return redirect(url_for("profesor.instruprofile"))

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
        return redirect(url_for("profesor.instruprofile"))

    return render_template(
        "VisINSTRU/insEditperfil.html",
        user=user,
        errores=[]
    )

#Miscursos-------------------------------------------------------------------------------------------------------#

@profesor_bp.route("/insmiscursos")
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
@profesor_bp.route("/insviewcourse/<int:curso_id>")
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

@profesor_bp.route("/editcourse/<int:id>", methods=["GET", "POST"])
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

            return redirect(url_for("profesor.insviewcourse", curso_id=id))

        except Exception as e:

            db.conexion.rollback()

            cursor.close()

            return f"Error: {e}"

    cursor.close()

    return render_template("VisINSTRU/editarCurse.html", curso=curso)

# ViewLesson-------------------------------------------------------------------------------------------------------#
@profesor_bp.route("/insViewlesson/<int:id>")
def insViewlesson(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["user_id"]

    cursor = db.conexion.cursor(dictionary=True)

    cursor.execute("""
        SELECT c.profesor_id 
    FROM lecciones l
    INNER JOIN cursos c ON l.curso_id = c.id
    WHERE l.id = %s """, (id,))

    resultado = cursor.fetchone()

    puede_editar = resultado["profesor_id"] == usuario_id

    cursor.execute("""
        SELECT curso_id,
        profesor_id
        FROM cursos """)

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
        "VisINSTRU/insViewleson.html",
        leccion=leccion,
        archivos_pdf=archivos_pdf,
        puede_editar=puede_editar
    )
# Edit Lesson-------------------------------------------------------------------------------------------------------#

@profesor_bp.route("/editlesson/<int:id>", methods=["GET", "POST"])
def editlesson(id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    usuario_id = session["user_id"]

    cursor = db.conexion.cursor(dictionary=True)

    # ==========================================
    # COMPROBAR QUE LA LECCIÓN EXISTE
    # Y QUE PERTENECE AL PROFESOR
    # ==========================================

    cursor.execute("""
        SELECT
            l.*,
            c.profesor_id
        FROM lecciones l
        INNER JOIN cursos c
            ON l.curso_id = c.id
        WHERE l.id = %s
    """, (id,))

    leccion = cursor.fetchone()

    if not leccion:
        cursor.close()
        return "Lección no encontrada", 404

    if leccion["profesor_id"] != usuario_id:
        cursor.close()
        return "No tienes permiso para editar esta lección", 403

    errores = []

    # ==========================================
    # OBTENER PDFs ACTUALES
    # ==========================================

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

    # ==========================================
    # POST
    # ==========================================

    if request.method == "POST":

        titulo = request.form.get("titulo", "").strip()
        vista_previa = request.form.get(
            "vistaPreviaCon",
            ""
        ).strip()

        contenido = request.form.get(
            "contenido",
            ""
        ).strip()

        # ==========================================
        # VALIDAR TÍTULO
        # ==========================================

        if not titulo:

            errores.append(
                "El título es obligatorio."
            )

        elif len(titulo) < 3:

            errores.append(
                "El título debe tener al menos 3 caracteres."
            )

        elif len(titulo) > 255:

            errores.append(
                "El título no puede superar los 255 caracteres."
            )

        # ==========================================
        # VALIDAR VISTA PREVIA
        # ==========================================

        if len(vista_previa) > 100:

            errores.append(
                "La vista previa no puede superar los 100 caracteres."
            )

        # ==========================================
        # OBTENER ORDENES DE LOS PDFs EXISTENTES
        # ==========================================

        ordenes = {}

        for archivo in archivos_pdf:

            valor = request.form.get(
                f"orden_{archivo['id']}",
                ""
            ).strip()

            try:

                orden = int(valor)

                ordenes[archivo["id"]] = orden

            except ValueError:

                errores.append(
                    f"El orden del archivo '{archivo['nombre']}' debe ser un número."
                )

        # ==========================================
        # NUEVOS ARCHIVOS
        # ==========================================

        nuevos_archivos = request.files.getlist(
            "archivos"
        )

        nuevos_archivos_validos = []

        for archivo in nuevos_archivos:

            if not archivo or archivo.filename == "":
                continue

            nombre = secure_filename(
                archivo.filename
            )

            if "." not in nombre:

                errores.append(
                    f"El archivo '{nombre}' no tiene una extensión válida."
                )

                continue

            extension = nombre.rsplit(
                ".",
                1
            )[1].lower()

            if extension != "pdf":

                errores.append(
                    f"El archivo '{nombre}' debe ser PDF."
                )

                continue

            # Máximo 10 MB

            archivo.seek(0, 2)

            tamaño = archivo.tell()

            archivo.seek(0)

            if tamaño > 10 * 1024 * 1024:

                errores.append(
                    f"El archivo '{nombre}' supera los 10 MB."
                )

                continue

            nuevos_archivos_validos.append(
                archivo
            )

        # ==========================================
        # ARCHIVOS QUE SE VAN A ELIMINAR
        # ==========================================

        eliminados = request.form.getlist(
            "eliminar_pdf"
        )

        eliminados_ids = []

        for valor in eliminados:

            try:
                eliminados_ids.append(int(valor))
            except ValueError:
                pass

        # ==========================================
        # CALCULAR CANTIDAD FINAL DE ARCHIVOS
        # ==========================================

        archivos_actuales_finales = [
            archivo
            for archivo in archivos_pdf
            if archivo["id"] not in eliminados_ids
        ]

        total_archivos = (
            len(archivos_actuales_finales)
            + len(nuevos_archivos_validos)
        )

        # ==========================================
        # VALIDAR ORDEN
        # ==========================================

        ordenes_finales = []

        for archivo in archivos_actuales_finales:

            if archivo["id"] in ordenes:

                ordenes_finales.append(
                    ordenes[archivo["id"]]
                )

        # Los nuevos archivos recibirán órdenes
        # consecutivas después de los existentes.

        siguiente_orden = (
            max(ordenes_finales)
            + 1
            if ordenes_finales
            else 1
        )

        ordenes_nuevos = []

        for archivo in nuevos_archivos_validos:

            ordenes_nuevos.append(
                siguiente_orden
            )

            siguiente_orden += 1

        todos_los_ordenes = (
            ordenes_finales
            + ordenes_nuevos
        )

        # Deben ser exactamente:
        # 1, 2, 3, ..., total_archivos

        ordenes_esperados = list(
            range(1, total_archivos + 1)
        )

        if sorted(todos_los_ordenes) != ordenes_esperados:

            errores.append(
                f"El orden de los archivos debe ser exactamente del 1 al {total_archivos}, sin repetir números."
            )

        # ==========================================
        # SI HAY ERRORES
        # ==========================================

        if errores:

            leccion["titulo"] = titulo
            leccion["vistaPreviaCon"] = vista_previa
            leccion["contenido"] = contenido

            cursor.close()

            return render_template(
                "VisINSTRU/editar_lesson.html",
                leccion=leccion,
                archivos_pdf=archivos_pdf,
                errores=errores
            )

        # ==========================================
        # ACTUALIZAR LECCIÓN
        # ==========================================

        cursor.execute("""
            UPDATE lecciones
            SET titulo = %s,
                vistaPreviaCon = %s,
                contenido = %s
            WHERE id = %s
        """, (
            titulo,
            vista_previa,
            contenido,
            id
        ))

        # ==========================================
        # ELIMINAR PDFs
        # ==========================================

        for archivo in archivos_pdf:

            if archivo["id"] not in eliminados_ids:
                continue

            # Eliminar archivo físico

            ruta_fisica = os.path.join(
                "static",
                archivo["ruta"]
            )

            if os.path.exists(ruta_fisica):

                os.remove(ruta_fisica)

            # Eliminar registro

            cursor.execute("""
                DELETE FROM archivospdf
                WHERE id = %s
                  AND leccion_id = %s
            """, (
                archivo["id"],
                id
            ))

        # ==========================================
        # ACTUALIZAR ORDEN DE PDFs EXISTENTES
        # ==========================================

        for archivo in archivos_actuales_finales:

            cursor.execute("""
                UPDATE archivospdf
                SET `orden` = %s
                WHERE id = %s
                  AND leccion_id = %s
            """, (
                ordenes[archivo["id"]],
                archivo["id"],
                id
            ))

        # ==========================================
        # GUARDAR NUEVOS PDFs
        # ==========================================

        upload_folder = os.path.join(
            "static",
            "uploads",
            "lecciones"
        )

        os.makedirs(
            upload_folder,
            exist_ok=True
        )

        for archivo, orden in zip(
            nuevos_archivos_validos,
            ordenes_nuevos
        ):

            nombre_original = secure_filename(
                archivo.filename
            )

            nombre_unico = (
                str(uuid.uuid4())
                + ".pdf"
            )

            ruta_fisica = os.path.join(
                upload_folder,
                nombre_unico
            )

            archivo.save(
                ruta_fisica
            )

            ruta_bd = (
                "uploads/lecciones/"
                + nombre_unico
            )

            cursor.execute("""
                INSERT INTO archivospdf
                (
                    leccion_id,
                    nombre,
                    ruta,
                    `orden`
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
            """, (
                id,
                nombre_original,
                ruta_bd,
                orden
            ))

        # ==========================================
        # GUARDAR CAMBIOS
        # ==========================================

        db.conexion.commit()

        cursor.close()

        return redirect(
            url_for(
                "profesor_bp.insViewlesson",
                id=id
            )
        )

    # ==========================================
    # GET
    # ==========================================

    cursor.close()

    return render_template(
        "VisINSTRU/editar_lesson.html",
        leccion=leccion,
        archivos_pdf=archivos_pdf,
        errores=[]
    )