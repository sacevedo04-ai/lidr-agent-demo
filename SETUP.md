# Como dejar este agente corriendo para la demo

Este repo (`sacevedo04-ai/lidr-agent-demo`) es una copia independiente del
demo mostrado en el evento de LIDR-academy. El codigo en si ya lo tienes en
GitHub; lo que faltaba para que corra son 3 cosas, resueltas aca.

## 1. Que faltaba (y por que)

- `constants.py` no viene en el repo (esta en `.gitignore` a proposito,
  porque ahi va tu token de GitHub, nunca se sube un secreto a un repo
    publico). El script hace `from constants import GITHUB_TOKEN` en la
      primera linea, asi que sin este archivo ni siquiera arranca.
      - El agente usa el modelo `openai:gpt-4o`, lo que requiere la variable de
        entorno `OPENAI_API_KEY`. No esta declarada en ningun lado del codigo
          (la libreria la busca sola), asi que es facil pasarla por alto.
          - `requirements.txt` no fijaba la version de `opentelemetry`, y pip
            instalaba por defecto la mas nueva (1.44.x), que ya no es compatible con
              `pydantic-ai==0.0.42` (tira `ModuleNotFoundError: No module named
                'opentelemetry._events'`). Ya quedo corregido en este repo, fijando
                  `opentelemetry-api==1.29.0` / `opentelemetry-sdk==1.29.0` /
                    `opentelemetry-semantic-conventions==0.50b0`.

                    ## 2. Pasos para correrlo en tu computador

                    ```bash
                    git clone https://github.com/sacevedo04-ai/lidr-agent-demo.git
                    cd lidr-agent-demo

                    python3 -m venv .venv
                    source .venv/bin/activate        # en Windows: .venv\Scripts\activate

                    pip install -r requirements.txt
                    ```

                    Crea dos archivos en la raiz del proyecto (NO se suben a GitHub, ya estan
                    en `.gitignore`):

                    `constants.py`:
                    ```python
                    GITHUB_TOKEN = "tu_token_real_de_github"
                    ```
                    (se crea en https://github.com/settings/tokens, scope "repo" alcanza
                    para leer issues de repos publicos)

                    `.env`:
                    ```
                    OPENAI_API_KEY=tu_api_key_real_de_openai
                    LOGFIRE_TOKEN=
                    ```
                    (la key se consigue en https://platform.openai.com/account/api-keys;
                    LOGFIRE_TOKEN es opcional, se puede dejar vacio)

                    Despues corre:

                    ```bash
                    python3 github-agent.py
                    ```

                    ## 3. Una cosa mas a revisar antes de la demo

                    Al final de `github-agent.py`, dentro de `if __name__ == '__main__':`, el
                    repo que analiza esta hardcodeado a `LIDR-academy/AI4Devs-pipeline-solved`,
                    que no es este repo. Para la demo probablemente quieras apuntar a un repo
                    que tu controles y donde tengas issues preparados de antemano, para que la
                    demo en vivo no dependa de que issues existan justo ese dia.

                    ## 4. Verificacion que ya se hizo

                    Se probo de punta a punta con credenciales falsas: el script corre limpio
                    hasta el llamado real a la API de OpenAI, donde falla con un 401 claro
                    ("Incorrect API key provided"), que es exactamente lo esperado sin
                    credenciales reales. Con tu OPENAI_API_KEY y GITHUB_TOKEN verdaderos,
                    deberia funcionar sin mas cambios.
                    
