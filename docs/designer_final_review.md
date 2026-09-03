# Revisión para el diseñador — visto final

Este documento es para **ti**, el diseñador que cerró las notas 49 y 50. No es un plan de ingeniería nuevo. Es el estado real del producto **después** de Hito 0, Hito 1, Hito 2, el pulido de Chat/Settings y una auditoría de cableado. Te pedimos un **visto final**: qué se queda, qué se corrige, qué se pospone, y qué no se toca.

Responde por ítem. “Quédate como está” es una respuesta válida. Los locks no se negocian aquí (no Aegis, no `/v1/chat/completions`, no segundo registry, no replay de login, no jammer). Si un ítem choca con un lock, dilo y paramos.

---

## 1. Dónde estamos respecto a tu plan

Tu orden (nota 49 + 50):

| Hito | Qué pediste | Estado |
|---|---|---|
| 0 | Servidor HTTP de factory en el `Universal` existente | **Hecho.** `python3 -m universal serve` |
| 1 | SPA Chat / Agents / Settings, respuestas completas | **Hecho.** `web/` en Vite + React |
| 2 | Streaming token a token por factory, no clone API | **Hecho.** SSE en `POST /v1/agents/{id}/ask` con `stream: true` |
| Polish | Historial al cambiar de agente, burbuja si falla el envío | **Hecho.** Settings ya no muestra formulario vacío si el servidor no carga |
| 3 | Canal webhook en el catálogo, elegido en `create` | **No empezado.** Esperamos tu **sí** |
| 4 | Lista de plugins (lectura) + ZIP desde la UI | **No empezado.** El ZIP existe por CLI/API; la SPA no lo llama |
| 5 | Guía de uso + demo | **Parcial.** README + `web/README.md`; no hay walkthrough de owner |

Decisiones tuyas que **se respetaron**:

- SPA es la cara principal. CLI queda como admin/debug.
- Un hilo por agente, en memoria. No hay lista de conversaciones ni títulos.
- Sin pause: solo start / stop / delete.
- Settings solo en el proceso. La UI no escribe `.env`.
- `--demo` con echo, no un modelo “local” registrado.
- Servidor solo en localhost, sin login.
- Marca: bloque “U”, nombre Universal / Universal Platform.
- Tokens `#0B0E14` / `#00E5FF` / Inter.
- Webhook anunciado como “later”, **no registrado**.
- Browser, scheduler, EW, 40 providers, sandbox: fuera.

Lo que **creció más allá** de “conversación + lista lateral” (nota 49):

El Chat ya no es dos columnas. Pediste (owner) **tres áreas independientes**:

1. **Izquierda — Agents:** plantillas con descripción + lista de agentes + crear.
2. **Medio — Messages:** hilo + compositor (texto, File, Audio, Send).
3. **Derecha — Workspace:** dock de Screen + pestaña Extension.

Cada panel se abre y se cierra. El estado se guarda en `localStorage` bajo `universal-layout` (**solo** visibilidad de paneles, no settings ni keys).

El Workspace **no** es una extensión de Chrome ni una pantalla compartida. Es un hueco honesto: “No screen connected” / “Extension: not connected”. Connect e Install están deshabilitados. Browser automation y login replay siguen fuera.

File: un `.txt` / markdown / código pequeño se mete en el prompt. Binarios solo dejan una nota. Audio: el micrófono graba un clip; **no hay speech-to-text** en el servidor. El modelo ve una nota (“Attached audio clip…”).

---

## 2. Cómo está cableado (síntesis, no metáfora)

Un proceso `universal serve` construye **un** objeto `Universal`. Ese objeto es el único que crea:

- `AgentRegistry` (memoria)
- `AgentLifecycle` (estados: created → starting → running → stopping → stopped / error)
- `AgentFactory`, que **recibe** esos dos objetos y construye:
  - `AgentGenerator` (create)
  - `AgentManager` (start / stop / list / delete / deploy)

Generator y Manager **no** se fabrican su propio registry. Si alguien intenta inyectar un lifecycle de otro registry, el factory rechaza.

