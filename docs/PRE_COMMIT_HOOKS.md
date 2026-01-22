# Pre-commit Hooks

Este proyecto usa [pre-commit](https://pre-commit.com/) para mantener la calidad del código mediante hooks de git automáticos.

## ¿Qué son los hooks?

Los hooks son scripts que se ejecutan automáticamente antes de hacer commits o push. Esto nos ayuda a:

- **Mantener calidad consistente**: Formato automático del código
- **Prevenir errores**: Validación de tipos y linting antes de commit
- **Seguridad**: Detección de claves privadas accidentales
- **Ahorrar tiempo**: Detectar problemas antes de code review

## Hooks configurados

### Pre-commit (antes de cada commit)

1. **Verificaciones generales**:
   - Eliminar espacios en blanco al final de líneas
   - Agregar línea vacía al final de archivos
   - Validar YAML, JSON, TOML
   - Detectar archivos grandes (>1MB)
   - Detectar claves privadas

2. **Formateo de código**:
   - **Black**: Formateo automático de Python
   - **isort**: Ordenamiento de imports

3. **Linting**:
   - **Ruff**: Linter rápido de Python (reemplaza flake8, pylint)
   - **mypy**: Verificación de tipos estáticos

4. **Seguridad**:
   - **Bandit**: Análisis de seguridad de código Python

## Instalación

Los hooks se instalan automáticamente con `make setup`, pero también puedes:

```bash
# Instalar manualmente
make hooks-install

# O directamente con pre-commit
source .venv/bin/activate
pre-commit install
```

## Uso diario

Una vez instalados, los hooks se ejecutan **automáticamente** al hacer commit:

```bash
git add .
git commit -m "feat: add new feature"
# ⬆️ Los hooks se ejecutan aquí automáticamente
```

Si un hook falla:
1. Revisa los errores mostrados
2. Algunos hooks **auto-arreglan** el código (black, isort, ruff)
3. Vuelve a hacer `git add .` para agregar las correcciones
4. Intenta el commit nuevamente

## Comandos útiles

```bash
# Ejecutar todos los hooks manualmente en todos los archivos
make hooks-run

# Ejecutar hooks en archivos específicos
pre-commit run --files packages/agent_config/schemas.py

# Actualizar versiones de hooks
make hooks-update

# Saltar hooks temporalmente (NO RECOMENDADO)
git commit -m "mensaje" --no-verify

# Desinstalar hooks
make hooks-uninstall
```

## Configuración

La configuración está en `.pre-commit-config.yaml`. Puedes:

- Agregar o remover hooks
- Cambiar versiones de herramientas
- Modificar argumentos de comandos
- Excluir archivos o directorios

## Resolución de problemas

### "pre-commit command not found"

```bash
source .venv/bin/activate
pip install pre-commit
pre-commit install
```

### Hooks muy lentos

La primera ejecución es lenta porque descarga las herramientas. Las siguientes son rápidas por caching.

### Quiero saltar un hook específico

Edita `.pre-commit-config.yaml` y comenta el hook que quieres desactivar.

### Necesito hacer un commit urgente

```bash
# Solo en emergencias - NO es buena práctica
git commit -m "mensaje" --no-verify
```

## Mejores prácticas

1. **No saltes los hooks**: Están para ayudarte, no para molestarte
2. **Revisa los cambios auto-aplicados**: Black/isort pueden reformatear tu código
3. **Actualiza los hooks**: `make hooks-update` regularmente
4. **Lee los errores**: Los mensajes de error suelen ser claros sobre qué arreglar

## Herramientas incluidas

- [pre-commit](https://pre-commit.com/) - Framework de git hooks
- [black](https://black.readthedocs.io/) - Formateo de código Python
- [isort](https://pycqa.github.io/isort/) - Ordenamiento de imports
- [ruff](https://docs.astral.sh/ruff/) - Linter ultra-rápido de Python
- [mypy](https://mypy.readthedocs.io/) - Verificación de tipos estáticos
- [bandit](https://bandit.readthedocs.io/) - Análisis de seguridad
