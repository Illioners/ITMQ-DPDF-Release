# Instrucciones de Instalación - ClasificadorPDF

## Documentación Técnica

Este documento explica en detalle por qué ocurre el error "Windows no puede acceder al dispositivo" y cómo solucionarlo.

---

## El Problema: Mark of the Web (MOTW)

### ¿Qué es MOTW?

Cuando descargas un archivo de Internet, Windows agrega un **Alternate Data Stream (ADS)** llamado `Zone.Identifier` al archivo. Este stream contiene información sobre el origen del archivo:

```
[ZoneTransfer]
ZoneId=3
ReferrerUrl=https://github.com/...
HostUrl=https://github.com/...
```

### Zonas de Seguridad de Windows

- **Zone 0**: Computadora local
- **Zone 1**: Intranet local
- **Zone 2**: Sitios de confianza
- **Zone 3**: Internet (archivos descargados)
- **Zone 4**: Sitios restringidos

Los archivos con `ZoneId=3` son tratados con restricciones adicionales de seguridad.

### ¿Por qué afecta a ejecutables?

Windows aplica políticas de seguridad más estrictas a archivos ejecutables (`.exe`, `.dll`, `.bat`) descargados de Internet:

1. **SmartScreen Filter**: Verifica la reputación del archivo
2. **Firma Digital**: Verifica si el ejecutable está firmado
3. **Restricciones de Ejecución**: Puede bloquear completamente la ejecución

Como `ClasificadorPDF.exe` es compilado con PyInstaller y **no utiliza firma digital** (decisión de diseño para evitar costos y renovaciones), Windows puede marcarlo inicialmente como desconocido.

---

## Soluciones Implementadas

### 1. DesbloquearApp.bat (Recomendado)

**Ventajas:**
- ✅ NO requiere permisos de administrador
- ✅ Funciona en cuentas de usuario estándar
- ✅ Desbloquea todos los archivos recursivamente
- ✅ Lanza automáticamente la aplicación

**Cómo funciona:**

```batch
powershell -Command "Get-ChildItem -Path '.' -Recurse -File | Unblock-File"
```

Este comando:
1. Lista todos los archivos en la carpeta actual y subcarpetas
2. Ejecuta `Unblock-File` en cada uno
3. `Unblock-File` elimina el ADS `Zone.Identifier`

**Limitaciones:**
- Requiere PowerShell (incluido en Windows 7+)
- No funciona si el usuario no tiene permisos sobre los archivos

### 2. RepararAcceso.bat (Opción Avanzada)

**Ventajas:**
- ✅ Desbloquea archivos
- ✅ Modifica permisos NTFS
- ✅ Soluciona problemas de permisos corruptos

**Desventajas:**
- ❌ Requiere permisos de administrador
- ❌ Más complejo para usuarios normales

**Cuándo usar:**
- Cuando `DesbloquearApp.bat` no funciona
- Cuando hay problemas de permisos NTFS
- En entornos corporativos con políticas restrictivas

---

## Mejoras en el Updater

### Problema Original

El `itmq_updater.py` descargaba archivos pero no los desbloqueaba automáticamente, causando que las actualizaciones automáticas también estuvieran bloqueadas.

### Solución Implementada

```python
# En replace_file()
try:
    subprocess.run([
        "powershell", 
        "-Command", 
        f"Unblock-File -Path '{self.target_path}'"
    ], capture_output=True)
    logger.info("Unblock-File successful.")
except:
    pass
```

Ahora el updater:
1. Descarga el nuevo ejecutable
2. Reemplaza el archivo antiguo
3. **Desbloquea automáticamente el nuevo archivo**
4. Lanza la aplicación actualizada

---

## Proceso de Distribución

### Estructura del ZIP

```
ClasificadorPDF-v1.3.0.zip
├── ClasificadorPDF.exe          # Aplicación principal
├── DesbloquearApp.bat           # Script de desbloqueo (NUEVO)
├── RepararAcceso.bat            # Script avanzado
├── LEEME.txt                    # Instrucciones (NUEVO)
├── _internal/                   # Dependencias de PyInstaller
│   ├── *.dll
│   ├── *.pyd
│   └── ...
└── ITMQ-Updater.exe            # Updater standalone (opcional)
```

### Modificaciones en build.py

```python
# Copiar archivos de documentación al dist
repair_script = get_abs_path('RepararAcceso.bat')
unlock_script = get_abs_path('DesbloquearApp.bat')
readme = get_abs_path('LEEME.txt')

for file in [repair_script, unlock_script, readme]:
    if os.path.exists(file):
        shutil.copy2(file, os.path.join(os.path.dirname(exe_path), os.path.basename(file)))
```