La SPA no tiene agentes propios. Habla solo con:

- `GET /health`
- `GET /v1/templates`
- `GET` / `PUT /v1/settings`
- `GET` / `POST /v1/agents`
- `GET /v1/agents/{id}`
- `POST .../start` · `POST .../stop` · `DELETE .../{id}`
- `POST .../ask` (completo o SSE)

No existe `/v1/chat/completions` en Universal. Los tests lo comprueban (404). El provider OpenAI-compatible **sí** llama hacia afuera a `{base}/chat/completions`: eso es el cliente real hacia el LLM, no una API clone hacia el mundo.

Flujo de un mensaje en Chat (demo o live):

```
SPA Send
  → POST /v1/agents/{id}/ask { prompt, stream: true }
  → servidor: factory.start(id) si aún no corre   (la SPA no llama /start antes de ask)
  → Agent.accept_stream(prompt)
  → channel.handle_text_stream
  → Agent.complete_stream
  → plugins.before_complete
  → provider.stream (o complete si hay tools)
  → plugins.after_complete
  → SSE: data: {"text": "..."} … data: { done: true, history, ... }
```

`complete` es el camino del **modelo**. `accept` es el camino de **entrada** después de start. HTTP usa accept. El CLI `universal chat` es la excepción: entra por `channel.serve_forever` → `handle` → el mismo `complete` bound, **sin** pasar por `accept`. Ingeniería lo marca como fuga de contrato, no como segundo factory.

`universal shell` y `serve` = un root por proceso. `universal ask` / `list` / `deploy` (comandos sueltos) = un `Universal` nuevo cada vez. Los agentes de un `ask` CLI no aparecen en la SPA. Eso es intencional con el lock de “sin persistencia”.

---

## 3. ¿La fábrica produce todo con el método plugin?

**No.** Esto es el punto más importante para tu visto.

La frase de producto que firmaste: *un agente es proveedor + canal + plugins*.

La fábrica **ensambla** esas tres piezas. Solo la tercera pieza pasa por `PluginCatalog` y `agent.attach_plugin`.

### 3.1 Qué SÍ es plugin (método plugin)

Hay un `Plugin` abstracto con:

- `on_attach` / `on_detach`
- `before_complete` / `after_complete`
- `tools()` / `invoke_tool`

Hay un `PluginHost` por agente. Hot-swap: `attach_plugin` / `detach_plugin` mientras corre. **Funciona en librería y tests. No hay ruta HTTP ni control en la SPA.** Tú lo dejaste para Hito 4 (lista de solo lectura) y “attach/detach por CLI o fase posterior”. Hoy ni la SPA ni el shell tienen attach/detach.

`PluginCatalog` registra **tres** ids:

| Id | Clase | Qué hace |
|---|---|---|
| `system_prompt` | `SystemPromptPlugin` | Reemplaza el system message que va al modelo por el texto de la plantilla |
| `transcript` | `TranscriptPlugin` | Guarda eventos before/after **dentro del plugin**. No es el historial del chat. No se ve en la UI. Crece sin tope |
| `tools` | `ToolBeltPlugin` | Ofrece herramientas al modelo. Hoy solo `utc_now` (hora UTC). Sin red, sin secretos |

El generator **no** hace `if plugin_id == "tools"`. Lee `template.default_plugins` y llama `plugins.create(id)`. Eso sí es el método plugin.

### 3.2 Qué instala cada plantilla

| Plantilla | Plugins instalados al create |
|---|---|
| `general` | `system_prompt`, `transcript` |
| `researcher` | `system_prompt`, `transcript`, `tools` |
| `coder` | `system_prompt`, `transcript` |

Solo **researcher** tiene una herramienta. General y coder no pueden llamar `utc_now` salvo que alguien haga hot-swap a mano en Python.

### 3.3 Qué NO es plugin (y la fábrica igual lo produce)

Estas piezas se ensamblan en `generate()`, pero **no** pasan por `PluginCatalog`:

