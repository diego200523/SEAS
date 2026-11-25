# SEAS · Sistema de Evaluación de Adopción de Software

Aplicación Django con PostgreSQL como base de datos de entrega. Conserva el diseño del prototipo: navegación lateral azul, acentos verdes, panel, historial y seis pasos GUIOS.

## Arranque con Docker (PostgreSQL 15)

1. Instale Docker Desktop e inícielo.
2. Copie .env.example a .env. Cambie DJANGO_SECRET_KEY, POSTGRES_PASSWORD y SEAS_ADMIN_PASSWORD. La contraseña de administrador debe tener al menos 10 caracteres y no ser común.
3. Desde esta carpeta ejecute:

    docker compose up --build

4. Abra http://127.0.0.1:8000. Entre con SEAS_ADMIN_EMAIL y la contraseña que configuró.

El arranque aplica migraciones y carga el catálogo sin sobrescribir registros existentes. Los datos permanecen en el volumen seas_database. No use docker compose down -v si desea conservarlos.

## Arranque sin Docker

Requiere Python 3.12+, PostgreSQL 15 disponible y una base de datos llamada seas. Configure .env y ejecute INICIAR.ps1 desde PowerShell. El script crea un entorno virtual, instala dependencias, aplica migraciones e inicia Waitress. No descarga ni instala PostgreSQL.

Para ejecutar solo pruebas sin PostgreSQL, establezca SEAS_SQLITE=1 y DJANGO_DEBUG=1 antes de python manage.py test core. SQLite es únicamente una alternativa de desarrollo; la configuración predeterminada usa PostgreSQL.

## Uso

- Administración: cree usuarios con los roles Administrador, Decisor y Dirección. Configure factores, subfactores, matriz, plantillas y valoraciones CSV.
- Nueva evaluación: registre organización y software. Asigne importancia, revise relevancia, califique subfactores y revise ponderaciones, FODA y decisión.
- Guardado: el indicador inferior confirma el guardado en el servidor. No cierre la ventana cuando indique cambios pendientes o error.
- Finalización: el servidor exige respuestas completas, calcula los resultados y bloquea la edición. Duplicar conserva el contexto y las importancias aplicables, pero solicita nuevas respuestas con el catálogo vigente.
- Historial: filtre, continúe borradores y consulte informes. Compare de dos a cuatro evaluaciones finalizadas con el mismo catálogo y matriz.
- Informe: descargue un PDF real con resultados, recomendaciones, respuestas y observaciones. También puede exportar los datos JSON de la evaluación.
- Dirección: consulta resultados finalizados. Por defecto tiene alcance global; una organización asignada en Usuarios limita ese acceso a su registro. Decisor solo ve sus propias evaluaciones.

## Recuperación de contraseña

El flujo genera enlaces de un solo uso y vigencia de 30 minutos. Configure SMTP en .env para entregar correos. En modo consola, el mensaje aparece en el registro del servidor y no se envía a un buzón. No hay cuentas de acceso rápido ni contraseñas en el navegador.

## Pruebas

    python manage.py test core
    coverage run --source=core.engine manage.py test core
    coverage report -m

Consulte VALIDACION.md para distinguir verificaciones ejecutadas y pendientes. METODOLOGIA.md documenta la fuente, las adaptaciones y RN09.

## Respaldo y restauración

RESPALDAR.ps1 genera un archivo PostgreSQL mediante pg_dump desde Docker. Prográmelo diariamente en el Programador de tareas del equipo que aloja SEAS; el paquete no crea tareas en su sistema. Para comprobar una restauración utilice una base de prueba separada y pg_restore. La programación diaria y una restauración real están pendientes de ejecutar en el servidor de entrega.

## Publicación

La configuración incluida es para demostración local. Antes de exponerla en Internet configure dominio, TLS, DJANGO_DEBUG=0, DJANGO_HTTPS=1, DJANGO_ALLOWED_HOSTS y SMTP; almacene las claves fuera del código. Las cookies seguras requieren HTTPS cuando DEBUG=0. Los archivos estáticos se sirven desde una ruta fija de la aplicación; en despliegues de mayor tráfico conviene servirlos mediante un proxy web.

## Estructura

- core/engine.py: motor puro RN01–RN10.
- core/models.py y core/migrations/: modelo relacional y migraciones.
- core/services.py: catálogo, autorización, transacciones e instantáneas.
- core/views.py: API, sesiones, importación CSV y PDF.
- static/: diseño y comportamiento de la interfaz.
- core/data/catalog.json: 18 factores, 61 subfactores adaptados y valores iniciales.
- core/tests.py: 28 pruebas automáticas.

Las credenciales, sesiones, bases de datos de prueba y dependencias temporales no forman parte del paquete. La cuenta inicial se crea con las variables que configure el instalador.
