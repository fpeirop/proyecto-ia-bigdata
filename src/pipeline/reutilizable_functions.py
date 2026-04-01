def extract_lat_lon(df, column):
    coords = df[column].str.extract(r"POINT \((-?\d+\.\d+) (-?\d+\.\d+)\)")
    coords.columns = [f"{column}_lon", f"{column}_lat"]
    return coords.astype(float)
