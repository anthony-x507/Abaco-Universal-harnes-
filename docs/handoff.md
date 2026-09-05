# Handoff — Universal (Abaco Universal Harness)

Esto es para **pasar el trabajo** a otra persona (ingeniería o diseño). No es un plan de producto nuevo. Lee esto antes de tocar archivos.

Idioma del repo: inglés. Puedes responder en español.

**Repo:** https://github.com/anthony-x507/Abaco-Universal-harnes-  
**Producto en Mac:** solo `Universal.dmg` → `/Applications/Universal.app`  
**Current version:** 1.2.9 (header **Abaco Universal Harness**)

---

## 1. Esto no es código regular

No es un ChatGPT clone. No es un frontend que pega a `/v1/chat/completions`. No es un monorepo de “microservicios”.

Es una **fábrica de agentes con plugins**:

```
Un proceso
  └─ Universal                 ← único raíz (platform.py)
       ├─ AgentRegistry        ← uno. Identidades. No el historial.
       ├─ AgentLifecycle       ← uno. Estados created → running → stopped.
       └─ AgentFactory         ← recibe esos dos. No construye otros.
            ├─ AgentGenerator  ← create
            └─ AgentManager    ← start / stop / list / delete / deploy
```

Un **agente** se arma así:

```
agente = modelo (provider) + canal + PluginHost
```

- El **provider** no es un plugin. Hay un cliente HTTP real: `OpenAICompatProvider`. El eco (`EchoProvider`) solo existe con `universal serve --demo`.
- El **canal** no es un plugin. Hoy: `cli` y `webhook`. El texto entra por `Agent.accept`, no saltándose el canal.
- Los **plugins** sí se enchufan. Plantillas **nombran ids**. El catálogo los instancia. El generator **no** hace `if plugin_id == "terminal"`.

Si alguien llega y crea un segundo registry, un segundo lifecycle, un segundo cliente HTTP por agente, o una API estilo OpenAI Chat Completions, **rompe el producto**. Eso no se “refactoriza después”. Se para.

Hay un diseñador en el equipo. Él cierra cara, hitos y qué se queda. Ingeniería no copia el árbol viejo **Aegis** (`factory/`, `aegis-agent/`, LibreChat, 40 providers falsos). Las notas de eso están en `notes/` como archivo, no como código a pegar.

---

## 2. Dónde está el código

| Qué | Dónde | Qué hace |
|---|---|---|
| Núcleo Python | `universal/` | Factory, agentes, plugins nativos, factory HTTP |
| Raíz de composición | `universal/core/platform.py` | **Único** sitio que construye registry + lifecycle |
| Agente | `universal/core/agent.py` | `complete` (modelo + tools), `accept` (canal), `run` (Auto) |
| Factory HTTP | `universal/server.py` | `127.0.0.1:43124`. Rutas `/v1/agents/...`, no `/v1/chat/completions` |
| CLI | `universal/cli.py` | `ask`, `chat`, `serve`, `desktop`, `update`, `audit` |
| Plantillas | `universal/templates/catalog.py` | Exactamente **tres**: `general`, `researcher`, `coder`. No hay `mother.yaml` |
| Plugins nativos | `universal/plugins/` | Python. Van en **todos** los agentes |
| Plugins Node | `agent_runtime/plugins/` | Hablan al core firmado (`ctx.corePost`). No son un segundo loader |
| Runtime Node | `agent_runtime/runtime.js` | Proceso aparte. Wallet/Tor los decide Python |
| Cara (SPA) | `web/` | Vite + React + Tailwind. Chat, Agents, Design, Settings |
| Chat | `web/src/pages/ChatPage.tsx` | Escribe, responde, Models, API key. **No crea agentes** |
| Design | `web/src/pages/DesignPage.tsx` | Aquí se crean agentes |
| API del browser | `web/src/lib/api.ts` | Solo habla con la factory |
| Tests Python | `tests/` | `python3 -m pytest` |
| Tests cara | `web/` (`vitest`) | `cd web && npm test` |
| Auditoría | `audit/` + `python3 -m universal audit` | Prueba los locks. HMAC, no quantum |
| Notas de diseño (archivo) | `notes/` | Aegis / ideas viejas. **No integrar copiando** |
| Briefs del diseñador | `docs/designer_*.md` | Alineación, visto, incidente de caché |
| Mapa de cableado | `docs/wiring.md` | Qué está conectado y qué no |

Puertos fijos en desarrollo:

- Cara Vite: `http://127.0.0.1:43123` (proxy a la factory)
- Factory: `http://127.0.0.1:43124`

