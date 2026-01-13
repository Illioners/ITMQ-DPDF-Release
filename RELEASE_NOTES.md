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