| Pieza | Cómo se crea | ¿Plugin? |
|---|---|---|
| **Provider** (LLM) | Un `OpenAICompatProvider` cacheado en el generator, o `EchoProvider` si `--demo` | No. Es el modelo |
| **Channel** | `ChannelCatalog.create("cli")` → `CLIChannel` | No. Es el transporte. Mismo *patrón* de catálogo, otra clase (`BaseCommunication`) |
| **Template** | `TemplateCatalog.get("general")` | No. Es la receta (prompt + lista de plugin ids) |
| **Historial del chat** | `Agent._history` en el agente | No. Un hilo en memoria. Distinto de `TranscriptPlugin` |
| **System prompt en el agente** | `agent.system_prompt = template.system_prompt` **y además** el plugin `system_prompt` | Doble capa. Ver pregunta 4 |
| **Settings** | Dataclass en el proceso | No |
| **ZIP deploy** | `ZipPackager` vía factory/manager | No |
| **Páginas SPA** (Chat, Agents, Settings, Workspace) | React. Cliente de la factory | No son plugins |

Conclusión para ti: **todo agente sale de la fábrica con el mismo método de ensamblaje** (plantilla → provider + channel + plugins). **No todo lo que la fábrica toca es un plugin.** Si tu modelo mental era “todo es plugin”, hoy no es así. Provider y channel son ciudadanos de primera, no plugins.

### 3.4 Qué se anunció y no quedó instalado como plugin (ni como canal)

| Cosa | Estado | Por qué |
|---|---|---|
| Webhook | Anunciado en `COMING_CHANNELS` y en la UI como “later”. **No está en `ChannelCatalog`.** `create(channel="webhook")` da error | Hito 3, esperando sí |
| Telegram / Discord / Slack | No registrados | Descartados como stubs |
| Plugins de notas 07–17 (search, scraper, office, browser…) | No existen en el catálogo vivo | Retrasados / nunca |
| HF / MLX / 40 providers | No hay stubs | Un cliente OpenAI-compat |
| Extensión Chrome / screen share | UI de hueco. Cero código de captura | Descartado como automatización |
| Attach/detach en UI | No | Hito 4 |
| ZIP en UI | API `POST /v1/agents/{id}/deploy` existe; Chat/Agents no la llaman | Hito 4 |
| `GET /v1/channels` | Existe; la SPA usa `settings.channels` | Cosmético |
| `Agent.reset_history`, `find_by_name`, `lifecycle.error_of` | Código muerto. Nadie los llama | Nadie los diseñó en la cara |

---

## 4. La cara, tal como está (para que la juzgues)

### 4.1 App shell

Nav estrecha: Chat / Agents / Settings. Letra U. En viewport medio es solo iconos; en xl se lee “Universal / Platform”. Punto verde + “Demo echo” o “Connected”.

### 4.2 Chat (tres paneles)

- **Agents (izq.):** cards de General / Researcher / Coder con tu copy de descripción. Crear agente. Lista con estado (`running`), canal, nombres de plugins (solo lectura, como pediste).
- **Messages (centro):** un hilo. Composer abajo. File, Audio, Send. Al cambiar de agente se limpia el hilo y carga el nuevo (ya no parpadea el anterior). Si ask falla, el texto vuelve al compositor.
- **Workspace (der.):** Screen (marco, Offline, Connect disabled) y Extension (Universal companion, not installed, Install disabled).

Pregunta de diseño, no de ingeniería: **¿las tres columnas son la cara que firmas, o quieres volver a conversación + lista y dejar Workspace para Hito 4+?** El owner las pidió. Tú habías dibujado dos zonas. Los tres paneles caben; en pantallas estrechas se apilan o se cierran.

### 4.3 Agents

Create (nombre, plantilla, canal `cli` / webhook disabled). Start / Stop / Delete / Open chat. Sin pause. El canal del formulario es estado local `'cli'`; **no lee** `default_channel` de Settings.

### 4.4 Settings

Base URL, API key (vacío = no tocar el secreto), modelo, canal por defecto (`cli` + webhook later). Copy: “not written to disk”. Si el servidor no responde: error + Retry, **no** un form vacío.