---

## Alternativas Consideradas

### 1. Firma Digital con Certificado de Código

**Pros:**
- ✅ Solución definitiva
- ✅ Windows confía automáticamente
- ✅ No requiere scripts de desbloqueo

**Contras:**
- ❌ Costo: $100-$400 USD/año
- ❌ Proceso de validación (días/semanas)
- ❌ Requiere renovación anual

**Estado:** El uso de certificados PFX ha sido descartado para simplificar la distribución.

### 2. Compilación con Nuitka

**Pros:**
- ✅ Genera ejecutables más "limpios"
- ✅ Mejor rendimiento
- ✅ Más difícil de descompilar

**Contras:**
- ❌ Proceso de compilación más complejo
- ❌ Aún requiere firma digital para evitar SmartScreen
- ❌ Problemas de compatibilidad con algunas librerías

**Estado:** No implementado (PyInstaller es suficiente)

### 3. Distribución vía Microsoft Store

**Pros:**
- ✅ Firma automática por Microsoft
- ✅ Actualizaciones automáticas integradas
- ✅ Confianza total de Windows

**Contras:**
- ❌ Costo: $19 USD registro + comisión por venta
- ❌ Proceso de revisión estricto
- ❌ Restricciones de empaquetado (MSIX)

**Estado:** No viable para distribución interna

---

## Verificación Manual

### Comprobar si un archivo está bloqueado

**PowerShell:**
```powershell
Get-Item -Path "ClasificadorPDF.exe" -Stream Zone.Identifier
```

Si el archivo está bloqueado, verás:
```
FileName: C:\...\ClasificadorPDF.exe
Stream  : Zone.Identifier
Length  : 26
```

### Desbloquear manualmente un archivo

**PowerShell:**
```powershell
Unblock-File -Path "ClasificadorPDF.exe"
```

**Interfaz gráfica:**
1. Clic derecho en el archivo
2. Propiedades
3. En la pestaña "General", abajo verás: "Este archivo proviene de otro equipo..."
4. Marca la casilla "Desbloquear"
5. Aplicar y Aceptar

---

## Logs y Diagnóstico

### Ubicación de Logs

```
%LOCALAPPDATA%\ClasificadorPDF\Logs\
├── itmq_updater.log    # Logs del updater
└── app.lock            # Lock file para instancia única
```

### Información útil en logs

```
2026-01-14 07:30:00 - INFO - Updater initialized. Target: C:\...\ClasificadorPDF.exe
2026-01-14 07:30:05 - INFO - Download completed: C:\...\ClasificadorPDF.exe.tmp
2026-01-14 07:30:06 - INFO - Target replaced successfully. Attempting to unblock...
2026-01-14 07:30:06 - INFO - Unblock-File successful.
```

---

## Preguntas Frecuentes

### ¿Por qué no firmar el ejecutable?

Los certificados de firma de código válidos tienen un costo anual elevado y requieren procesos de validación complejos. Para esta aplicación, se ha decidido **eliminar por completo** la firma digital para simplificar el mantenimiento y la distribución, utilizando en su lugar scripts de desbloqueo que son gratuitos y efectivos.

### ¿Es seguro ejecutar DesbloquearApp.bat?

Sí. El script solo ejecuta comandos de PowerShell estándar de Windows (`Unblock-File`). No modifica archivos del sistema ni requiere permisos elevados.

### ¿Qué pasa si no ejecuto el script de desbloqueo?

Windows puede:
1. Mostrar el error "Windows no puede acceder al dispositivo"
2. Bloquear la ejecución completamente
3. Mostrar advertencias de SmartScreen

### ¿Necesito ejecutar el script cada vez?

No. Solo necesitas ejecutar `DesbloquearApp.bat` UNA VEZ después de:
- Descargar la aplicación por primera vez
- Extraer un nuevo ZIP descargado
- Copiar los archivos desde un USB o red

Las actualizaciones automáticas NO requieren volver a ejecutar el script.

---

## Referencias

- [Microsoft Docs: Unblock-File](https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/unblock-file)
- [Mark of the Web (MOTW)](https://docs.microsoft.com/en-us/windows/security/threat-protection/windows-defender-application-control/configure-windows-defender-application-control-policies)
- [Zone.Identifier ADS](https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-fscc/6e3f7352-d11c-4d76-8c39-2516a9df36e8)
- [PyInstaller Security](https://pyinstaller.org/en/stable/operating-mode.html#windows-security)

---

**Última actualización:** 2026-01-14  
**Versión del documento:** 1.0  
**Autor:** ITMQ Development Team
