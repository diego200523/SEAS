# Validación ejecutada — 20/11/2026

## Resultado técnico

- Django 5.2.19: comprobación del proyecto sin incidencias.
- Migraciones iniciales generadas y aplicadas en SQLite de prueba.
- 28 pruebas automáticas aprobadas.
- Cobertura de sentencias del motor core/engine.py: 100 % (34/34). No equivale a cobertura total de la aplicación ni a validación empírica de GUIOS.
- Catálogo inicial comprobado: 18 factores, 61 subfactores y 16 celdas de matriz.
- Sintaxis de ambos archivos JavaScript verificada.
- Generación de contenido de 17 vistas principales verificada con un entorno JavaScript aislado, sin valores undefined. Esta comprobación no sustituye pruebas en navegador.
- Respuesta HTTP 200 de la aplicación local.
- PDF real de cuatro páginas generado y revisado visualmente página a página. Incluido como informe-ejemplo.pdf con datos ficticios.

## Casos cubiertos

Todas las celdas de la matriz; escalas inválidas; cuatro cuadrantes FODA; frontera PM=3; ausencia de redondeo prematuro; soporte interno/externo; respuestas faltantes; catálogo vacío; ausencia de relevancia; fronteras RN09 y caso sin factores críticos.

Inicio de sesión; CSRF; contraseñas no expuestas; permisos de decisor y dirección; acceso a registros de otro usuario; rechazo de resultados o catálogo enviados por el cliente; instantáneas; bloqueo e idempotencia de finalización; conflicto de revisiones; reversión de cambios inválidos; duplicado sin respuestas antiguas; PDF; tokens de recuperación; autorización de configuración; CSV atómico y redondeo.

## Pendiente antes de la entrega definitiva

1. Ejecutar Docker Compose o la instalación nativa contra PostgreSQL 15. No había servidor PostgreSQL ni Docker disponible en el entorno; no se afirma compatibilidad comprobada mediante ejecución real.
2. Revisar visualmente la interfaz en escritorio y móvil, y completar una evaluación usando Chrome, Firefox y Edge. La herramienta de navegador falló y la alternativa de navegador aislado tampoco pudo iniciarse.
3. Configurar SMTP y comprobar entrega a un buzón real. Se probó el flujo y la generación del correo mediante el backend de pruebas.
4. Programar respaldo diario y ensayar restauración en una base separada.
5. Ejecutar aceptación con un usuario nuevo, contrastar accesibilidad y recibir la validación académica de las adaptaciones metodológicas.
6. Integrar el código en el repositorio del equipo y registrar la revisión del incremento.

## Registro de pruebas

```text
Found 28 test(s).
System check identified no issues (0 silenced).
Catálogo disponible: 18 factores y 61 subfactores.
Creating test database for alias 'default'...
............................
----------------------------------------------------------------------
Ran 28 tests in 9.598s

OK
Destroying test database for alias 'default'...

No changes detected
Promedio ms por evaluación: 0.305
```