En el `.app` de Mac, pywebview abre la factory (la SPA empaquetada en `web/dist`). La versión va en la URL (`/?v=1.2.9`) para no servir un Chat cacheado de v1.0.0.

---

## 3. Cómo encajan las integraciones (plugins)

Hay **dos pisos**. No los mezcles.

### Piso 1 — Python nativo (el que importa)

Vive en el paquete `universal`. Lista canónica: `NATIVE_PLUGIN_NAMES` en `universal/plugins/catalog.py`.

Hoy siempre se instalan: `terminal`, `tts`, `stt`, `vision`, `web_search`, `scraper`, `rule_enforcer`, `navigator`, `team`, `strategist`, `proof`, `improvement`, `package_manager`.

Un plugin Python:

1. Implementa `universal.core.plugin.Plugin` (hooks `before_complete` / tools).
2. Se registra en `PluginCatalog` por **id**.
3. La plantilla puede nombrarlo. Los nativos se meten igual aunque la lista venga vacía.
4. El modelo ve tools (`run_command`, `package_manager`, `set_objective`, …) y el loop las ejecuta en el mismo proceso.

Ejemplo reciente: `package_manager` → lógica en `universal/packages.py` → plugin `universal/plugins/package_manager.py`. Instala pip/npm/brew **después** del diálogo de permiso. No es “el agente corre `os.system` suelto”.

### Piso 2 — Node (propuestas, no gobierno)

`agent_runtime/plugins/*.js` llama `POST /v1/runtime/...` o `ctx.corePost`. El core Python firma, cifra (wallet) y abre Tor. Node **no** es la fuente de verdad.

No hay un segundo cargador de plugins en Application Support. Los nativos viven en el paquete.

### Qué no es plugin

- El modelo (provider)
- El canal
- El registry / lifecycle
- La cara React
- El catálogo de 10 China + 40 US: **una sola empresa, un flagship**. Rellenan `base_url` + `model` del **mismo** `OpenAICompatProvider`. No son 50 clientes HTTP.

---

## 4. Cara: Chat vs Design (diseñador)

Hay un **diseñador**. La cara se decide con él. Locks de UI que ya están cerrados:

| Página | Qué hace | Qué no hace |
|---|---|---|
| **Chat** | Hablar con un agente existente. Models + API key en la barra. Auto = `/run`. Workspace a la derecha | **No** crea agentes. No tiene “Create General”. No es Aegis / Universal Platform v1.0 |
| **Agents** | Lista, start/stop, settings del agente | No es el sitio principal de crear |
| **Design** | Elegir plantilla y crear | Tres plantillas, no una cuarta “madre” |
| **Settings** | Default del proceso, Check for Updates, auditoría | No escribe `.env`. Keys van a `llm.json` (0600) |

Chat 1.2.7: las respuestas quedan **arriba** de la caja de escribir. La caja es cristal más oscuro. El compositor no se monta encima del hilo.

Si alguien “arregla” Chat metiendo de nuevo Crear / Templates en el medio, está revirtiendo Hito 1. Parar.

Incidente real (diseñador, sep 2026): la Mac mostraba la cara v1.0.0 (**Universal Platform** + Create General) con un `.app` nuevo. Causa: WKWebView cacheó `http://127.0.0.1:43124/`. Detalle: `docs/designer_incident_report.md`. Wipe: `scripts/wipe_macos.sh`.

---

## 5. Dónde viven los datos (no se mezclan dos Macs)

En Mac, Application Support del usuario (no el repo):

| Archivo | Qué es | Qué no es |
|---|---|---|
| `registry.json` | Nombres, plantilla, plugins, estado | Historial, keys |
| `history/{id}.json` | Turnos de Chat | Registry |
| `llm.json` | Default del proceso (URL, modelo, key) | |
| `agent_secrets.json` | Key por agente | |
| `situation/{id}.json` | Misión (`MissionPhase`) | No es `AgentState` |
| `memory.json` | Hechos del researcher, por **nombre** | Segundo registry |
| `webview/` | Caché de la ventana nativa | |

Dos computadoras no comparten esa carpeta. Un `git push` **no** actualiza la app del diseñador. Actualiza el `.app` el workflow de Release al publicar un tag `v*`, o Settings → **Check for Updates**.

---

## 6. Cómo correrlo (dev)

```bash
python3 -m pip install -e ".[dev]"
python3 -m universal serve --demo --host 127.0.0.1 --port 43124

# otra terminal
cd web && npm install && npm run dev   # http://127.0.0.1:43123
```

