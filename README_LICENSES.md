# Configuración de Licencias Online (GitHub)

Para que la activación automática funcione, debes subir el archivo `licenses.json` a tu repositorio GitHub.

1.  **Edita** el archivo `licenses.json` que se ha creado en esta carpeta.
2.  **Agrega** los IDs de tus clientes autorizados en la sección `authorized_ids`.
    *   Ejemplo: `"MACHINE-ID": "365D"`
    *   Puedes obtener el formato correcto usando el botón **"Copiar JSON para Servidor"** en el panel `itmq_admin.py`.
3.  **Sube** los cambios a GitHub (este paso se realiza automáticamente si apruebas la subida en el chat).
4.  **Verifica**: Navega a tu repositorio en GitHub, busca `licenses.json` y asegúrate de que esté allí.

La aplicación `ITMQ-GD` ahora consultará automáticamente ese archivo al iniciar.
