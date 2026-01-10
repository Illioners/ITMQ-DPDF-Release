# Guía de Release - ClasificadorPDF

Esta guía explica cómo crear una nueva versión de la aplicación.

## Requisitos Previos

- Python 3.11+ instalado
- PyInstaller y dependencias instaladas (`pip install -r requirements.txt`)
- Acceso al repositorio GitHub

## Proceso de Release

### 1. Actualizar Versión

Edita `build_config.json` y actualiza el número de versión:

```json
{
  "app_name": "ClasificadorPDF",
  "version": "1.0.1",  // <- Actualiza aquí
  "github_repo": "Illioners/ITMQ-DPDF",
  "auto_check_updates": true
}
```

### 2. Compilar Localmente (Opcional pero Recomendado)

Prueba el build localmente antes de crear el release:

```bash
python build.py
```

Esto generará:
- `dist/ClasificadorPDF.exe` - El ejecutable
- `version.json` - Actualizado con SHA256
- `RELEASE_NOTES.md` - Notas de la versión

### 3. Probar el Ejecutable

Ejecuta `dist/ClasificadorPDF.exe` y verifica:
- ✓ La aplicación inicia correctamente
- ✓ El logo se muestra
- ✓ La versión en el footer es correcta
- ✓ Todas las funcionalidades principales funcionan

### 4. Crear Tag de Git

Una vez verificado, crea el tag de versión:

```bash
git add .
git commit -m "Release v1.0.1"
git tag v1.0.1
git push origin main
git push origin v1.0.1
```

### 5. GitHub Actions Automático

Al hacer push del tag, GitHub Actions automáticamente:
1. ✓ Compila la aplicación en Windows
2. ✓ Calcula el SHA256
3. ✓ Crea el GitHub Release
4. ✓ Sube el ejecutable como asset
5. ✓ Actualiza `version.json` en GitHub Pages

### 6. Verificar Release

1. Ve a `https://github.com/Illioners/ITMQ-DPDF/releases`
2. Verifica que el release se creó correctamente
3. Descarga el ejecutable y pruébalo
4. Verifica que `version.json` esté disponible en GitHub Pages

## Versionado Semántico

Usa [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.x.x): Cambios incompatibles con versiones anteriores
- **MINOR** (x.1.x): Nueva funcionalidad compatible
- **PATCH** (x.x.1): Correcciones de bugs

Ejemplos:
- `1.0.0` → `1.0.1` - Corrección de bugs
- `1.0.1` → `1.1.0` - Nueva característica
- `1.1.0` → `2.0.0` - Cambio importante/breaking change

## Changelog

Mantén un registro de cambios en cada release. Edita `RELEASE_NOTES.md` antes del release para incluir:

- **Nuevas características**: Qué se agregó
- **Correcciones**: Qué bugs se arreglaron
- **Mejoras**: Qué se optimizó
- **Breaking changes**: Qué puede romper compatibilidad

## Troubleshooting

### El build falla localmente

```bash
# Reinstala dependencias
pip install --upgrade pyinstaller pillow pymupdf pytesseract

# Limpia builds anteriores
pyinstaller ClasificadorPDF.spec --clean
```

### GitHub Actions falla

1. Verifica los logs en la pestaña "Actions" del repositorio
2. Asegúrate de que todas las dependencias estén en el workflow
3. Verifica que `build_config.json` tenga el formato correcto

### Las actualizaciones no funcionan

1. Verifica que GitHub Pages esté habilitado
2. Confirma que `version.json` esté en la rama `gh-pages`
3. Prueba acceder a: `https://illioners.github.io/ITMQ-DPDF/version.json`

## Configuración de GitHub Pages

Para habilitar GitHub Pages (solo necesario la primera vez):

1. Ve a Settings → Pages
2. Source: Deploy from a branch
3. Branch: `gh-pages` / `root`
4. Save

## Notas Adicionales

- El sistema de actualizaciones verifica automáticamente al iniciar la app
- Los usuarios recibirán una notificación cuando haya una nueva versión
- La descarga e instalación es automática con un solo clic
- El ejecutable anterior se respalda automáticamente antes de actualizar