Con API key real: Settings en la cara, o `UNIVERSAL_LLM_*`. Sin `--demo` no hay eco.

Tests mínimos antes de un cambio de locks:

```bash
python3 -m pytest
cd web && npm test
python3 -m universal audit
```

---

## 7. Cómo se publica un update que la Mac sí ve

**Check for Updates no mira `git push`.** Mira GitHub **Releases** del repo `anthony-x507/Abaco-Universal-harnes-`:

`GET https://api.github.com/repos/anthony-x507/Abaco-Universal-harnes-/releases/latest`

Ahí tiene que existir un tag más nuevo que el de la app **y** un archivo **`Universal.dmg`**. Si solo hay commits en `main`, Settings dice que no hay update. Eso no es un bug.

### Receta para el agente / ingeniero nuevo

1. **Subir la versión en el código** (todas a la misma, por ejemplo `1.2.8`):
   - `version.json` (`version` + `release_notes`)
   - `universal/_version.py`
   - `pyproject.toml`
   - `web/package.json`
   - tests que afirman la versión (`tests/test_updater.py`, `tests/test_desktop.py`, `web/src/test/fetch.ts`, `web/src/components/Header.test.tsx`)
2. **Commit** en `main`.
3. **Push de la rama a GitHub** (el remoto que es `anthony-x507/Abaco-Universal-harnes-`, no basta un remoto interno):
   ```bash
   git push github main
   ```
4. **Crear y empujar el tag** `v` + esa versión. El workflow **solo** corre con tags `v*`:
   ```bash
   git tag -a v1.2.8 -m "Una línea de qué cambió."
   git push github v1.2.8
   ```
   Sin este paso **no hay Release y no hay update**.
5. **Esperar Actions.** En el repo: Actions → workflow **Release**. Tiene que terminar en verde y adjuntar `Universal.dmg` al Release `v1.2.8`.
6. Comprobar a mano:
   - https://github.com/anthony-x507/Abaco-Universal-harnes-/releases/latest
   - Tiene que listar **Universal.dmg** (no un zip de source).
   - El tag tiene que ser **más alto** que el número del header en la Mac de Anthony (si la app dice 1.2.7, el Release tiene que ser 1.2.8 o más).
7. En la Mac: app en **`/Applications/Universal.app`** → Settings → **Check for Updates** → **Download now**. Si el `.app` está en Descargas, el updater avisa y no instala.

### Qué no sirve

| Lo que hizo alguien | Qué ve Anthony |
|---|---|
| `git push` a `main` | Nada. El header sigue igual. |
| Push a un remoto que no es ese GitHub | Nada. |
| Tag sin `v` (`1.2.8`) | El workflow no corre. |
| Tag empujado pero Actions falló | Release sin `.dmg` → “Latest release has no .dmg asset.” |
| Tag igual o menor que la app (`v1.2.7` si ya tiene 1.2.7) | “Already up to date.” |
| Subir solo el source zip a Releases | El updater busca un asset que termina en `.dmg`. |

`workflow_dispatch` en `.github/workflows/release.yml` también puede armar un Release, pero el camino normal es **tag `v*`**. No se “prepara el update” editando Settings. Se prepara en GitHub: **versión + tag + Actions + `Universal.dmg`**.

---

## 8. Locks (no negociar en un handoff)

- Un `Universal`, un registry, un lifecycle.
- Un provider HTTP real. Eco solo con `--demo`.
- Tres plantillas. Cero `mother.yaml`.
- Chat no crea agentes.
- Factory REST bajo `/v1/agents/...`, no clone de Chat Completions.
- Proof = HMAC, `quantum: false`.
- ZIP sin la API key en crudo.
- Plugins nativos en el paquete Python; Node llama al core.
- Nada de Aegis, LibreChat, jammer/EW, replay de logins, Redis/NATS.

Si un pedido choca con esto, se pregunta. No se “adapta el lock”.

---

## 9. A quién preguntar qué

| Tema | Quién |
|---|---|
| Layout, copy, hitos de cara, “qué se queda” | Diseñador |
| Registry, provider, plugins, factory, tests, DMG | Ingeniería |
| “¿Puedo añadir una plantilla / un provider / un Chat Completions?” | No, salvo que se reabran locks por escrito |

Documentos extra (no hace falta leerlos todos el primer día):

- `README.md` — cómo se usa
- `docs/wiring.md` — mapa
- `docs/designer_alignment_brief.md` — por qué no es Aegis
- `docs/designer_incident_report.md` — caché WKWebView
- `audit/README.md` — cómo se prueba que el harness sigue siendo el harness
