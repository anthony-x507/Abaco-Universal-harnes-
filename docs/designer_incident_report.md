# Informe para el diseñador — 4 septiembre 2026

Esto es un informe de incidente, no un plan de producto nuevo. Pedimos guía: qué se queda, y cómo confirmamos que la Mac muestra la cara actual. Los locks no se negocian (un registry, un provider real, Chat no crea agentes).

## 1. Qué está viendo Anthony ahora

Después de un wipe limpio de `/Applications/Universal.app` y de Application Support, la ventana sigue mostrando la cara de **Hito 1 / v1.0.0–v1.0.1**:

- Marca **Universal Platform** (bloque “U”), no **Abaco Universal Harness**
- Nav: Chat / Agents / Settings — **sin Design**
- En Chat: Templates, Face, **Create General**
- Placeholder: **Write in the middle column...**
- Workspace Screen OFFLINE / “coming soon”
- Agente **Test** creado con el botón viejo

Esa cara salió del código fuente el 4 sep ~10:51 UTC en `ee2232e` (“Quiet Chat to three panes and add a Design page”). Desde v1.0.4 en adelante el Header ya dice Abaco Universal Harness y Chat no crea agentes.

**Anthony no está viendo el fuente actual.** Está viendo un documento HTML/JS viejo.

## 2. Qué hay en el repo ahora (verificado)

GitHub `main` y el tag `v1.2.3` (`188e46e`) tienen:

| Superficie | Estado real en fuente |
|---|---|
| Header | Abaco Universal Harness + versión de `/health` |
| Nav | Chat, Agents, **Design**, Settings |
| Chat | Models + API key. Placeholder: “How can I help you today?”. Crear se hace en Design |
| Factory | `PUT /v1/settings` persiste `llm.json`. Keys por agente en `agent_secrets.json`. Historial en `history/{id}.json` |

CI de Release para `v1.2.3` corrió sobre `188e46e`, conclusión **success**, y subió `Universal.dmg` (115 MB, 3 descargas). El script de build **falla** si `web/dist` todavía contiene “Write in the middle column” o no contiene “Abaco Universal Harness”.

Conclusión: **el DMG publicado no puede haber empaquetado esa cara vieja.** Si el `.app` instalado se inspecciona, `web/dist` debe tener la cara nueva.

## 3. Qué hicimos hoy (cronología honesta)

Hora UTC, 4 sep 2026. Todo el día en la misma rama `main`.

| Hora | Qué | ¿Cambió la cara de Chat? |
|---|---|---|
| 20:13 | `v1.0.7` — historial persistente, Models en el compositor, relaunch al actualizar | No. Chat ya era Harness + Design |
| 22:07 | `v1.2.1` — persistir API key y rebind de agentes vivos | No |
| 22:18 | `v1.2.2` — hidratar la key en el provider antes de cada ask | No |
| 22:48 | `v1.2.3` — `Cache-Control: no-store` en `index.html`, badge de versión, guardrail en el build | No. Intentó evitar caché; **no basta** |
| 22:57–23:01 | Script de wipe + expulsar DMGs montados | No toca `web/` |

**Ningún commit de las últimas horas revirtió Chat a Universal Platform.** Si el diseñador busca un revert de `ee2232e`, no está en este árbol.

El pedido de Anthony de “el último push de hace dos horas” encaja con `v1.2.1`–`v1.2.3`: ahí empezamos a publicar DMGs nuevos y a decirle que usara Check for Updates. La **actualización del `.app` sí corrió**. La **cara en pantalla no cambió**.

## 4. Qué funcionó y qué no

### Funcionó

- El fuente y los tests de Chat/Design/Header.
- Persistir keys e historial **en el factory** (Application Support).
- El wipe: `/Applications/Universal.app` y Application Support quedaron vacíos (él pegó `No such file or directory`).
- Expulsar `/Volumes/Universal` y `/Volumes/Universal 1`.
- Publicar `v1.2.3` en GitHub Releases. GitHub **no** manda un DMG distinto por Mac.

### No funcionó (errores nuestros)

1. **Diagnóstico equivocado.** Dijimos “abriste un `.app` viejo en Descargas”. Después del wipe eso ya no era el problema principal.
2. **El wipe no tocó la caché real.** Las rutas `~/Library/Caches/com.universal*` y `~/Library/WebKit/com.universal*` **nunca existieron** (zsh: `no matches found`). pywebview no usa ese bundle id.
3. **`private_mode=False` en el desktop.** Lo dejamos así para que `getUserMedia` exista. Efecto: WKWebView **guarda** `http://127.0.0.1:43124/` en disco. Reemplazar `Universal.app` no borra ese sitio. El factory nuevo sigue aceptando `POST /v1/agents`, así que **Create General** del HTML viejo sigue creando “Test” contra el backend nuevo.
4. **`Cache-Control: no-store` en 1.2.3 no ayuda** si WebView sirve el `index.html` viejo desde disco sin volver a pedir la red.
5. La ventana nativa se sigue titulado `"Universal platform"` — confunde el chrome con la cara vieja.

Dos Macs **no** se mezclan. En **una** Mac, la caché de localhost sí sobrevive a 10 updates.

## 5. Causa raíz (ingeniería)

```
Universal.app 1.2.3  →  factory :43124 sirve la SPA nueva
WKWebView (private_mode=False)  →  documento cacheado de v1.0.0
Usuario ve Universal Platform + Create General
```

No se perdió el trabajo de Design, Models, ni keys. Está en el binario. La ventana no lo pinta.

## 6. Recuperación propuesta (pedimos visto)

Ingeniería va a hacer esto, salvo que digas que no:

1. Cargar `http://127.0.0.1:43124/?v=<versión>` para que la clave de caché no sea la de v1.0.0.
2. Guardar el storage de WebView **dentro** de Application Support (`webview/`), para que un wipe futuro sí lo borre.
3. `Cache-Control: no-store` en **todos** los assets de la SPA, no solo `index.html`.
4. Título de ventana: **Abaco Universal Harness**.
5. Publicar **v1.2.4** (mismo Chat de ahora, no un rollback a Create-on-Chat).

En la Mac, mientras tanto, confirmar qué hay **dentro** del `.app`:

```bash
rg -l "Write in the middle|How can I help you today|Abaco Universal Harness" \
  /Applications/Universal.app/Contents/Resources/web/dist
```

- Si el `.app` tiene “How can I help” / Harness y la ventana no: es caché. 1.2.4 lo corta.
- Si el `.app` tiene “Write in the middle”: no es este release; hay que ver qué archivo se abrió.

**No** vamos a devolver Templates/Face/Create General a Chat a menos que el diseñador lo pida. Anthony ha pedido la cara Harness + Design + Models.

## 7. Qué no se toca

Un `AgentRegistry`, un `AgentLifecycle`, un `OpenAICompatProvider`, tres templates, factory en 43124, Chat en `ChatPage.tsx`, crear en Design, proof HMAC (`quantum: false`), plugins nativos y rule ids.

## 8. Pregunta al diseñador

1. ¿Confirmas que la cara correcta es Harness + Design + Models, y que Universal Platform / Create-on-Chat es la que hay que dejar atrás?
2. ¿El título nativo de la ventana debe decir Abaco Universal Harness (no “Universal platform”)?
3. ¿Algo más de las notas 49/50 debe volver a Chat, o se queda en Design?
