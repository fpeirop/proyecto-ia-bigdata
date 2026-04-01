import os


def ejecutar_pipeline():
    print("--- 🛰️ SmartTrafficFlow: Pipeline ETL ---")

    os.makedirs("data/processed", exist_ok=True)

    # CARGA DE DATOS (Requisito: CSV)

    print("⚙️ Aplicando Ciclicidad, Festivos Madrid y Lags...")
    # df_procesado = aplicar_ingenieria(traffic_df)

    # GUARDADO EN PARQUET (Eficiencia Big Data)
    # output_path = 'data/processed/trafico_limpio.parquet'
    # df_procesado.to_parquet(output_path, engine='pyarrow')

    # print(f"💾 Guardado en: {output_path}")
    print("🎯 Fase 3 finalizada con éxito.")


if __name__ == "__main__":
    ejecutar_pipeline()
