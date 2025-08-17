# GitSlave - herramienta de automatización
# Copyright (C) 2025  Santiago Potes Giraldo
#
# Este programa es software libre: puedes redistribuirlo y/o modificarlo
# bajo los términos de la Licencia Pública General de GNU publicada por
# la Free Software Foundation, ya sea la versión 3 de la Licencia, o
# (a tu elección) cualquier versión posterior.
#
# Este programa se distribuye con la esperanza de que sea útil,
# pero SIN NINGUNA GARANTÍA; ni siquiera la garantía implícita de
# COMERCIALIZACIÓN o IDONEIDAD PARA UN PROPÓSITO PARTICULAR.
# Consulta la Licencia Pública General de GNU para más detalles.
#
# Deberías haber recibido una copia de la Licencia junto a este programa.
# En caso contrario, consulta <https://www.gnu.org/licenses/>.


import os
import re
import time
import json
import hashlib
import argparse
import requests
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

GITHUB_HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
EXCLUDE_PATHS = ["migrations/", "__pycache__/", "venv/", "env/", "node_modules/", ".git/"]
DAILY_LIMIT = 200  # máximo archivos por día

# Filtros por stack para limpiar código antes de enviar a Gemini
FILTERS_BY_STACK = {
    "django": [
        (r"(SECRET_KEY\s*=\s*['\"].*?['\"])", "SECRET_KEY = '***REDACTED***'"),
        (r"(PASSWORD\s*=\s*['\"].*?['\"])", "PASSWORD = '***REDACTED***'"),
        (r"(API_KEY\s*=\s*['\"].*?['\"])", "API_KEY = '***REDACTED***'"),
        (r"(DEBUG\s*=\s*True)", r"\1  # DEV MODE: No usar en producción"),
        (r"(ALLOWED_HOSTS\s*=\s*\[.*?\])", "ALLOWED_HOSTS = ['*']  # DEV ONLY")
    ],
    "flask": [
        (r"(SECRET_KEY\s*=\s*['\"].*?['\"])", "SECRET_KEY = '***REDACTED***'"),
        (r"(SQLALCHEMY_DATABASE_URI\s*=\s*['\"].*?['\"])", "SQLALCHEMY_DATABASE_URI = '***REDACTED***'"),
        (r"(DEBUG\s*=\s*True)", r"\1  # DEV MODE: No usar en producción")
    ],
    "node": [
        (r"(process\.env\.(?:[A-Z_]+_?KEY|PASSWORD|TOKEN|SECRET)[^\n]*)", "/* ***REDACTED*** */"),
        (r"(['\"](?:AIza|sk-|ghp_)[A-Za-z0-9_\-]+['\"])", "'***REDACTED***'"),
        (r"(app\.listen\(\s*\d+\s*\))", r"\1 // DEV PORT, ajustar en producción")
    ],
    "react": [
        (r"(process\.env\.REACT_APP_[A-Z0-9_]+)", "/* ***REDACTED*** */"),
        (r"(https?:\/\/[^\s'\"]+\/api[^\s'\"]*)", "'***REDACTED_URL***'"),
        (r"(mode:\s*'development')", r"\1 // DEV BUILD")
    ],
    "restapi": [
        (r"(Bearer\s+[A-Za-z0-9_\-\.]+)", "Bearer ***REDACTED***"),
        (r"(Authorization:\s*['\"]?[A-Za-z0-9_\-\.]+['\"]?)", "Authorization: ***REDACTED***"),
        (r"(https?:\/\/(?:localhost|127\.0\.0\.1|192\.\d+\.\d+\.\d+)[^\s'\"]*)", "'***LOCAL_URL***'"),
        (r"(sandbox|dev|staging)", r"\1 // TEST ENVIRONMENT")
    ]
}

class ProgressTracker:
    def __init__(self, total_files):
        self.total_files = total_files
        self.current_file = 0
        
    def update_file(self, filename, stage):
        """
        Stages: 'reading', 'processing', 'writing'
        """
        stage_names = {
            'reading': '📖 Leyendo archivo',
            'processing': '🤖 Procesando con Gemini', 
            'writing': '💾 Escribiendo review'
        }
        
        progress = (self.current_file / self.total_files) * 100
        print(f"\n[{progress:.1f}%] {stage_names[stage]}: {filename}")
        print(f"Progreso: {self.current_file}/{self.total_files} archivos")
        
        if stage == 'writing':
            self.current_file += 1

