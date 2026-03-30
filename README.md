[![CI — SmartTrafficFlow AI](https://github.com/fpeirop/proyecto-ia-bigdata/actions/workflows/ci.yml/badge.svg)](https://github.com/fpeirop/proyecto-ia-bigdata/actions/workflows/ci.yml)

# SmartTrafficFlow AI 🚦

> Sistema Predictivo de Congestión de Tráfico en Madrid mediante Big Data y Machine Learning

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![CI](https://github.com/fpeirop/proyecto-ia-bigdata/actions/workflows/ci.yml/badge.svg)](https://github.com/fpeirop/proyecto-ia-bigdata/actions/workflows/ci.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## Descripción

**SmartTrafficFlow AI** anticipa niveles de congestión en Madrid con **30–60 minutos de antelación**, utilizando datos históricos de sensores viales, variables meteorológicas y patrones temporales. El resultado se visualiza en un dashboard web interactivo pensado para conductores, logística urbana y gestores de movilidad.

- **Dataset:** Madrid Traffic Dataset (MTD) — 554 sensores, ~30 meses (jun 2022 – nov 2024)
- **Modelos:** Random Forest · XGBoost
- **Interfaz:** Dashboard Streamlit desplegado en Hugging Face Spaces

---

## Equipo

| Nombre | Rol | GitHub |
|---|---|---|
| Jokin Mel | Project Manager & ML Engineer | [@jokin](https://github.com/) |
| Donovan Alexis Yaguana | Data Engineer & BI Developer | [@donovan](https://github.com/) |
| Francisco Peiró | ML Engineer & MLOps | [@fpeirop](https://github.com/fpeirop) |
| Marcos Cobos | BI Developer & Platform Engineer | [@marcos](https://github.com/) |

---

## Estructura del repositorio

```
proyecto-ia-bigdata/
│
├── data/
│   ├── raw/                  # Datos originales del MTD (no se suben a Git)
│   ├── processed/            # Datos limpios listos para entrenar
│   └── predictions/          # Outputs del modelo
│
├── docs/                     # Documentación técnica y diagramas
│
├── environment/
│   ├── requirements.txt      # Dependencias de producción
│   └── environment.yml       # Entorno Conda (alternativa)
│
├── src/
│   ├── pipeline/             # ETL: ingesta, limpieza, feature engineering
│   ├── models/               # Entrenamiento, evaluación, inferencia
│   └── frontend/             # Dashboard Streamlit
│
├── tests/                    # Tests unitarios y de integración
│
├── .github/
│   └── workflows/
│       └── ci.yml            # GitHub Actions — CI automático
│
├── .gitignore
├── .pre-commit-config.yaml   # Hooks de calidad de código
├── Makefile                  # Comandos unificados del proyecto
├── pyproject.toml            # Configuración de herramientas (black, ruff, etc.)
└── README.md
```

---

## Instalación rápida

### Requisitos previos
- Python 3.11+
- Git

### 1. Clonar el repositorio

```bash
git clone https://github.com/fpeirop/proyecto-ia-bigdata.git
cd proyecto-ia-bigdata
```

### 2. Crear y activar el entorno virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r environment/requirements.txt
```

### 4. Instalar hooks de pre-commit

```bash
pre-commit install
```

---

## Comandos disponibles (Makefile)

```bash
make install      # Instala todas las dependencias
make lint         # Ejecuta ruff y black (comprobación de estilo)
make format       # Formatea el código con black
make test         # Ejecuta todos los tests con pytest
make etl          # Ejecuta el pipeline de datos completo
make train        # Entrena el modelo
make app          # Lanza el dashboard en local (Streamlit)
make clean        # Limpia archivos temporales y caché
```

---

## Flujo de trabajo Git

Seguimos **Git Flow** con las siguientes ramas:

| Rama | Propósito |
|---|---|
| `main` | Código estable y listo para entrega. **Nunca push directo.** |
| `develop` | Integración continua del equipo |
| `feature/nombre` | Desarrollo de funcionalidades específicas |

**Convención de commits:**

```
feat: añadir feature engineering de variables temporales
fix: corregir lectura de sensores con valores nulos
data: actualizar subset MTD a 300 sensores
docs: actualizar README con instrucciones de instalación
test: añadir tests para el pipeline de limpieza
```

**Flujo habitual:**

```bash
git checkout develop
git pull origin develop
git checkout -b feature/mi-tarea
# ... trabajar ...
git add .
git commit -m "feat: descripción clara del cambio"
git push origin feature/mi-tarea
# Abrir Pull Request hacia develop en GitHub
```

---

## Arquitectura del sistema

```
[MTD Dataset CSV] → [Pipeline ETL] → [Feature Engineering]
                                              ↓
                                    [Modelo ML: XGBoost/RF]
                                              ↓
                              [Dashboard Streamlit / FastAPI]
                                              ↓
                                     [Usuario final]
```

---

## Variables de entorno

Copia el fichero `.env.example` a `.env` y rellena los valores:

```bash
cp .env.example .env
```

El fichero `.env` **nunca** se sube al repositorio (está en `.gitignore`).

---

## Métricas objetivo

| Métrica | Objetivo |
|---|---|
| MAE (t+30 min) | < 15 veh/hora |
| RMSE (t+30 min) | < 25 veh/hora |
| R² | > 0.80 |

---

## Licencia

MIT License — ver [LICENSE](LICENSE) para más detalles.
