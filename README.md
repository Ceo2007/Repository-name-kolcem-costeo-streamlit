# Kolcem - Cockpit Gerencial de Costeo de Cemento

Aplicación Streamlit para análisis gerencial de costeo de cemento a partir del archivo Excel operativo.

## Archivos del proyecto

- `app.py`: aplicación principal Streamlit.
- `requirements.txt`: dependencias necesarias para Streamlit Cloud.
- `.streamlit/config.toml`: tema visual y configuración de carga.
- `.gitignore`: evita subir archivos locales o información sensible.

## Fuente de datos esperada

La app espera que el usuario cargue un archivo Excel `.xlsm` o `.xlsx` con una hoja llamada `Consolidado`.

Estructura requerida de `Consolidado`:

| Producción | Indice | Concepto/Observacion | Valor | Mes | Año | MesNro |
|---|---|---|---:|---|---:|---:|

La app también puede leer la hoja opcional `Metas Gerenciales`.

## Ejecución local

```bash
cd Kolcem_Costeo_Streamlit_Cloud
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Publicación en Streamlit Community Cloud

1. Crear un repositorio en GitHub, por ejemplo: `kolcem-costeo-streamlit`.
2. Subir estos archivos al repositorio:
   - `app.py`
   - `requirements.txt`
   - `.streamlit/config.toml`
   - `.gitignore`
   - `README.md`
3. Entrar a Streamlit Community Cloud.
4. Crear una nueva app seleccionando el repositorio.
5. En **Main file path**, escribir:

```text
app.py
```

6. Desplegar.

## Seguridad recomendada

No subir al repositorio archivos Excel con datos financieros reales. La app está diseñada para que el usuario cargue el Excel manualmente desde la interfaz.

Para uso empresarial, se recomienda migrar luego a un VPS privado o agregar autenticación.
