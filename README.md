# OctoAutomator
---

OctoAutomator es un script que simplifica y automatiza las funciones core de GitHub.
Inspirado en la agilidad de la araña y la potencia del pulpo, OctoAutomator extiende sus 8 patas para manejar repositorios con fluidez.

---

🚀 Features

Crear y configurar repositorios en segundos.

Manejo de branches y PRs automatizado.

Limpieza de paths irrelevantes (__pycache__, migrations/, etc.).

Integración lista con APIs de GitHub.

Escalable a flujos DevOps y CI/CD.

---

⚡ Quickstart
1. Clonar el repo
```
git clone https://github.com/SPotes22/OctoAutomator.git
cd OctoAutomator
```
2. Configurar variables de entorno

Crea un archivo .env en la raíz:
```
GEMINI_API_KEY=(Por el momento)
GITHUB_TOKEN=(token_creada_desde_gh)
GITHUB_USERNAME=username
```
3. Instalar dependencias
```
pip install -r requirements.txt
```
4. Ejecutar
```
 Code review completo
python script.py --action review --repo ./mi-proyecto --owner miusuario --remote https://github.com/miusuario/mi-proyecto.git

# Buscar secretos
python script.py --action issue --repo ./mi-proyecto

# Ver Pull Requests
python script.py --action pull

# Ver repositorios con forks
python script.py --action fork

# Auto-commit mejorado
python script.py --action commit
````

🕸️ Ejemplo de uso
# Crear documentacion repo local 
```
python octoautomator.py --action review  --repo /home/SpiderNet" --owner User
```                        
--- 

📦 Roadmap

 Automatizar releases.

 Integrar GitHub Actions templates.

 Soporte multi-LLM para documentación de repos.

🧩 License

Este proyecto se publica bajo GPL-3.0
---

![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)  
![Status: Active](https://img.shields.io/badge/Status-Active_Development-brightgreen.svg)  
![Spider Approved](https://img.shields.io/badge/Spider-Approved-black.svg?logo=github)

---