**Comportamiento que choca con lo que un usuario espera:** al Save, el proceso actualiza Settings y tira el cliente LLM cacheado. Los **agentes ya creados siguen con el provider viejo**. Un agente nuevo sí usa la key/URL nueva. ¿Es eso lo que quieres (settings = defaults para el próximo create) o quieres que Save recablee a todos los agentes vivos?

---

## 5. Hallazgos de la auditoría (para que opines, no para que programes)

Cuatro barridos: bugs, cableado, locks, tests. Locks **limpios**. 59 tests verdes. Problemas de síntesis y de carrera.

### 5.1 Cableado (HOLD vs fuga)

| Hecho | Tipo | ¿Te importa en la cara? |
|---|---|---|
| Un registry + un lifecycle inyectados | HOLD | Sí: es tu definición de Universal |
| HTTP ask usa `accept` / `accept_stream` | HOLD | Sí: un solo camino de mensaje |
| Settings PUT no recablea agentes vivos | Fuga | **Pregunta 8** |
| Settings PUT no cierra el `httpx` viejo | Fuga técnica | No visual |
| Catálogos (templates/plugins/channels) son singletons de módulo, no del `Universal` | Fuga de composición | Hoy la UI ve lo mismo. Si un día inyectamos otro catálogo, HTTP puede mentir |
| SPA create ignora `default_channel` de Settings | Fuga de cara | **Pregunta 9** |
| CLI `chat` no usa `accept` | Fuga de contrato | CLI no es la cara |
| `factory.create(provider=...)` permite otro provider por agente | Fuga de librería, no HTTP | No expuesto en UI |

### 5.2 Bugs que afectan la cara

1. **Dos asks a la vez** (dos pestañas, doble Send) pueden **corromper el historial**. No hay lock por agente. Tu regla fue “un hilo por agente”. Ingeniería puede serializar asks. ¿Lo tratamos como regla de producto (un ask a la vez, el segundo espera o se rechaza)?
2. **Borrar un agente mientras Chat está enviando** deja un stream escribiendo en un objeto que ya no está en el registry. ¿Delete debe esperar / cancelar el ask, o la UI debe bloquear Delete si hay envío?
3. **SSE a veces no ve el evento final** si el socket cierra sin `\n\n`. El polish entonces **revierte** el mensaje (parece que no se envió, pero el servidor sí contestó). ¿Prefieres “mensaje enviado, error al confirmar” o el rollback actual?
4. Errores de stream se muestran todos como 502. Poco útil para ti; es copy de error.

### 5.3 Tests (por si te importa la confianza, no la cara)

Los tests no espían si HTTP usa `accept` o `complete`. Si alguien recableara mal, varios tests seguirían verdes. No hay tests de la SPA. No hay test de “ask sin start previo” (que es exactamente lo que hace Chat). No hay test de “serve rechaza 0.0.0.0”.

---

## 6. Preguntas para tu visto final

Responde 1–16. Una frase basta. Si un bloque entero te parece bien, escribe “1–7: quédate”.

### Cara

1. **Tres paneles (Agents / Messages / Workspace).** ¿Los firmas como primera cara, o Workspace sale del Chat hasta que haya algo real que mostrar?
2. **File y Audio en el compositor.** Hoy son adjuntos al prompt, no un pipeline de archivos ni STT. ¿Se quedan con copy honesta, se quitan hasta tener backend, o diseñamos otro control (solo File, solo Audio, drag-and-drop más visible)?
3. **Screen / Extension deshabilitados.** ¿El hueco honesto se queda (para que la columna exista), o la columna derecha no debería existir hasta Hito posterior?
4. **System prompt doble.** El agente guarda `system_prompt` y además instala el plugin `system_prompt` con el mismo texto. Si se desinstala el plugin, el agente **sigue** mandando system por la capa del agente. ¿Quieres una sola fuente (solo plugin, o solo campo del agente)?
5. **`transcript` invisible.** Está en las tres plantillas. El usuario no lo ve. El chat usa `_history`, no ese plugin. ¿Lo quitamos de general/coder (y de researcher), lo dejamos como debug interno, o Hito 4 lo muestra como “activity log”?
6. **`tools` solo en researcher.** ¿General y coder deben nacer sin herramientas (hoy), o las tres plantillas llevan `utc_now`? ¿O ninguna lleva tools hasta que diseñes una Tools page?
7. **Nombres de plugins en la lista de agentes.** Se ven como `cli · system_prompt, transcript`. ¿Suficiente para v1, o demasiado interno (mejor ocultar ids y mostrar “2 plugins”)?

