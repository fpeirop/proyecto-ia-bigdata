# ==============================================================================
# SmartTrafficFlow AI — Makefile
# Interfaz unificada de comandos para el equipo
# Uso: make <comando>
# ==============================================================================

.PHONY: help install install lint format test etl train app clean

# Mostrar ayuda por defecto
help:
	@echo ""
	@echo "  SmartTrafficFlow AI — Comandos disponibles"
	@echo "  ==========================================="
	@echo ""
	@echo "  Configuracion:"
	@echo "    make install      Instala dependencias de produccion"
	@echo ""
	@echo "  Calidad de codigo:"
	@echo "    make lint         Comprueba estilo con ruff y black"
	@echo "    make format       Formatea el codigo automaticamente con black"
	@echo ""
	@echo "  Testing:"
	@echo "    make test         Ejecuta todos los tests con pytest"
	@echo "    make test-cov     Ejecuta tests con reporte de cobertura"
	@echo ""
	@echo "  Pipeline:"
	@echo "    make etl          Ejecuta el pipeline de datos completo (ETL)"
	@echo "    make train        Entrena el modelo ML"
	@echo "    make predict      Genera predicciones con el modelo entrenado"
	@echo ""
	@echo "  Aplicacion:"
	@echo "    make app          Lanza el dashboard Streamlit en local"
	@echo ""
	@echo "  Limpieza:"
	@echo "    make clean        Elimina archivos temporales y cache"
	@echo ""

# ------------------------------------------------------------------------------
# Configuración del entorno
# ------------------------------------------------------------------------------

install:
	pip install --upgrade pip
	pip install -r environment/requirements.txt
	pre-commit install
	@echo ""
	@echo "  Entorno de desarrollo listo. Hooks de pre-commit instalados."
	@echo ""

# ------------------------------------------------------------------------------
# Calidad de código
# ------------------------------------------------------------------------------

lint:
	@echo ">> Ejecutando ruff..."
	ruff check src/ tests/
	@echo ">> Ejecutando black (modo comprobacion)..."
	black --check src/ tests/
	@echo ">> Todo correcto."

format:
	@echo ">> Formateando con black..."
	black src/ tests/
	@echo ">> Ordenando imports con isort..."
	isort src/ tests/
	@echo ">> Formato aplicado."

# ------------------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------------------

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
	@echo ">> Reporte HTML generado en htmlcov/index.html"

# ------------------------------------------------------------------------------
# Pipeline de datos y modelos
# ------------------------------------------------------------------------------

etl:
	@echo ">> Ejecutando pipeline ETL..."
	python src/pipeline/run_pipeline.py
	@echo ">> Pipeline completado. Datos procesados en data/processed/"

train:
	@echo ">> Entrenando modelo ML..."
	python src/models/train.py
	@echo ">> Modelo entrenado y guardado."

predict:
	@echo ">> Generando predicciones..."
	python src/models/predict.py
	@echo ">> Predicciones guardadas en data/predictions/"

# ------------------------------------------------------------------------------
# Aplicación web
# ------------------------------------------------------------------------------

app:
	@echo ">> Iniciando dashboard SmartTrafficFlow AI..."
	@echo ">> Abre http://localhost:8501 en tu navegador"
	streamlit run src/frontend/app.py

# ------------------------------------------------------------------------------
# Limpieza
# ------------------------------------------------------------------------------

clean:
	@echo ">> Limpiando archivos temporales..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	@echo ">> Limpieza completada."
