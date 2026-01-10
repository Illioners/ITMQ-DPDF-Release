# Sistema de Actualizaciones Automáticas - ClasificadorPDF

## Descripción

Sistema completo de actualizaciones automáticas integrado en la aplicación ClasificadorPDF. Permite a los usuarios recibir y aplicar actualizaciones con un solo clic.

## Características

✅ **Verificación automática** al iniciar la aplicación  
✅ **Descarga e instalación automática** con barra de progreso  
✅ **Verificación de integridad** mediante SHA256  
✅ **Rollback automático** en caso de fallo  
✅ **Hosting gratuito** en GitHub Releases  
✅ **Sin dependencias externas** (usa urllib estándar)

## Arquitectura

```
┌─────────────────┐
│   proglite.py   │ ← Aplicación principal
└────────┬────────┘
         │ importa
         ▼
┌─────────────────┐
│   updater.py    │ ← Módulo de actualizaciones
└────────┬────────┘
         │ lee
         ▼
┌─────────────────┐
│build_config.json│ ← Configuración (versión, repo)
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  version.json   │ ← Info de versión remota (GitHub Pages)
└─────────────────┘
```

## Archivos del Sistema

### Core
- **`updater.py`**: Módulo principal de actualizaciones
- **`build_config.json`**: Configuración de build y versión
- **`version.json`**: Información de versión (local y remota)

### Build & Deploy
- **`build.py`**: Script de compilación automatizada
- **`ClasificadorPDF.spec`**: Configuración de PyInstaller
- **`.github/workflows/release.yml`**: GitHub Actions para releases automáticos

### Documentación
- **`RELEASE_GUIDE.md`**: Guía para crear nuevas versiones
- **`README_UPDATES.md`**: Este archivo

## Uso para Usuarios

### Verificación Manual

1. Abrir la aplicación
2. Hacer clic en "🔄 Buscar Actualizaciones"
3. Si hay actualización disponible, confirmar descarga
4. La aplicación se reiniciará automáticamente

### Verificación Automática

- La aplicación verifica actualizaciones al iniciar (cada 2 segundos después del splash)
- Si hay actualización, muestra un diálogo automáticamente
- Configurable en `build_config.json` → `auto_check_updates`

## Uso para Desarrolladores

### Crear Nueva Versión

1. **Actualizar versión** en `build_config.json`:
   ```json
   {
     "version": "1.0.1"
   }
   ```

2. **Compilar localmente** (opcional):
   ```bash
   python build.py
   ```

3. **Crear tag y push**:
   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```

4. **GitHub Actions** se encarga del resto automáticamente

Ver [RELEASE_GUIDE.md](RELEASE_GUIDE.md) para detalles completos.

## Configuración de GitHub

### Primera Vez (Setup)

1. **Habilitar GitHub Pages**:
   - Settings → Pages
   - Source: `gh-pages` branch
   - Save

2. **Verificar acceso**:
   - URL: `https://illioners.github.io/ITMQ-DPDF/version.json`
   - Debe devolver JSON con info de versión

### Crear Primer Release

```bash
# Asegúrate de que build_config.json tenga la versión correcta
python build.py

# Crea el tag
git tag v1.0.0
git push origin v1.0.0
```

## Flujo de Actualización

```
Usuario inicia app
       │
       ▼
Verificar versión remota (GitHub Pages)
       │
       ├─→ No hay actualización → Continuar normal
       │
       └─→ Actualización disponible
              │
              ▼
       Mostrar diálogo con changelog
              │
              ├─→ Usuario cancela → Continuar normal
              │
              └─→ Usuario acepta
                     │
                     ▼
              Descargar .exe desde GitHub Release
                     │
                     ▼
              Verificar SHA256
                     │
                     ├─→ Hash inválido → Error y cancelar
                     │
                     └─→ Hash válido
                            │
                            ▼
                     Crear backup del .exe actual
                            │
                            ▼
                     Reemplazar .exe con nuevo
                            │
                            ▼
                     Reiniciar aplicación
```

## Troubleshooting

### "No se pudo conectar al servidor de actualizaciones"

**Causa**: GitHub Pages no está habilitado o `version.json` no está disponible

**Solución**:
1. Verifica que GitHub Pages esté habilitado
2. Accede manualmente a: `https://illioners.github.io/ITMQ-DPDF/version.json`
3. Si no existe, crea un release para generar la rama `gh-pages`

### "El archivo descargado está corrupto"

**Causa**: El SHA256 no coincide

**Solución**:
1. Verifica que el release en GitHub tenga el ejecutable correcto
2. Regenera el release con `python build.py`
3. Asegúrate de que `version.json` tenga el SHA256 correcto

### La actualización no se instala

**Causa**: Permisos insuficientes o antivirus bloqueando

**Solución**:
1. Ejecuta la aplicación como administrador
2. Agrega excepción en el antivirus para la carpeta de la app
3. Verifica que no haya otro proceso usando el .exe

### GitHub Actions falla

**Causa**: Dependencias faltantes o error en el build

**Solución**:
1. Revisa los logs en GitHub → Actions
2. Verifica que todas las dependencias estén en `release.yml`
3. Prueba el build localmente primero con `python build.py`

## Seguridad

- ✅ **Verificación SHA256**: Cada descarga se verifica contra el hash esperado
- ✅ **HTTPS obligatorio**: Todas las descargas usan HTTPS
- ✅ **Backup automático**: Se crea backup antes de reemplazar el ejecutable
- ✅ **Rollback**: Si falla la instalación, se puede restaurar el backup
- ⚠️ **Firma de código**: No implementada (considerar para producción)

## Limitaciones

- Solo soporta Windows (puede extenderse a otros OS)
- Descarga completa del ejecutable (no actualizaciones delta)
- Requiere conexión a internet para verificar actualizaciones
- GitHub Pages puede tener latencia de ~1 minuto después del deploy

## Próximas Mejoras

- [ ] Firma de código con certificado
- [ ] Actualizaciones delta (solo cambios)
- [ ] Soporte multi-plataforma (macOS, Linux)
- [ ] Opción de actualización en segundo plano
- [ ] Historial de versiones en la UI
- [ ] Rollback manual desde la UI

## Contacto

Para reportar problemas o sugerencias sobre el sistema de actualizaciones, abre un issue en:
https://github.com/Illioners/ITMQ-DPDF/issues
