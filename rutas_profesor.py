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