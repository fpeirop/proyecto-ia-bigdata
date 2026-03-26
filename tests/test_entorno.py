"""
Tests de humo — verifican que el entorno básico está correctamente configurado.
Ampliar con tests reales a medida que se desarrollen los módulos.
"""


def test_imports_basicos():
    """Verifica que las dependencias principales están instaladas."""
    import pandas as pd
    import numpy as np
    import sklearn

    assert pd.__version__ >= "2.0"
    assert np.__version__ >= "1.24"


def test_python_version():
    """Verifica que se está usando Python 3.11+."""
    import sys

    assert sys.version_info >= (3, 11), f"Se requiere Python 3.11+, tienes {sys.version}"


def test_estructura_datos(tmp_path):
    """Verifica que se pueden crear y leer ficheros CSV básicos."""
    import pandas as pd

    df = pd.DataFrame({"sensor_id": [1, 2, 3], "intensidad": [100, 150, 200]})
    ruta = tmp_path / "test.csv"
    df.to_csv(ruta, index=False)

    df_leido = pd.read_csv(ruta)
    assert len(df_leido) == 3
    assert "sensor_id" in df_leido.columns
    assert "intensidad" in df_leido.columns
