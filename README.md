<h1 align="center">🕷️ OctoAutomator 🐙</h1>

<p align="center">
Automatiza <strong>code reviews</strong> con LLMs y simplifica tareas repetitivas de GitHub.  
Inspirado en la agilidad de la araña y la potencia del pulpo.  
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="License: GPL v3">
  <img src="https://img.shields.io/badge/Status-Active_Development-brightgreen.svg" alt="Status: Active Development">
  <img src="https://img.shields.io/badge/Spider-Approved-black.svg?logo=github" alt="Spider Approved">
</p>

---

## 🚀 Current Features
- **Code reviews automatizados** usando Gemini (extensible a otros LLMs).  
- Generación de feedback en archivos separados.  
- Limpieza automática de paths irrelevantes (`__pycache__`, `migrations/`, etc.).  
- **Auto-commit** mejorado para flujos rápidos.  

> 🔎 Lo que ves aquí funciona ya mismo en tu entorno local.

---

## ⚡ Quickstart

### 1. Clonar el repo

```
git clone https://github.com/SPotes22/OctoAutomator.git
cd OctoAutomator
```

2. Configurar variables de entorno

Crea un archivo .env en la raíz:

```
GEMINI_API_KEY=tu_api_key
GITHUB_TOKEN=tu_token_github
GITHUB_USERNAME=tu_usuario
```

3. Instalar dependencias
```
pip install -r requirements.txt
```
4. Ejecutar
```
# Code review completo
python script.py --action review --repo ./mi-proyecto --owner miusuario

# Buscar secretos
python oscript.py --action issue --repo ./mi-proyecto

# Auto-commit mejorado
python script.py --action commit
```
🕸️ Ejemplo de uso:
```
python script.py --action review --repo "/home/SpiderNet" --owner User
```

📦 Roadmap
Automatizar releases.

Integrar templates de GitHub Actions.

Soporte multi-LLM (GPT, Claude, Llama) para documentación y reviews.

Manejo avanzado de PRs y branches.

🧩 License
Este proyecto se publica bajo GPL-3.0.

🐣 Orígenes: AutoCommit
OctoAutomator nació como un script llamado AutoCommit, que pedía mensaje de commit, confirmaba el push y ejecutaba git add, git commit y git push.
Aunque era minimalista, probó que era posible encapsular tareas repetitivas de Git en un flujo automático.
Ese prototipo creció hasta convertirse en OctoAutomator.