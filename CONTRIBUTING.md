# Guía de Contribución — SmartTrafficFlow AI

Esta guía define cómo trabajamos en equipo para mantener el código limpio, trazable y libre de conflictos.

---

## 1. Configuración inicial (solo la primera vez)

```bash
# 1. Clona el repositorio
git clone https://github.com/fpeirop/proyecto-ia-bigdata.git
cd proyecto-ia-bigdata

# 2. Crea y activa el entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. Instala dependencias de desarrollo
make install

# Esto instala también los hooks de pre-commit automáticamente.
# A partir de ahora, antes de cada commit se ejecutará black y ruff.
```

---

## 2. Flujo de trabajo Git

### Nunca trabajes directamente en `main` o `develop`.

```bash
# 1. Ponte al día con develop
git checkout develop
git pull origin develop

# 2. Crea tu rama de trabajo
git checkout -b feature/nombre-descriptivo

# Ejemplos de nombres de rama:
# feature/limpieza-datos-nulos
# feature/entrenamiento-xgboost
# feature/dashboard-mapa-sensores
# fix/correccion-split-temporal
# docs/actualizar-readme
```

### Trabaja, añade y commitea:

```bash
git add .
git commit -m "tipo: descripción corta y clara del cambio"
```

### Sube tu rama y abre un Pull Request hacia `develop`:

```bash
git push origin feature/nombre-descriptivo
# Luego ve a GitHub y abre el Pull Request
```

---

## 3. Convención de commits

Usa siempre el formato `tipo: descripción`:

| Tipo | Cuándo usarlo |
|---|---|
| `feat:` | Nueva funcionalidad |
| `fix:` | Corrección de error |
| `data:` | Cambios en datos o pipeline ETL |
| `model:` | Cambios en modelos ML |
| `docs:` | Documentación |
| `test:` | Tests |
| `refactor:` | Refactorización sin cambio funcional |
| `chore:` | Cambios de configuración, dependencias |

**Ejemplos buenos:**
```
feat: añadir feature engineering de variables temporales
fix: corregir lectura de sensores con valores nulos en columna ocupacion
data: filtrar sensores M-30 para subset de 300 elementos
model: entrenar XGBoost con horizonte t+30 y validación temporal
docs: añadir diagrama de arquitectura al README
test: añadir tests unitarios para el módulo de limpieza
```

**Ejemplos malos:**
```
fix cosas
actualizacion
cambios
```

---

## 4. Reglas del Pull Request

- Todo PR debe ir hacia `develop`, nunca hacia `main` directamente.
- El PR debe pasar el CI (lint + tests) en verde antes de mergear.
- Al menos un miembro del equipo debe revisar el PR antes de aprobarlo.
- El título del PR debe seguir la misma convención que los commits.
- Borra la rama después de mergear.

---

## 5. Qué NO subir al repositorio

- El fichero `.env` (contiene rutas y configuraciones locales)
- Los datos del MTD en `data/raw/` y `data/processed/` (son demasiado grandes)
- Modelos entrenados `.pkl` o `.joblib`
- Carpetas `__pycache__/`, `.pytest_cache/`, `venv/`
- Notebooks con outputs de celdas ejecutadas (limpiadlos antes)

Todo esto está cubierto por el `.gitignore`. Si algo grande se cuela por error, avisad antes de hacer push.

---

## 6. Pre-commit: qué hace automáticamente

Cada vez que ejecutas `git commit`, estos checks se ejecutan solos:

- **black**: formatea tu código automáticamente
- **ruff**: detecta errores de estilo y los corrige donde puede
- **isort**: ordena los imports
- **check-large-files**: te avisa si intentas subir un fichero > 5MB
- **no-commit-to-branch**: bloquea commits directos a `main` o `develop`

Si un hook falla, el commit se cancela y verás qué hay que arreglar.

---

## 7. Canal de comunicación

- **Telegram**: comunicación diaria
- **Teams** (martes y viernes 18–20h): reuniones de seguimiento
- **GitHub Issues**: para registrar tareas, bugs o decisiones técnicas
