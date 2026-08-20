from flask import Blueprint, render_template, request, redirect, url_for, session, Response
import database as db
from datetime import datetime, date

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

import os
import uuid

from werkzeug.utils import secure_filename


UPLOAD_FOLDER = os.path.join(
    "static",
    "uploads",
    "lecciones"
)

EXTENSIONES_PERMITIDAS = {"pdf"}


@profesor_bp.route("/crear_leccion/<int:curso_id>", methods=["GET", "POST"])
def crear_leccion(curso_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = db.conexion.cursor(dictionary=True)

    errores = []

    # ==========================================
    # COMPROBAR QUE EL CURSO EXISTE
    # ==========================================

    cursor.execute("""
        SELECT *
        FROM cursos
        WHERE id = %s
    """, (curso_id,))

    curso = cursor.fetchone()

    if not curso:
        cursor.close()
        return "Curso no encontrado", 404

    # ==========================================
    # POST
    # ==========================================

    if request.method == "POST":

        titulo = request.form.get("titulo", "").strip()
        descripcion = request.form.get("descripcion", "").strip()

        archivos = request.files.getlist("archivos")

        # ==========================================
        # VALIDAR TÍTULO
        # ==========================================

        if not titulo:

            errores.append(
                "El título de la lección es obligatorio."
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
        # VALIDAR DESCRIPCIÓN
        # ==========================================

        if len(descripcion) > 2000:

            errores.append(
                "La descripción no puede superar los 2000 caracteres."
            )

        # ==========================================
        # VALIDAR ARCHIVOS
        # ==========================================

        archivos_validos = []

        for archivo in archivos:

            if not archivo or archivo.filename == "":
                continue

            nombre = secure_filename(archivo.filename)

            if "." not in nombre:

                errores.append(
                    f"El archivo {nombre} no tiene una extensión válida."
                )

                continue

            extension = nombre.rsplit(".", 1)[1].lower()

            if extension not in EXTENSIONES_PERMITIDAS:

                errores.append(
                    f"El archivo {nombre} debe ser un PDF."
                )

                continue

            # Máximo 10 MB por PDF
            archivo.seek(0, 2)

            tamaño = archivo.tell()

            archivo.seek(0)

            if tamaño > 10 * 1024 * 1024:

                errores.append(
                    f"El archivo {nombre} supera el límite de 10 MB."
                )

                continue

            archivos_validos.append(archivo)

        # ==========================================
        # SI HAY ERRORES
        # ==========================================

        if errores:

            cursor.close()

            return render_template(
                "VisPROF/crear_leccion.html",
                curso=curso,
                errores=errores
            )

        # ==========================================
        # CREAR CARPETA
        # ==========================================

        os.makedirs(
            UPLOAD_FOLDER,
            exist_ok=True
        )

        # ==========================================
        # CREAR LECCIÓN
        # ==========================================

        cursor.execute("""
            INSERT INTO lecciones
            (
                curso_id,
                titulo,
                descripcion
            )
            VALUES
            (
                %s,
                %s,
                %s
            )
        """, (
            curso_id,
            titulo,
            descripcion
        ))

        leccion_id = cursor.lastrowid

        # ==========================================
        # GUARDAR PDFs
        # ==========================================

        orden = 1

        for archivo in archivos_validos:

            nombre_original = secure_filename(
                archivo.filename
            )

            extension = nombre_original.rsplit(
                ".",
                1
            )[1].lower()

            nombre_unico = (
                str(uuid.uuid4())
                + "."
                + extension
            )

            ruta_fisica = os.path.join(
                UPLOAD_FOLDER,
                nombre_unico
            )

            archivo.save(ruta_fisica)

            # Esta es la ruta que guardamos en MySQL
            ruta_bd = os.path.join(
                "uploads",
                "lecciones",
                nombre_unico
            ).replace("\\", "/")

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
                leccion_id,
                nombre_original,
                ruta_bd,
                orden
            ))

            orden += 1

        # ==========================================
        # GUARDAR TODO
        # ==========================================

        db.conexion.commit()

        cursor.close()

        return redirect(
            url_for(
                "view_lesson",
                id=leccion_id
            )
        )

    # ==========================================
    # GET
    # ==========================================

    cursor.close()

    return render_template(
        "VisPROF/crear_leccion.html",
        curso=curso,
        errores=[]
    )