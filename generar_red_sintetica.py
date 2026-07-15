"""
generar_red_sintetica.py
=========================
Genera una red IoT sintética de una faena minera (tranque de relaves,
rajo/flota, planta) con sensores de distinto tipo y grado de hardware,
y simula su telemetría de conectividad a lo largo del tiempo.

Objetivo: dataset base para detección PROACTIVA de riesgo de
degradación de conectividad — mantención programada por trayectoria
de batería/hardware, en vez de alertas reactivas post-falla (tipo
dashboard tradicional que solo muestra el estado actual).

Calibración (fuentes públicas, ver documentación técnica del proyecto):
  - PDR base                 : 96.4%  (estudio académico WSN industrial)
  - MTBF hardware industrial : 50,000+ h  (routers grado industrial, -40°C)
  - MTBF hardware consumidor : ~20,000 h  (3-5x más fallas)
  - Degradación de batería   : promesa 3 años -> caso real 4 meses en
                                ambientes hostiles (piloto industrial real)
  - Objetivo de reliability  : >99.999% (estándar industrial IoT crítico)

Modelo de fallas de hardware: curva de bañera (Weibull, shape=2.2),
NO probabilidad constante — el riesgo aumenta gradualmente a medida
que el sensor se acerca a su MTBF (estándar real de ingeniería de
confiabilidad), dejando salud_hw como indicador líder expuesto.

Autor: Manuel | Proyecto: Vigía IoT (iot_reliability_synthetic)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy.ndimage import gaussian_filter
import warnings
warnings.filterwarnings('ignore')

rng = np.random.default_rng(42)

# ─── CONFIGURACIÓN DEL SITIO ────────────────────────────────────────────────
OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SITE_SIZE_X = 8000
SITE_SIZE_Y = 6000

ZONAS = {
    'tranque_relaves': {'centro': (1200, 4800), 'radio': 900,  'criticidad': 3, 'n_sensores': 150},
    'rajo_flota':      {'centro': (4500, 3000), 'radio': 2200, 'criticidad': 2, 'n_sensores': 300},
    'planta':          {'centro': (6800, 1200), 'radio': 600,  'criticidad': 2, 'n_sensores': 150},
}

ANTENAS = np.array([
    [1000, 4500], [1500, 5200],
    [3500, 2500], [4200, 3600], [5200, 2800], [5800, 3800],
    [6600, 1000], [7000, 1500],
])

N_DIAS = 120
FREC_HORAS = 1
N_TIMESTEPS = N_DIAS * 24 // FREC_HORAS

def generar_sensores():
    registros = []
    sid = 0
    for zona, cfg in ZONAS.items():
        cx, cy = cfg['centro']
        for _ in range(cfg['n_sensores']):
            ang = rng.uniform(0, 2 * np.pi)
            r = cfg['radio'] * np.sqrt(rng.uniform(0, 1))
            x = cx + r * np.cos(ang)
            y = cy + r * np.sin(ang)
            tipo = {'tranque_relaves': 'talud', 'rajo_flota': 'flota', 'planta': 'fijo'}[zona]
            grado = 'industrial' if rng.random() < 0.7 else 'consumidor'
            registros.append({
                'sensor_id': f"S{sid:04d}", 'zona': zona, 'tipo_sensor': tipo,
                'grado_hw': grado, 'x': x, 'y': y, 'criticidad': cfg['criticidad'],
            })
            sid += 1
    return pd.DataFrame(registros)

def distancia_antena_mas_cercana(x, y):
    d = np.sqrt((ANTENAS[:, 0] - x) ** 2 + (ANTENAS[:, 1] - y) ** 2)
    return d.min()

def simular_campo_interferencia(nx=80, ny=60, sigma=6):
    campo = rng.standard_normal((nx, ny))
    campo = gaussian_filter(campo, sigma=sigma)
    campo = (campo - campo.min()) / (campo.max() - campo.min())
    return campo

def muestrear_campo(campo, x, y):
    nx, ny = campo.shape
    ix = int(np.clip(x / SITE_SIZE_X * nx, 0, nx - 1))
    iy = int(np.clip(y / SITE_SIZE_Y * ny, 0, ny - 1))
    return campo[ix, iy]

def calcular_senal_base(df):
    campo_interf = simular_campo_interferencia()
    dist = df.apply(lambda r: distancia_antena_mas_cercana(r['x'], r['y']), axis=1)
    interf = df.apply(lambda r: muestrear_campo(campo_interf, r['x'], r['y']), axis=1)
    senal_distancia = np.clip(1 - dist / 3500, 0.05, 1.0)
    senal_base = senal_distancia * (1 - 0.4 * interf)
    df = df.copy()
    df['dist_antena_m'] = dist.round(1)
    df['senal_base'] = senal_base.round(4)
    df['interferencia_terreno'] = interf.round(4)
    return df

def asignar_mtbf(df):
    df = df.copy()
    mtbf_base = np.where(df['grado_hw'] == 'industrial', 50000, 20000)
    mult_exposicion = 1.0 - 0.15 * (df['criticidad'] - 1)
    ruido_unidad = rng.uniform(0.8, 1.2, len(df))
    df['mtbf_horas'] = (mtbf_base * mult_exposicion * ruido_unidad).round(0)
    return df

def simular_curva_bateria(n_sensores, n_timesteps, grado_hw):
    vida_real_media_h = np.where(grado_hw == 'industrial', 14000, 2920)
    horas = np.arange(n_timesteps) * FREC_HORAS
    bateria = np.zeros((n_sensores, n_timesteps))
    for i in range(n_sensores):
        vida_individual = rng.normal(vida_real_media_h[i], vida_real_media_h[i] * 0.25)
        vida_individual = max(vida_individual, 500)
        curva = np.clip(100 * (1 - horas / vida_individual), 0, 100)
        ruido = rng.normal(0, 1.5, n_timesteps)
        bateria[i] = np.clip(curva + ruido, 0, 100)
    return bateria

def simular_eventos_shock(n_timesteps, prob_evento_dia=0.004):
    dias = n_timesteps // 24
    eventos = rng.random(dias) < prob_evento_dia
    shock = np.ones(n_timesteps)
    for d in np.where(eventos)[0]:
        duracion_h = rng.integers(2, 48)
        inicio = d * 24 + rng.integers(0, 24)
        fin = min(inicio + duracion_h, n_timesteps)
        shock[inicio:fin] = 0.05
    return shock

def simular_telemetria(df_sensores):
    n = len(df_sensores)
    print(f"► Simulando telemetría: {n} sensores x {N_TIMESTEPS} timesteps ({N_TIMESTEPS*n:,} registros)...")
    bateria = simular_curva_bateria(n, N_TIMESTEPS, df_sensores['grado_hw'].values)
    registros = []
    for zona in ZONAS:
        idx_zona = df_sensores.index[df_sensores['zona'] == zona].tolist()
        shock_zona = simular_eventos_shock(N_TIMESTEPS)
        for i in idx_zona:
            row = df_sensores.loc[i]
            senal_base = row['senal_base']
            mtbf_h = row['mtbf_horas']
            ruido_senal = rng.normal(0, 0.05, N_TIMESTEPS)
            factor_bateria = np.where(bateria[i] < 20, 0.5 + 0.5 * bateria[i] / 20, 1.0)
            shape = 2.2
            t_horas = np.arange(N_TIMESTEPS) * FREC_HORAS
            salud_hw = np.exp(-((t_horas / mtbf_h) ** shape))
            hazard_t = (shape / mtbf_h) * (t_horas / mtbf_h) ** (shape - 1)
            prob_falla_hw = 1 - np.exp(-hazard_t * FREC_HORAS)
            falla_hw = (rng.random(N_TIMESTEPS) < prob_falla_hw).astype(float)
            falla_hw_acumulada = np.maximum.accumulate(falla_hw)
            senal_t = (senal_base + ruido_senal) * factor_bateria * shock_zona * (1 - falla_hw_acumulada)
            senal_t = np.clip(senal_t, 0, 1)
            pdr_t = np.clip(0.964 * senal_t / max(senal_base, 0.05) + rng.normal(0, 0.02, N_TIMESTEPS), 0, 1)
            sin_senal = (senal_t < 0.15).astype(int)
            for t in range(N_TIMESTEPS):
                registros.append((row['sensor_id'], t, senal_t[t], round(bateria[i, t], 2),
                                   round(pdr_t[t], 4), sin_senal[t], round(salud_hw[t], 4)))
    df_tel = pd.DataFrame(registros, columns=['sensor_id','timestep','senal','bateria_pct','pdr','sin_senal','salud_hw'])
    return df_tel

def main():
    print("=" * 60)
    print("GENERADOR DE RED IoT SINTÉTICA — FAENA MINERA — Vigía IoT")
    print("=" * 60)
    df_sensores = generar_sensores()
    print(f"► Sensores generados: {len(df_sensores)} ({dict(df_sensores['zona'].value_counts())})")
    df_sensores = calcular_senal_base(df_sensores)
    df_sensores = asignar_mtbf(df_sensores)
    df_sensores.to_csv(OUTPUT_DIR / "sensores_metadata.csv", index=False)
    print(f"► Metadata guardada: {OUTPUT_DIR / 'sensores_metadata.csv'}")
    df_telemetria = simular_telemetria(df_sensores)
    df_telemetria.to_csv(OUTPUT_DIR / "telemetria_sintetica.csv", index=False)
    print(f"► Telemetría guardada: {OUTPUT_DIR / 'telemetria_sintetica.csv'} ({len(df_telemetria):,} filas)")
    print(f"\n{'='*60}\nRESUMEN\n{'='*60}")
    print(f"Sensores totales      : {len(df_sensores)}")
    print(f"Timesteps simulados   : {N_TIMESTEPS} ({N_DIAS} días, cada {FREC_HORAS}h)")
    print(f"% tiempo sin señal    : {df_telemetria['sin_senal'].mean():.2%}")
    print(f"Batería final promedio: {df_telemetria.groupby('sensor_id')['bateria_pct'].last().mean():.1f}%")
    print(f"PDR promedio          : {df_telemetria['pdr'].mean():.2%}")
    por_zona = df_telemetria.merge(df_sensores[['sensor_id','zona']], on='sensor_id')
    print(f"\n% tiempo sin señal por zona:")
    for zona, grp in por_zona.groupby('zona'):
        print(f"  {zona:<18}: {grp['sin_senal'].mean():.2%}")

if __name__ == "__main__":
    main()
