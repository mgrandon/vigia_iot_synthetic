# Vigía IoT — Mantención Predictiva de Conectividad para Sensores Críticos

Modelo predictivo que anticipa la pérdida de conectividad en redes IoT industriales — aplicado a un caso piloto de faenas mineras chilenas (redes LTE/5G privadas para monitoreo de taludes, tranques de relave y flota autónoma).

**A diferencia de un dashboard reactivo** (que muestra fallas después de que ocurrieron), Vigía identifica con semanas de anticipación qué sensores están entrando en zona de riesgo — permitiendo programar mantención antes de perder visibilidad de infraestructura crítica.

🔗 **Demo interactivo:** [ver demo](vigia_iot_demo.html) *(o vía GitHub Pages una vez publicado)*

---

## El problema

La industria manufacturera pierde en promedio **USD 50 mil millones al año** en downtime no planificado. Los sistemas de monitoreo IoT actuales (incluyendo plataformas de electromovilidad y minería ya en uso en Chile) son en su mayoría **reactivos**: alertan cuando el dispositivo ya perdió conexión, no antes.

## El hallazgo del piloto

En una red simulada de 600 sensores IoT distribuidos en 3 zonas de una faena minera (tranque de relaves, rajo/flota, planta), monitoreados durante 120 días:

| Métrica | Valor |
|---|---|
| Sensores simulados | 600 |
| % tiempo global sin señal | 0.73% |
| Batería final — hardware industrial | 77.9% |
| Batería final — hardware consumidor | 9.2% |
| Día de cruce crítico (consumidor, <20% batería) | Día 96 de 120 |

**El hardware de menor costo entra en zona de riesgo ~24 días antes del final de la ventana simulada** — una ventana real de acción que un dashboard reactivo no ofrece.

## Metodología

- **Generación sintética con continuidad espacial:** campo de interferencia simulado con filtro gaussiano (mismo enfoque que un variograma simplificado), no ruido punto a punto.
- **Modelo de falla de hardware:** curva de bañera (Weibull, shape=2.2) — el riesgo de falla aumenta progresivamente con el tiempo de uso, no es constante (estándar real de ingeniería de confiabilidad).
- **Calibración con referencias públicas:**
  - PDR base: 96.4% (estudio académico de redes de sensores industriales)
  - MTBF hardware industrial: ≥50,000h vs. consumidor: ~20,000h
  - Degradación de batería calibrada con caso real documentado (promesa de 3 años vs. ~4 meses en ambientes hostiles)
  - Costo de downtime: referencia Deloitte (industria manufacturera)

## Datos

100% sintéticos — no representan información de ninguna operación minera real. El objetivo es demostrar la metodología sin comprometer información confidencial de ningún cliente.

## Autor

Manuel Grandón Troncoso — Consultor independiente, Machine Learning aplicado a minería e IoT industrial.

📧 manuel.grandon@gmail.com
🔗 www.linkedin.com/in/manuel-enrique-grandón-troncoso-0592337
