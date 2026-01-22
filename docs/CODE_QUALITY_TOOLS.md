# Herramientas de Calidad de Código

Este proyecto utiliza múltiples herramientas para garantizar alta calidad, seguridad y mantenibilidad del código.

## 🛠️ Herramientas Integradas

### Formateo Automático

**Black** - Formateo de código Python
- ✅ Configurado en pre-commit
- Formatea automáticamente al hacer commit
- Línea máxima: 100 caracteres
- Estilo consistente sin discusiones

**isort** - Ordenamiento de imports
- ✅ Configurado en pre-commit
- Organiza imports automáticamente
- Compatible con Black
- Agrupa: stdlib, third-party, local

### Linting y Análisis Estático

**Ruff** - Linter ultra-rápido
- ✅ Configurado en pre-commit
- 10-100x más rápido que flake8
- Combina múltiples herramientas (flake8, pylint, etc.)
- Auto-corrección de errores comunes

**Flake8** - Análisis de complejidad
- ✅ Configurado en pre-commit
- Complejidad ciclomática máxima: 10
- Plugins adicionales:
  - `flake8-docstrings`: Valida docstrings
  - `flake8-bugbear`: Detecta bugs comunes
  - `flake8-comprehensions`: Mejora comprehensions
  - `flake8-simplify`: Sugiere simplificaciones

**mypy** - Verificación de tipos
- ✅ Configurado en pre-commit
- Modo strict activado
- Type hints obligatorios
- Detecta errores de tipos antes de runtime

### Seguridad

**Bandit** - Análisis de seguridad
- ✅ Configurado en pre-commit
- Detecta vulnerabilidades comunes:
  - SQL injection
  - Command injection
  - Hardcoded passwords
  - Weak crypto
  - XSS vulnerabilities

### Calidad de Documentación

**pydocstyle** - Validación de docstrings
- ✅ Configurado en pre-commit
- Convención: Google style
- Verifica que clases y funciones públicas tengan docs
- Excluye tests y scripts

### Testing

**pytest** - Framework de testing
- ✅ Configurado en pre-commit
- Hooks:
  - Pre-commit: Tests unitarios rápidos
  - Pre-push: Tests completos con coverage
- Coverage mínimo requerido: 80%

**pytest-cov** - Cobertura de código
- ✅ Integrado con pytest
- Reportes en terminal y HTML
- Falla si coverage < 80%

## 📊 Ejecución de Herramientas

### Automático (con git hooks)

```bash
# Pre-commit (al hacer commit)
git commit -m "mensaje"
# Ejecuta: black, isort, ruff, mypy, bandit, pydocstyle, flake8, pytest-quick

# Pre-push (al hacer push)
git push
# Ejecuta todo lo anterior + pytest con coverage completo
```

### Manual

```bash
# Formateo
make format

# Linting
make lint

# Tests
make test

# Tests con coverage
make test-cov

# Todos los hooks manualmente
make hooks-run

# Solo verificar sin modificar
source .venv/bin/activate
black --check packages/ tests/
isort --check-only packages/ tests/
ruff check packages/ tests/
mypy packages/
```

## 🎯 Métricas de Calidad Actuales

- ✅ **79/79 tests** pasando (100%)
- ✅ **Cobertura**: >80% requerido
- ✅ **Type coverage**: 100% (mypy strict)
- ✅ **Complejidad**: <10 por función
- ✅ **Seguridad**: 0 vulnerabilidades detectadas

## 🚀 Herramientas Adicionales Recomendadas

### 1. **SonarQube / SonarCloud** ⭐⭐⭐⭐⭐
**Análisis de calidad completo**
- Detecta bugs, vulnerabilidades, code smells
- Métricas de mantenibilidad
- Integración con CI/CD
- Dashboard web con tendencias

**Cómo integrar:**
```bash
# Opción 1: SonarCloud (gratuito para proyectos públicos)
pip install sonar-scanner
# Agregar sonar-project.properties

# Opción 2: SonarQube local con Docker
docker run -d --name sonarqube -p 9000:9000 sonarqube:latest
```

**Configuración recomendada:**
```properties
# sonar-project.properties
sonar.projectKey=konko-agent
sonar.sources=packages
sonar.tests=tests
sonar.python.coverage.reportPaths=coverage.xml
sonar.python.version=3.10
```

### 2. **Radon** ⭐⭐⭐⭐
**Métricas de complejidad**
- Complejidad ciclomática
- Complejidad cognitiva
- Índice de mantenibilidad
- Líneas de código

```bash
pip install radon

# Complejidad ciclomática
radon cc packages/ -a

# Índice de mantenibilidad
radon mi packages/

# Raw metrics
radon raw packages/
```

### 3. **Vulture** ⭐⭐⭐⭐
**Detección de código muerto**
- Encuentra código no utilizado
- Variables, funciones, clases sin usar
- Imports innecesarios