def detectar_stack(path="."):
    """Detecta automáticamente el stack tecnológico del proyecto"""
    path = os.path.abspath(path)
    files = set()
    dirs = set()
    
    for root, dirnames, filenames in os.walk(path):
        # Solo revisar el primer nivel y algunos subdirectorios importantes
        level = root.replace(path, '').count(os.sep)
        if level > 2:
            continue
            
        for f in filenames:
            files.add(f.lower())
        for d in dirnames:
            dirs.add(d.lower())

    print(f"🔍 Detectando stack en {path}...")
    print(f"   📁 Directorios: {sorted(list(dirs))[:5]}...")
    print(f"   📄 Archivos: {sorted(list(files))[:5]}...")

    # Django
    if "manage.py" in files or "asgi.py" in files or "wsgi.py" in files:
        if "settings.py" in files or any("settings" in f for f in files):
            print("✅ Stack detectado: Django")
            return "django"

    # Flask
    if "app.py" in files or "wsgi.py" in files:
        req_files = [f for f in files if "requirements" in f or "pipfile" in f]
        for req_file in req_files:
            try:
                req_path = os.path.join(path, req_file)
                with open(req_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
                    if "flask" in content:
                        print("✅ Stack detectado: Flask")
                        return "flask"
            except:
                continue

    # React
    if "package.json" in files:
        try:
            pkg_path = os.path.join(path, "package.json")
            with open(pkg_path, encoding="utf-8") as f:
                pkg_content = f.read().lower()
                if "react" in pkg_content and ("src" in dirs or any("jsx" in f or "tsx" in f for f in files)):
                    print("✅ Stack detectado: React")
                    return "react"
        except:
            pass

    # Node.js (genérico/Express)
    if "package.json" in files:
        try:
            pkg_path = os.path.join(path, "package.json")
            with open(pkg_path, encoding="utf-8") as f:
                pkg_content = f.read().lower()
                if "express" in pkg_content or "fastify" in pkg_content or "node" in pkg_content:
                    print("✅ Stack detectado: Node.js")
                    return "node"
        except:
            pass

    # REST API (detectar por archivos OpenAPI/Swagger)
    api_indicators = ["openapi", "swagger", "postman"]
    for root, _, filenames in os.walk(path):
        for filename in filenames:
            if filename.lower().endswith(('.yaml', '.yml', '.json')):
                try:
                    filepath = os.path.join(root, filename)
                    with open(filepath, encoding="utf-8", errors="ignore") as f:
                        content = f.read().lower()
                        if any(indicator in content for indicator in api_indicators):
                            print("✅ Stack detectado: REST API")
                            return "restapi"
                except:
                    continue

    print("❓ Stack no detectado automáticamente")
    return None

def aplicar_filtros_stack(codigo, stack):
    """Aplica filtros de seguridad según el stack detectado"""
    if not stack or stack not in FILTERS_BY_STACK:
        return codigo
    
    codigo_filtrado = codigo
    aplicados = 0
    
    for patron, reemplazo in FILTERS_BY_STACK[stack]:
        nuevo_codigo = re.sub(patron, reemplazo, codigo_filtrado, flags=re.IGNORECASE | re.MULTILINE)
        if nuevo_codigo != codigo_filtrado:
            aplicados += 1
            codigo_filtrado = nuevo_codigo
    
    if aplicados > 0:
        print(f"   🔒 {aplicados} filtros de seguridad aplicados para {stack}")
    
    return codigo_filtrado

def crear_branch_documentacion(stack):
    """Crea una branch temporal para documentación"""
    try:
        # Verificar si estamos en un repo git
        subprocess.run(["git", "status"], check=True, capture_output=True)
        
        branch_name = f"doc-gen/{stack}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Crear y cambiar a la nueva branch
        subprocess.run(["git", "checkout", "-b", branch_name], check=True, capture_output=True)
        print(f"🌿 Branch temporal creada: {branch_name}")
        return branch_name
        
    except subprocess.CalledProcessError:
        print("⚠️ No se pudo crear branch (no es repo git o hay problemas)")
        return None

def log_gemini_response(review_dir, filename, response_data, tokens_used):
    """Guarda log de respuestas de Gemini"""
    log_path = os.path.join(review_dir, f"{filename}_review.log")
    
    try:
        with open(log_path, "a", encoding="utf-8") as log_file:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            response_id = response_data.get("responseId", "N/A")
            model_version = response_data.get("modelVersion", "N/A")
            
            log_file.write(f"{timestamp} | {response_id} | {tokens_used} tokens | {model_version}\n")
            
        print(f"   📝 Log guardado: {tokens_used} tokens utilizados")
    except Exception as e:
        print(f"   ⚠️ Error guardando log: {e}")

def hash_code(content):
    """Genera un hash SHA256 del contenido de un archivo."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def github_create_status(owner, repo, sha, state, description, context="Code Review Bot"):
    """Crea un status en GitHub para un commit SHA"""
    url = f"https://api.github.com/repos/{owner}/{repo}/statuses/{sha}"
    data = {
        "state": state,
        "description": description,
        "context": context
    }
    response = requests.post(url, json=data, headers=GITHUB_HEADERS)
    if response.status_code in [201, 200]:
        print(f"✅ Status creado: {state} para commit {sha}")
    else:
        print(f"⚠️ Error creando status: {response.status_code} {response.text}")

def get_latest_commit_sha(owner, repo, branch="main"):
    """Obtiene el SHA del último commit de la rama principal"""
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
    response = requests.get(url, headers=GITHUB_HEADERS)
    if response.status_code == 200:
        return response.json()["sha"]
    else:
        print(f"⚠️ Error obteniendo commit SHA: {response.status_code} {response.text}")
        return None

def count_python_files(repo_path):
    """Cuenta el total de archivos Python para el progreso"""
    count = 0
    for root, _, files in os.walk(repo_path):
        if any(ex in root for ex in EXCLUDE_PATHS):
            continue
        for f in files:
            if f.endswith(".py"):
                count += 1
    return count

def code_review_gemini(repo_path, owner, remote_url, stack_override=None):
    """Realiza code review usando Gemini AI con detección de stack y filtros de seguridad"""
    print(f"Resolved repo path: {os.path.abspath(repo_path)}")
    if not GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY no está configurada en .env")
        return

    # Detectar o usar stack override
    stack = stack_override or detectar_stack(repo_path)
    if not stack:
        print("⚠️ Stack no detectado. Usa --stack para especificar: django, flask, node, react, restapi")
        stack = "generic"
    
    print(f"🔧 Usando stack: {stack}")

    # Crear branch temporal para documentación
    temp_branch = crear_branch_documentacion(stack)

    repo_name = remote_url.rstrip("/").split("/")[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    review_dir = os.path.join(repo_path, "review")
    os.makedirs(review_dir, exist_ok=True)

    sha = get_latest_commit_sha(owner, repo_name)
    if not sha:
        print("⚠️ No se pudo obtener el SHA para crear status en GitHub.")
        return

    # Contar archivos para progreso
    total_files = count_python_files(repo_path)
    if total_files == 0:
        print("📄 No se encontraron archivos Python para revisar.")
        return
        
    print(f"🔍 Iniciando review de {total_files} archivos Python...")
    progress = ProgressTracker(total_files)

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }

    reviewed_count = 0

    for root, _, files in os.walk(repo_path):
        if any(ex in root for ex in EXCLUDE_PATHS):
            continue

        for f in files:
            if not f.endswith(".py"):
                continue

            filepath = os.path.join(root, f)
            rel_dir = os.path.relpath(root, repo_path).replace(os.sep, "_")
            review_filename = f"{rel_dir}_{f}_review.md"
            review_path = os.path.join(review_dir, review_filename)

            # Etapa 1: Leyendo archivo
            progress.update_file(f, 'reading')
            
            try:
                with open(filepath, "r", encoding="utf-8") as file:
                    code = file.read()
            except Exception as e:
                print(f"❌ Error leyendo {filepath}: {e}")
                progress.current_file += 1
                continue

            code_hash = hash_code(code)

            # Verificar si ya existe un review previo
            if os.path.exists(review_path):
                with open(review_path, "r", encoding="utf-8") as rf:
                    first_line = rf.readline().strip()
                    if first_line.startswith("<!-- hash:") and first_line.endswith("-->"):
                        old_hash = first_line.split(":")[1].split("-->")[0].strip()
                        if old_hash == code_hash:
                            print(f"✅ {f} sin cambios, agregando sello de revisión...")
                            with open(review_path, "a", encoding="utf-8") as rf_new:
                                rf_new.write(
                                    f"\n\n---\n✅ Sin cambios significativos - Última revisión {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                                )
                            github_create_status(owner, repo_name, sha, "success", f"Sin cambios en {f}")
                            progress.current_file += 1
                            continue

            if reviewed_count >= DAILY_LIMIT:
                print(f"⚠️ Límite diario de {DAILY_LIMIT} archivos alcanzado. Espera 24h para continuar.")
                return

            # Etapa 2: Procesando con Gemini
            progress.update_file(f, 'processing')

            # Aplicar filtros de seguridad según el stack
            clean_code = aplicar_filtros_stack(code, stack)
            
            # Limpiar el código y limitarlo para evitar tokens excesivos
            clean_code = clean_code.strip()
            if len(clean_code) > 3000:  # Limitar tamaño
                clean_code = clean_code[:3000] + "\n... (código truncado)"

            prompt = f"""Analiza este código {stack.upper()} y proporciona una revisión detallada:

```python
{clean_code}
```

CONTEXTO: Este es un proyecto {stack.upper()}.

Proporciona:
1. **Resumen**: ¿Qué hace este código?
2. **Funcionalidades principales**
3. **Arquitectura y patrones** (específicos para {stack})
4. **Posibles mejoras**
5. **Problemas de seguridad** (si los hay)
6. **Recomendaciones para {stack}**

Sé conciso pero completo."""

            data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ]
            }

            try:
                print(f"   📡 Enviando request a Gemini API...")
                response = requests.post(url, json=data, headers=headers, timeout=30)
                
                print(f"   📊 Status code: {response.status_code}")

                if response.status_code == 429:
                    try:
                        error_data = response.json()
                        retry_time = 60  # default
                        if "error" in error_data and "details" in error_data["error"]:
                            details = error_data["error"]["details"]
                            for detail in details:
                                if "retryDelay" in detail:
                                    retry_delay = detail["retryDelay"]
                                    retry_time = int(retry_delay.replace("s", ""))
                                    break
                    except:
                        retry_time = 60
                    
                    print(f"⚠️ Rate limit alcanzado. Esperando {retry_time} segundos...")
                    time.sleep(retry_time)
                    continue

                if response.status_code == 200:
                    try:
                        result = response.json()
                        print(f"   ✅ Response recibida de Gemini")
                        
                        # Extraer información de tokens para logging
                        usage_metadata = result.get("usageMetadata", {})
                        total_tokens = usage_metadata.get("totalTokenCount", 0)
                        
                        # Guardar log de respuesta
                        log_gemini_response(review_dir, f"{rel_dir}_{f}", result, total_tokens)
                        
                        # Etapa 3: Escribiendo review
                        progress.update_file(f, 'writing')
                        
                        candidates = result.get("candidates", [])
                        if not candidates:
                            print(f"   ⚠️ No se recibieron candidatos en la respuesta")
                            progress.current_file += 1
                            continue
                            
                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        
                        if not parts:
                            print(f"   ⚠️ No se recibió contenido en la respuesta")
                            progress.current_file += 1
                            continue
                        
                        review_text = parts[0].get("text", "").strip()
                        
                        if not review_text:
                            print(f"   ⚠️ Texto de review vacío")
                            progress.current_file += 1
                            continue
                        
                        with open(review_path, "w", encoding="utf-8") as md_file:
                            md_file.write(f"<!-- hash:{code_hash} -->\n")
                            md_file.write(f"<!-- stack:{stack} -->\n")
                            md_file.write(f"# 📋 Code Review: {f}\n\n")
                            md_file.write(f"**Archivo:** `{os.path.relpath(filepath, repo_path)}`\n")
                            md_file.write(f"**Stack:** {stack.upper()}\n")
                            md_file.write(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                            md_file.write(f"**Líneas de código:** {len(code.splitlines())}\n")
                            md_file.write(f"**Tokens utilizados:** {total_tokens}\n\n")
                            md_file.write("---\n\n")
                            md_file.write(review_text + "\n")
                            
                        print(f"   ✅ Review completado y guardado")
                        github_create_status(owner, repo_name, sha, "success", f"Code review generated for {f}")
                        reviewed_count += 1
                        
                    except Exception as e:
                        print(f"   ❌ Error procesando respuesta JSON: {e}")
                        print(f"   📄 Response content: {response.text[:200]}...")
                        progress.current_file += 1
                        
                else:
                    print(f"   ❌ Error HTTP {response.status_code}")
                    print(f"   📄 Response: {response.text[:200]}...")
                    progress.current_file += 1
                    
            except Exception as e:
                print(f"❌ Error en request para {f}: {e}")
                progress.current_file += 1

    print(f"\n🎉 Review completado! {reviewed_count} archivos procesados de {total_files} totales.")
    
    if temp_branch:
        print(f"🌿 Documentación generada en branch: {temp_branch}")
        print("   Para mergear: git checkout main && git merge", temp_branch)

def find_secrets_and_update_env(repo_path):
    """Busca patrones sospechosos en código y actualiza .env"""
    print("🔍 Buscando secretos y configuraciones sensibles...")
    
    suspicious_patterns = {
        "DATABASE_URL": r"database[_\-]?url\s*[:=]\s*[\"']?([^\"'\n]+)",
        "PASSWORD": r"password\s*[:=]\s*[\"']?([^\"'\n]+)",
        "USER": r"user(?:name)?\s*[:=]\s*[\"']?([^\"'\n]+)",
        "HOST": r"host\s*[:=]\s*[\"']?([^\"'\n]+)",
        "PORT": r"port\s*[:=]\s*[\"']?([^\"'\n]+)",
        "API_KEY": r"api[_\-]?key\s*[:=]\s*[\"']?([^\"'\n]+)",
        "SECRET": r"secret\s*[:=]\s*[\"']?([^\"'\n]+)"
    }
    
    secrets = {}
    files_scanned = 0

    for root, _, files in os.walk(repo_path):
        if any(ex in root for ex in EXCLUDE_PATHS):
            continue
        for file in files:
            if file.endswith((".py", ".js", ".env.example", ".env", ".yml", ".yaml")):
                filepath = os.path.join(root, file)
                files_scanned += 1
                
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    for key, pattern in suspicious_patterns.items():
                        matches = re.findall(pattern, content, re.I)
                        for match in matches:
                            if match and len(match) > 3:  # Evitar matches muy cortos
                                secrets[key] = match
                                
                except Exception as e:
                    print(f"⚠️ Error leyendo {filepath}: {e}")

    env_path = os.path.join(repo_path, ".env")
    if secrets:
        mode = "a" if os.path.exists(env_path) else "w"
        with open(env_path, mode) as env_file:
            env_file.write(f"\n# Secretos encontrados - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            for k, v in secrets.items():
                env_file.write(f"{k}={v}\n")

        print(f"✅ .env actualizado con {len(secrets)} variables encontradas.")
        print(f"📊 Archivos escaneados: {files_scanned}")
        for key in secrets.keys():
            print(f"  - {key}")
    else:
        print(f"📊 {files_scanned} archivos escaneados, no se encontraron secretos.")

def check_pull_requests():
    """Consulta PRs abiertas del usuario en GitHub"""
    if not GITHUB_TOKEN or not GITHUB_USERNAME:
        print("❌ Error: GITHUB_TOKEN o GITHUB_USERNAME no configurados en .env")
        return
        
    print(f"🔍 Consultando Pull Requests para {GITHUB_USERNAME}...")
    
    url = f"https://api.github.com/search/issues?q=is:pr+is:open+user:{GITHUB_USERNAME}"
    response = requests.get(url, headers=GITHUB_HEADERS)
    
    if response.status_code == 200:
        data = response.json()
        total_prs = data.get("total_count", 0)
        
        if total_prs == 0:
            print("✅ No tienes Pull Requests abiertas.")
            return
            
        print(f"📋 Tienes {total_prs} Pull Request(s) abiertas:")
        for i, pr in enumerate(data.get("items", [])[:10], 1):  # Mostrar máximo 10
            repo_name = pr['repository_url'].split("/")[-1]
            created = pr['created_at'][:10]  # Solo fecha
            print(f"  {i}. 📁 [{repo_name}] {pr['title']}")
            print(f"     👤 Por: {pr['user']['login']} | 📅 {created}")
            print(f"     🔗 {pr['html_url']}")
            print()
    else:
        print(f"❌ Error consultando PRs: {response.status_code} {response.text}")

def check_forks():
    """Consulta forks de los repositorios del usuario en GitHub"""
    if not GITHUB_TOKEN or not GITHUB_USERNAME:
        print("❌ Error: GITHUB_TOKEN o GITHUB_USERNAME no configurados en .env")
        return
        
    print(f"🔍 Consultando forks para {GITHUB_USERNAME}...")
    
    url = f"https://api.github.com/users/{GITHUB_USERNAME}/repos?per_page=100"
    response = requests.get(url, headers=GITHUB_HEADERS)
    
    if response.status_code == 200:
        repos = response.json()
        forked_repos = []
        
        for repo in repos:
            forks_count = repo.get("forks_count", 0)
            if forks_count > 0:
                forked_repos.append({
                    'name': repo['name'],
                    'forks': forks_count,
                    'stars': repo.get('stargazers_count', 0),
                    'language': repo.get('language', 'N/A'),
                    'url': repo['html_url']
                })
        
        if not forked_repos:
            print("✅ Ninguno de tus repositorios tiene forks.")
            return
            
        # Ordenar por número de forks
        forked_repos.sort(key=lambda x: x['forks'], reverse=True)
        
        print(f"🍴 Repositorios con forks ({len(forked_repos)}):")
        for repo in forked_repos:
            print(f"  📁 {repo['name']} ({repo['language']})")
            print(f"     🍴 {repo['forks']} forks | ⭐ {repo['stars']} stars")
            print(f"     🔗 {repo['url']}")
            print()
    else:
        print(f"❌ Error consultando repos: {response.status_code} {response.text}")

def auto_commit():
    """Función de auto-commit mejorada"""
    try:
        # Verificar si estamos en un repo git
        subprocess.run(["git", "status"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("❌ No estás en un repositorio Git válido.")
        return
    
    # Mostrar estado actual
    result = subprocess.run(["git", "status", "--porcelain"], 
                          capture_output=True, text=True)
    
    if not result.stdout.strip():
        print("✅ No hay cambios para commitear.")
        return
    
    print("📊 Cambios detectados:")
    for line in result.stdout.strip().split('\n'):
        status = line[:2]
        file = line[3:]
        status_emoji = "📝" if "M" in status else "➕" if "A" in status else "❓"
        print(f"  {status_emoji} {file}")
    
    mensaje = input("\n💬 Mensaje del commit: ").strip()
    if not mensaje:
        print("❌ Mensaje de commit requerido.")
        return
        
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", mensaje], check=True)
        print("✅ Commit realizado exitosamente.")
        
        push = input("🚀 ¿Hacer push? (s/n): ").lower().strip()
        if push in ['s', 'si', 'y', 'yes']:
            subprocess.run(["git", "push"], check=True)
            print("✅ Push realizado exitosamente.")
        else:
            print("📋 Push cancelado. Usa 'git push' cuando estés listo.")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en git: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="🤖 CodeReviewBot - Herramienta unificada de automatización",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python script.py --action review --repo ./mi-proyecto --owner miusuario --remote https://github.com/miusuario/mi-proyecto.git
  python script.py --action issue --repo ./mi-proyecto
  python script.py --action pull
  python script.py --action fork
  python script.py --action commit
        """
    )
    
    parser.add_argument("--repo", type=str, help="Ruta al repositorio local")
    parser.add_argument("--action", type=str, required=True,
                        choices=["review", "issue", "pull", "fork", "commit"],
                        help="Acción: review, issue, pull, fork, commit")
    parser.add_argument("--remote", type=str, help="URL remota del repositorio (para review)")
    parser.add_argument("--owner", type=str, help="Usuario dueño del repo (para review)")
    parser.add_argument("--stack", type=str, help="Stack tecnológico (opcional): django, flask, node, react, restapi")

    args = parser.parse_args()

    print(f"🤖 CodeReviewBot iniciado - Acción: {args.action}")
    
    # Validaciones
    if args.action in ["review", "issue"] and not args.repo:
        print("❌ Error: --repo es requerido para las acciones 'review' y 'issue'")
        return
    if args.action == "review" and (not args.remote or not args.owner):
        print("❌ Error: --remote y --owner son requeridos para la acción 'review'")
        return

    # Ejecutar acciones
    if args.action == "review":
        code_review_gemini(args.repo, args.owner, args.remote, args.stack)
    elif args.action == "issue":
        find_secrets_and_update_env(args.repo)
    elif args.action == "pull":
        check_pull_requests()
    elif args.action == "fork":
        check_forks()
    elif args.action == "commit":
        auto_commit()
    
    print("✅ Acción completada.")

if __name__ == "__main__":
    main()
