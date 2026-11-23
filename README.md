# Ingeniero

Ingeniero de pista para Assetto Corsa: lee tu setup `.ini`, te pregunta por el contexto
del circuito y tus sensaciones, diagnostica el balance y genera un setup nuevo validado
(`ENG_...`), sin tocar nunca tu archivo original.

## Requisitos

- Windows con Assetto Corsa instalado (Steam).
- Python 3.11+ y Node 18+.
- (Opcional) Ollama con un modelo 7-8B para redactar la explicación. La app funciona
  sin él, con una plantilla determinística.

## Arrancar

Doble clic en `start.bat`. La primera vez crea el entorno virtual, instala dependencias y
compila el frontend. Después abre `http://127.0.0.1:8000`.

Para desarrollo: `start-dev.bat` (backend con `--reload` y Vite en `:5173`).

## Uso

1. **Setup**: elegí el coche y el circuito, y un setup guardado (o pegá el `.ini`).
2. **Contexto**: seco/húmedo/mojado, tipo de sesión, vueltas objetivo, temperaturas, combustible.
3. **Sensaciones**: marcá los síntomas por fase (entrada/medio/salida) y velocidad, cargá
   temperaturas/presiones en caliente y tiempos de vuelta.
4. **Diagnóstico**: revisá los cambios propuestos, el plan de prueba y el diff del archivo.
   Guardá el setup nuevo (`ENG_...`) y, después de probarlo, registrá el resultado.

## Sesiones y AC en vivo

- **Sesiones**: desde un setup cargado creá una sesión. Cada análisis queda encadenado y el
  setup guardado pasa a ser la base del siguiente. Usá "Continuar sesión" para iterar
  rápidamente sin re-cargar todo.
- **Leer de AC**: con Assetto Corsa corriendo y en pista, el botón "📡 Leer de AC" llena
  coche, circuito, temperaturas, neumáticos, presiones, combustible y tiempos
  automáticamente desde la memoria compartida del juego.

## Principios

- Tu setup original nunca se modifica: siempre se escribe un archivo nuevo.
- El motor de reglas es determinístico y los cambios se clamped a los rangos declarados
  (o inferidos) del coche. La IA solo redacta, nunca inventa valores.
- Las unidades (clicks, escalas ×10, etc.) se infieren por coche.
- Se avisa si el preset de boxes (`.sp`) está desincronizado con el `.ini`.

## Estructura

- `backend/` — FastAPI, motor de reglas, SQLite.
- `frontend/` — React/Vite.
- `data/` — catálogo y base de datos local.
