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

import subprocess

mensaje = input("Mensaje del commit: ")
confirm = input("¿Hacer push? (s/n): ").lower()

subprocess.run(["git", "add", "."])
subprocess.run(["git", "commit", "-m", mensaje])

if confirm == "s":
    subprocess.run(["git", "push"])
else:
    print("Push cancelado.")