### Settings y create

8. **Save en Settings.** ¿Aplica solo a agentes **nuevos** (hoy, hay que decirlo en la UI) o debe recablear a **todos** los agentes vivos en ese proceso?
9. **Canal por defecto.** Settings tiene “Default channel for new agents”. Chat y Agents crean con `cli` hardcodeado. ¿Create debe leer Settings, o quitamos ese campo de Settings hasta webhook?
10. **Key ausente en demo.** Settings muestra API key “(missing)” en `--demo`. ¿Copy “Demo echo — no key needed”, o está bien “missing”?

### Contrato de un mensaje

11. **Un ask a la vez por agente.** ¿Regla de producto (cola o rechazo + copy) o solo un arreglo interno silencioso?
12. **Delete durante un ask.** ¿Bloquear Delete / mostrar “agent is answering”, o cancelar el ask y borrar?
13. **Fallo a mitad de stream.** ¿Rollback al compositor (hoy) o dejar el mensaje del usuario y marcar el turno del agente como error?

### Hitos

14. **Hito 3 webhook.** ¿Siguiente sí ahora, o después de arreglar 8–13? Recuerda: webhook es canal en el catálogo, elegido en `create`, no un `POST /hooks` suelto.
15. **Hito 4.** Lista de plugins + botón ZIP. ¿La lista es solo lectura (tu nota 49) o ya quieres attach/detach en UI? ZIP: ¿en Agents, en Chat, o en ambos?
16. **Hito 5.** ¿Quieres guía + demo ahora, o después de 3/4?

### Locks (solo confirma)

17. Confirmas: sin Aegis, sin clone `/v1/chat/completions`, sin segundo registry, sin persistir agentes, sin replay/scheduler/EW, sin 40 providers. (Si algo de esto cambió, dilo explícito.)

---

## 7. Lo que ingeniería hará según tu respuesta

- Si dices **quédate** en cara (1–7) y **arregla Settings/ask** (8–13): pulimos copy + recableo/serialización. No abrimos webhook.
- Si dices **sí, Hito 3**: registramos `webhook` de verdad y la UI deja de mostrar “later” disabled.
- Si dices **Workspace fuera**: quitamos la columna derecha y volvemos a Agents + Messages.
- Si dices **todo es plugin**: **paramos**. Convertir provider y channel en plugins rompe el spine que firmaste (tres piezas distintas). No lo hacemos sin un rediseño tuyo por escrito.
- Si dices **quita transcript / unifica system prompt**: es un corte chico de factory, no de cara.

No implementamos nada de este documento hasta que contestes. Este es el paquete para tu visto.

---

## 8. Resumen en una página (por si lees esto al final)

Universal corre. Un proceso, una fábrica, un registry, un lifecycle, un provider real (o echo en demo), un canal (`cli`), tres plantillas, tres plugins en catálogo, tres páginas, Chat en tres paneles. Streaming por factory. Locks limpios.

**No** todo lo que sale de la fábrica es un plugin. Plugin = `system_prompt` + `transcript` + `tools`. El modelo y el canal se ensamblan al lado. Webhook, ZIP en UI, attach/detach, screen real: no instalados.

La auditoría no encontró un segundo factory. Encontró Settings que no recablean agentes vivos, asks concurrentes que pueden romper el hilo, y un Workspace que es un muelle vacío a propósito.

Tu visto cierra si esta cara y este ensamblaje son el producto, o qué hay que mover antes del Hito 3.