```bash
pip install vulture

# Buscar código muerto
vulture packages/ --min-confidence 80
```

### 4. **Safety** ⭐⭐⭐⭐⭐
**Verificación de dependencias vulnerables**
- Escanea requirements
- Base de datos de CVEs
- Alertas de seguridad

```bash
pip install safety

# Verificar dependencias
safety check

# Agregar al pre-commit:
# - repo: https://github.com/Lucas-C/pre-commit-hooks-safety
#   rev: v1.3.2
#   hooks:
#     - id: python-safety-dependencies-check
```

### 5. **Pylint** ⭐⭐⭐
**Linter tradicional (ya cubierto por Ruff)**
- Más lento pero más completo que Ruff
- Solo si necesitas análisis específicos

```bash
pip install pylint

# Ejecutar
pylint packages/
```

### 6. **Semgrep** ⭐⭐⭐⭐⭐
**Análisis de seguridad avanzado**
- Patrones personalizados
- Reglas de la comunidad
- Más preciso que Bandit

```bash
pip install semgrep

# Escanear con reglas automáticas
semgrep --config=auto packages/

# Reglas específicas de Python
semgrep --config "p/python" packages/
```

### 7. **Interrogate** ⭐⭐⭐
**Coverage de documentación**
- Mide % de código documentado
- Complementa pydocstyle

```bash
pip install interrogate

# Verificar coverage de docs
interrogate -v packages/

# Con badge
interrogate --generate-badge .
```

### 8. **Pyupgrade** ⭐⭐⭐⭐
**Moderniza sintaxis de Python**
- Actualiza a sintaxis moderna
- Compatible con pre-commit

```bash
pip install pyupgrade

# Agregar a .pre-commit-config.yaml:
# - repo: https://github.com/asottile/pyupgrade
#   rev: v3.15.0
#   hooks:
#     - id: pyupgrade
#       args: [--py310-plus]
```

### 9. **Liccheck** ⭐⭐⭐
**Verificación de licencias**
- Verifica licencias de dependencias
- Previene problemas legales

```bash
pip install liccheck

# Verificar licencias
liccheck
```

### 10. **CodeClimate / Codacy** ⭐⭐⭐⭐
**Plataformas de análisis continuo**
- Análisis automático en PRs
- Métricas históricas
- Badges para README

## 📝 Configuración CI/CD Recomendada

### GitHub Actions Example

```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run pre-commit
        run: pre-commit run --all-files

      - name: Run tests with coverage
        run: pytest --cov=packages --cov-report=xml

      - name: SonarCloud Scan
        uses: SonarSource/sonarcloud-github-action@master
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}

      - name: Safety check
        run: safety check

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 🎯 Roadmap de Calidad

### Fase 1: ✅ Implementado
- [x] Black (formateo)
- [x] isort (imports)
- [x] Ruff (linting)
- [x] mypy (tipos)
- [x] Bandit (seguridad)
- [x] pytest + coverage
- [x] pydocstyle (docs)
- [x] flake8 (complejidad)

### Fase 2: 🚧 Próximos pasos
- [ ] SonarCloud integración
- [ ] Safety check en CI/CD
- [ ] Radon para métricas
- [ ] Semgrep rules personalizadas
- [ ] GitHub Actions workflow

### Fase 3: 🔮 Futuro
- [ ] Mutation testing (mutmut)
- [ ] Property-based testing (Hypothesis avanzado)
- [ ] Performance profiling
- [ ] Dependency scanning automático

## 💡 Mejores Prácticas

1. **No saltes los hooks**: Te ahorran tiempo a largo plazo
2. **Revisa los reportes**: Aprende de los errores detectados
3. **Mantén coverage alto**: Mínimo 80%, ideal 90%+
4. **Documenta el código público**: Classes, funciones, módulos
5. **Usa type hints**: Ayudan a detectar errores temprano
6. **Actualiza dependencias**: `make hooks-update` regularmente

## 🔧 Troubleshooting

### "Too many errors to fix"

```bash
# Formatear todo el código
make format

# Correr hooks en lotes
pre-commit run black --all-files
pre-commit run isort --all-files
# ... uno por uno
```

### "Quiero ver solo errores, no warnings"

```bash
# Ruff solo errores
ruff check --select E,F packages/

# Flake8 solo errores
flake8 --select=E,F packages/
```

### "Hooks muy lentos"

```bash
# Desactiva temporalmente los más lentos
# Edita .pre-commit-config.yaml y comenta:
# - mypy (lento en primera ejecución)
# - pytest-coverage (solo para push)
```

## 📚 Referencias

- [Pre-commit](https://pre-commit.com/)
- [Ruff](https://docs.astral.sh/ruff/)
- [Black](https://black.readthedocs.io/)
- [mypy](https://mypy.readthedocs.io/)
- [Bandit](https://bandit.readthedocs.io/)
- [SonarQube](https://www.sonarqube.org/)
