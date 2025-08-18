<h1 align="center">🕷️ OctoAutomator 🐙</h1>

<p align="center">
Automatiza las funciones core de GitHub con la agilidad de la araña y la potencia del pulpo.  
Un solo script, 8 patas para manejar tus repositorios con fluidez.  
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="License: GPL v3">
  <img src="https://img.shields.io/badge/Status-Active_Development-brightgreen.svg" alt="Status: Active Development">
  <img src="https://img.shields.io/badge/Spider-Approved-black.svg?logo=github" alt="Spider Approved">
</p>

---

## 🚀 Features
- Crear y configurar repositorios en segundos.  
- Manejo de **branches** y **PRs** automatizado.  
- Limpieza de paths irrelevantes (`__pycache__`, `migrations/`, etc.).  
- Integración lista con **APIs de GitHub**.  
- Escalable a flujos **DevOps** y **CI/CD**.  

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
GEMINI_API_KEY=(por el momento)
GITHUB_TOKEN=(token_creada_desde_gh)
GITHUB_USERNAME=username
```

3. Instalar dependencias
   
```
pip install -r requirements.txt
```

4. Ejecutar
   
```
# Code review completo
python script.py --action review --repo ./mi-proyecto --owner miusuario --remote https://github.com/miusuario/mi-proyecto.git

# Buscar secretos
python script.py --action issue --repo ./mi-proyecto

# Ver Pull Requests
python script.py --action pull

# Ver repositorios con forks
python script.py --action fork

# Auto-commit mejorado
python script.py --action commit
```

🕸️ Ejemplo de uso

```
# Crear documentación de repo local
python octoautomator.py --action review --repo "/home/SpiderNet" --owner User
```

📦 Roadmap
 Automatizar releases.

 Integrar GitHub Actions templates.

 Soporte multi-LLM para documentación de repos.

🧩 License
Este proyecto se publica bajo GPL-3.0.