# Discord Application Bot - Professional Edition

Este es un bot de postulaciones para Discord profesional, modular y escalable, diseñado para ser fácilmente desplegable en plataformas como Railway.

## 🚀 Características

- **Persistencia de Datos**: Configuración y estado guardados en `config.json`.
- **Modularidad**: Código separado en Cogs y utilidades para fácil mantenimiento.
- **Sistema de Tickets**: Creación automática de canales para postulaciones.
- **Canal de Revisión**: Envío automático de resúmenes a un canal de staff con botones de acción.
- **Botones de Acción**: Aprobar, Rechazar o Solicitar Entrevista directamente desde el mensaje.
- **Sistema de Entrevistas**: Creación automática de canales de entrevista y asignación de roles.
- **Historial y Logs**: Registro detallado de todas las postulaciones en `data/history.json` y logs en canal de Discord.
- **Barra de Progreso**: Experiencia visual mejorada durante la postulación.
- **Configuración Fácil**: Todo se gestiona desde `config.json` y `.env`.

## 🛠️ Instalación

1. Clona este repositorio o descarga los archivos.
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Crea un archivo `.env` en la raíz del proyecto con tu token de Discord:
   ```env
   DISCORD_TOKEN=tu_token_aqui
   ```
4. Configura los IDs de canales y roles en `config.json`.
5. Ejecuta el bot:
   ```bash
   python main.py
   ```

## ⚙️ Configuración (`config.json`)

- `bot_prefix`: Prefijo para los comandos (ej. `.`).
- `channels`: IDs de los canales de aplicaciones, revisión, logs y redirección.
- `roles`: IDs de los roles de Staff, Postulante y Entrevistador.
- `categories`: IDs de las categorías para tickets y entrevistas.
- `embeds`: Personalización de títulos, descripciones y colores.

## 📝 Preguntas (`questions.json`)

Puedes modificar, añadir o quitar preguntas editando el archivo `questions.json`. El bot las cargará automáticamente.

## 📋 Comandos

- `.setup`: Envía el mensaje inicial de postulación con el botón.
- `.abrir-p`: Abre las postulaciones.
- `.cerrar-p`: Cierra las postulaciones.

## 🚢 Despliegue en Railway

1. Sube el código a un repositorio de GitHub.
2. Conecta tu repositorio a Railway.
3. Añade la variable de entorno `DISCORD_TOKEN` en Railway.
4. Railway detectará automáticamente el `requirements.txt` y ejecutará el bot.

---
Desarrollado con ❤️ para comunidades de Discord.
