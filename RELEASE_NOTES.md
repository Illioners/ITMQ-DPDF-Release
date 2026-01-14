# Release v1.4.4

## Información del Build

- **Versión**: 1.4.4
- **Fecha**: 2026-01-14

## Novedades de Esta Versión

- ✅ **Interfaz Responsiva**: La aplicación ahora se inicia maximizada por defecto para aprovechar mejor la resolución de la pantalla.
- ✅ **Ajuste de Ventanas**: Todas las ventanas principales se autoajustan al tamaño del monitor.

---

# Release v1.4.3

## Información del Build

- **Versión**: 1.4.3
- **Fecha**: 2026-01-14

## Novedades de Esta Versión

- ✅ **Critical Fix**: Se solucionó el error `name 'hashlib' is not defined` que impedía completar la actualización.

---

# Release v1.4.2

## Información del Build

- **Versión**: 1.4.2
- **Fecha**: 2026-01-14

## Novedades de Esta Versión

- ✅ **Instalación sin Admin**: Instalador optimizado para evitar requerir permisos de Administrador.
- ✅ **Desbloqueo Fácil**: Scripts `DesbloquearApp.bat` incluidos para solucionar problemas de acceso.
- ✅ **Mejoras de Acceso**: Instalación en carpeta de usuario en lugar de Program Files.

---

# Release v1.4.1

## Información del Build

- **Versión**: 1.4.1
- **Fecha**: 2026-01-14

## Novedades de Esta Versión

- ✅ **Mejoras Generales**: Corrección de errores y optimización del rendimiento.
- ✅ **Stability**: Mejoras en la estabilidad de la aplicación.

---

# Release v1.8.0

## Información del Build

- **Versión**: 1.8.0
- **Fecha**: 2026-01-14

## Novedades de Esta Versión

- ✅ **Actualización Estructural**: Transición a distribución basada en directorios (ZIP) para mayor estabilidad.
- ✅ **Mejoras en el Updater**: Refactorización completa del sistema de actualización para manejar paquetes ZIP.
- ✅ **Corrección de Errores**: Solucionados problemas de bloqueo de archivos y errores de inicio relacionados con fuentes.
- ✅ **Optimización de Interfaz**: Ajustes en el manejo de temas claro/oscuro.

---

# Release v1.3.2

## Información del Build

- **Versión**: 1.3.2
- **Fecha**: 2026-01-13

## Novedades de Esta Versión

- ✅ **Corrección Crítica**: Corregido error de variable de versión que impedía el inicio de la aplicación.
- ✅ **Mejora del Updater**: Mayor robustez en el proceso de reemplazo de archivos y manejo de bloqueos en Windows.
- ✅ **Permisos Elevados**: El Updater ahora solicita permisos de administrador (UAC) para asegurar el reemplazo de archivos en cualquier ubicación.
- ✅ **Logs del Updater**: Implementado sistema de logs en `%LOCALAPPDATA%\ClasificadorPDF\Logs\itmq_updater.log`.

---

# Release v1.3.1

## Información del Build

- **Versión**: 1.3.1
- **Fecha**: 2026-01-13
- **SHA256**: `0747d514d1bae47592194ad3fbb89d9432a4358d461b848e75103b39c7a696b0`

## Novedades de Esta Versión

Esta versión se enfoca en la limpieza del proyecto, la eliminación de la firma digital y la optimización del proceso de compilación.

### Mejoras Principales

- ✅ **Eliminación de Firma Digital**: Se ha removido la dependencia de certificados PFX para simplificar la distribución.
- ✅ **Optimización de Build**: Script de compilación `build.py` completamente rediseñado y más robusto.
- ✅ **Limpieza de Proyecto**: Eliminación de archivos temporales, certificados obsoletos y scripts de prueba innecesarios.
- ✅ **Mejora de Consola**: Soporte mejorado para la consola de Windows en los scripts de utilidad.

### Cambios Internos

- Refactorización de `build.py` para mejor manejo de errores.
- Actualización de `.gitignore` para mayor seguridad.
- Mejora en el cálculo automático de SHA256.

## Instalación

1. Descarga `ClasificadorPDF.exe`
2. Verifica el hash SHA256 (opcional pero recomendado)
3. Ejecuta el instalador

## Notas

- Esta versión incluye actualizaciones automáticas
- El sistema verificará automáticamente nuevas versiones al iniciar
- Se recomienda cerrar todas las instancias de la aplicación antes de actualizar

## Changelog Completo

- Sistema de logging con rotación de archivos
- Configuración centralizada del actualizador
- Validación de integridad de descargas mejorada
- Mejor manejo de errores de red
- Interfaz de usuario más responsiva durante actualizaciones
- Optimizaciones de rendimiento en el motor PDF
- Correcciones menores de estabilidad
