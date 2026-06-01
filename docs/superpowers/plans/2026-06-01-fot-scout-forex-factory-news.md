# Forex Factory News Block in `/fot-scout` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface upcoming high-impact Forex Factory events (next ~48h, filtered to the currencies of the unlocked fotmarkets assets) in every `/fot-scout` tick via the router JSON — informational only, no gating.

**Architecture:** A pure read-only function `upcoming_relevant()` in `wally_core.macro` reads the existing macro cache (refreshed daily by launchd), normalizes country→currency, filters by a currency set, and returns sorted events + nearest + stale flag. `fot_scout_router.scan()` collects the currencies of the unlocked assets being scanned and attaches a `news` block to its result dict. Claude renders that block in the `/fot-scout` output for all cases (APPROVED/override/WAIT).

**Tech Stack:** Python 3.11+, pytest. No new dependencies. Tests run from `shared/wally_core` using its `.venv`.

---

## File Structure

- **Modify** `shared/wally_core/src/wally_core/macro.py` — add `_country_to_currency()` helper and `upcoming_relevant()` function (read-only, reuses `_load_cache`, `_event_dt`, `CR_OFFSET`).
- **Modify** `shared/wally_core/tests/test_macro.py` — add fixture + tests for the new function.
- **Modify** `.claude/scripts/fot_scout_router.py` — add `ASSET_CURRENCIES` map, import `upcoming_relevant`, inject `news_fn` param into `scan()`, attach `news` block to the return dict.
- **Modify** `shared/wally_core/tests/test_fot_scout.py` — add tests asserting the news block is attached with currencies filtered to unlocked scanned assets.
- **Modify** `system/commands/fot-scout.md` — document the news render block.
- **Modify** `CLAUDE.md` — one-line note under the `/fot-scout` section.

**Test command (from repo root):**
```bash
cd shared/wally_core && .venv/bin/python -m pytest tests/test_macro.py tests/test_fot_scout.py -q
```

---

## Task 1: `upcoming_relevant()` in `wally_core.macro`

**Files:**
- Modify: `shared/wally_core/src/wally_core/macro.py`
- Test: `shared/wally_core/tests/test_macro.py`

- [ ] **Step 1: Write the failing tests**

Append to `shared/wally_core/tests/test_macro.py`:

```python
# ── upcoming_relevant ─────────────────────────────────────────────────────────

@pytest.fixture
def relevant_cache_file(tmp_path):
    """Mixed cache: USD + EUR (relevant) + AUD (noise) + a far USD event."""
    cache = {
        "fetched_at": "2026-06-01T04:00:00-06:00",
        "source": "forexfactory",
        "events": [
            {"name": "ADP Employment", "country": "United States", "impact": "high",
             "date": "2026-06-01", "time_cr": "10:00"},   # USD, +6h
            {"name": "ECB Rate", "country": "Euro Area", "impact": "high",
             "date": "2026-06-01", "time_cr": "07:00"},    # EUR, +3h
            {"name": "GDP q/q", "country": "AUD", "impact": "high",
             "date": "2026-06-01", "time_cr": "08:00"},    # AUD, noise
            {"name": "Far NFP", "country": "United States", "impact": "high",
             "date": "2026-06-05", "time_cr": "06:00"},    # USD, beyond 48h
        ],
    }
    f = tmp_path / "macro_events.json"
    f.write_text(json.dumps(cache))
    return f


def test_upcoming_relevant_filters_by_currency(monkeypatch, relevant_cache_file):
    set_cache_env(monkeypatch, relevant_cache_file)
    from wally_core.macro import upcoming_relevant
    now = datetime(2026, 6, 1, 4, 0, 0, tzinfo=CR_OFFSET)
    out = upcoming_relevant({"USD", "EUR"}, hours=48, now=now)
    names = [e["name"] for e in out["events"]]
    assert "GDP q/q" not in names          # AUD filtered out
    assert "Far NFP" not in names          # beyond 48h
    assert names == ["ECB Rate", "ADP Employment"]  # sorted by time


def test_upcoming_relevant_normalizes_country_to_currency(monkeypatch, relevant_cache_file):
    set_cache_env(monkeypatch, relevant_cache_file)
    from wally_core.macro import upcoming_relevant
    now = datetime(2026, 6, 1, 4, 0, 0, tzinfo=CR_OFFSET)
    out = upcoming_relevant({"USD"}, hours=48, now=now)
    assert all(e["currency"] == "USD" for e in out["events"])
    assert {e["name"] for e in out["events"]} == {"ADP Employment"}


def test_upcoming_relevant_nearest_and_hours_until(monkeypatch, relevant_cache_file):
    set_cache_env(monkeypatch, relevant_cache_file)
    from wally_core.macro import upcoming_relevant
    now = datetime(2026, 6, 1, 4, 0, 0, tzinfo=CR_OFFSET)
    out = upcoming_relevant({"USD", "EUR"}, hours=48, now=now)
    assert out["nearest"]["name"] == "ECB Rate"
    assert out["nearest"]["hours_until"] == 3.0
    assert out["events"][1]["hours_until"] == 6.0


def test_upcoming_relevant_excludes_outside_horizon(monkeypatch, relevant_cache_file):
    set_cache_env(monkeypatch, relevant_cache_file)
    from wally_core.macro import upcoming_relevant
    now = datetime(2026, 6, 1, 4, 0, 0, tzinfo=CR_OFFSET)
    out = upcoming_relevant({"USD"}, hours=2, now=now)   # 2h window excludes ADP(+6h)
    assert out["events"] == []
    assert out["nearest"] is None


def test_upcoming_relevant_stale_flag(monkeypatch, relevant_cache_file):
    set_cache_env(monkeypatch, relevant_cache_file)
    from wally_core.macro import upcoming_relevant
    fresh = datetime(2026, 6, 1, 5, 0, 0, tzinfo=CR_OFFSET)   # +1h after fetched
    assert upcoming_relevant({"USD"}, now=fresh)["stale"] is False
    stale = datetime(2026, 6, 2, 6, 0, 0, tzinfo=CR_OFFSET)   # +26h after fetched
    assert upcoming_relevant({"USD"}, now=stale)["stale"] is True


def test_upcoming_relevant_no_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("WALLY_MACRO_CACHE", str(tmp_path / "nonexistent.json"))
    from wally_core.macro import upcoming_relevant
    now = datetime(2026, 6, 1, 4, 0, 0, tzinfo=CR_OFFSET)
    out = upcoming_relevant({"USD"}, now=now)
    assert out == {"events": [], "nearest": None, "stale": True, "source": None}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd shared/wally_core && .venv/bin/python -m pytest tests/test_macro.py -q -k upcoming_relevant`
Expected: FAIL with `ImportError: cannot import name 'upcoming_relevant'`

- [ ] **Step 3: Write the implementation**

Append to `shared/wally_core/src/wally_core/macro.py`:

```python
STALE_HOURS = 24

_COUNTRY_CCY = {
    "united states": "USD",
    "usa": "USD",
    "euro area": "EUR",
    "united kingdom": "GBP",
    "japan": "JPY",
}


def _country_to_currency(country: str) -> str:
    """Normalize a cache `country` field to a 3-letter currency code.

    The FF scraper stores full names for USD/EUR/GBP/JPY ("United States", ...)
    and raw codes for everything else ("AUD", "CAD"). Map the known names;
    pass through unknown values uppercased.
    """
    c = (country or "").strip()
    return _COUNTRY_CCY.get(c.lower(), c.upper())


def upcoming_relevant(currencies, hours: int = 48,
                      now: datetime | None = None) -> dict:
    """High-impact events in the next `hours`, filtered to `currencies`.

    Read-only over the macro cache. Never fetches. Returns:
        {events: [{name, currency, country, date, time_cr, hours_until}],
         nearest: <first event or None>, stale: bool, source: str | None}
    """
    wanted = {str(c).upper() for c in currencies}
    cache = _load_cache()
    if cache is None:
        return {"events": [], "nearest": None, "stale": True, "source": None}

    if now is None:
        now = datetime.now(CR_OFFSET)
    if now.tzinfo is None:
        now = now.replace(tzinfo=CR_OFFSET)
    horizon = now + timedelta(hours=hours)

    out = []
    for ev in cache.get("events", []):
        if ev.get("impact") != "high":
            continue
        try:
            ev_dt = _event_dt(ev)
        except (ValueError, KeyError):
            continue
        if not (now <= ev_dt <= horizon):
            continue
        ccy = _country_to_currency(ev.get("country", ""))
        if ccy not in wanted:
            continue
        out.append({
            "name": ev.get("name", "?"),
            "currency": ccy,
            "country": ev.get("country", ""),
            "date": ev["date"],
            "time_cr": ev["time_cr"],
            "hours_until": round((ev_dt - now).total_seconds() / 3600.0, 1),
        })
    out.sort(key=lambda e: (e["date"], e["time_cr"]))

    stale = True
    fetched = cache.get("fetched_at")
    if fetched:
        try:
            f_dt = datetime.fromisoformat(fetched)
            if f_dt.tzinfo is None:
                f_dt = f_dt.replace(tzinfo=CR_OFFSET)
            stale = (now - f_dt) > timedelta(hours=STALE_HOURS)
        except ValueError:
            stale = True

    return {
        "events": out,
        "nearest": out[0] if out else None,
        "stale": stale,
        "source": cache.get("source"),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd shared/wally_core && .venv/bin/python -m pytest tests/test_macro.py -q`
Expected: PASS (5 existing + 6 new = 11 passed)

- [ ] **Step 5: Commit**

```bash
git add shared/wally_core/src/wally_core/macro.py shared/wally_core/tests/test_macro.py
git commit -m "feat(macro): upcoming_relevant() — currency-filtered FF events window"
```

---

## Task 2: Wire news block into `fot_scout_router.scan()`

**Files:**
- Modify: `.claude/scripts/fot_scout_router.py`
- Test: `shared/wally_core/tests/test_fot_scout.py`

- [ ] **Step 1: Write the failing tests**

Append to `shared/wally_core/tests/test_fot_scout.py` (reuses existing `mapping` fixture and `_bars` helper from that file):

```python
# ── news block ────────────────────────────────────────────────────────────────

def test_scan_attaches_news_block(mapping):
    captured = {}
    def fake_news(currencies, hours=48, now=None):
        captured["ccys"] = set(currencies)
        return {"events": [], "nearest": None, "stale": False, "source": "test"}
    out = r.scan(mapping, 1, 50.0, fetch=lambda a, i, n: _bars(40),
                 assets=["XAUUSD"], news_fn=fake_news)
    assert "news" in out
    assert out["news"]["source"] == "test"
    assert captured["ccys"] == {"USD"}


def test_scan_news_currencies_union_over_unlocked(mapping):
    captured = {}
    def fake_news(currencies, hours=48, now=None):
        captured["ccys"] = set(currencies)
        return {"events": [], "nearest": None, "stale": False, "source": None}
    out = r.scan(mapping, 1, 50.0, fetch=lambda a, i, n: _bars(40),
                 assets=["EURUSD", "XAUUSD"], news_fn=fake_news)
    assert captured["ccys"] == {"EUR", "USD"}


def test_scan_news_excludes_locked_asset_currency(mapping):
    # USDJPY is locked in phase 1 → JPY must not leak into the currency set.
    captured = {}
    def fake_news(currencies, hours=48, now=None):
        captured["ccys"] = set(currencies)
        return {"events": [], "nearest": None, "stale": False, "source": None}
    out = r.scan(mapping, 1, 50.0, fetch=lambda a, i, n: _bars(40),
                 assets=["USDJPY", "XAUUSD"], news_fn=fake_news)
    assert "JPY" not in captured["ccys"]
    assert captured["ccys"] == {"USD"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd shared/wally_core && .venv/bin/python -m pytest tests/test_fot_scout.py -q -k news`
Expected: FAIL with `TypeError: scan() got an unexpected keyword argument 'news_fn'`

- [ ] **Step 3: Add the import and `ASSET_CURRENCIES` map**

In `.claude/scripts/fot_scout_router.py`, near the other `wally_core`/`macross` imports (after the `import fot_scout_router` style path setup; the file already imports `from wally_core.validate import ...`), add the import:

```python
from wally_core.macro import upcoming_relevant  # noqa: E402
```

Then, near the other module-level maps (after `TV_SYMBOLS` / before `GOAL_USD`), add:

```python
# Divisas que mueven cada activo (para filtrar noticias FF relevantes).
ASSET_CURRENCIES = {
    "EURUSD": ("EUR", "USD"), "GBPUSD": ("GBP", "USD"), "USDJPY": ("USD", "JPY"),
    "XAUUSD": ("USD",), "NAS100": ("USD",), "SPX500": ("USD",),
    "BTCUSD": ("USD",), "ETHUSD": ("USD",),
}
```

- [ ] **Step 4: Add `news_fn` param and compute the news block**

Change the `scan` signature from:

```python
def scan(mapping: dict, phase: int, capital: float, *, fetch=fetch_bars,
         assets: list[str] | None = None, experimental_trend: bool = False) -> dict:
```

to:

```python
def scan(mapping: dict, phase: int, capital: float, *, fetch=fetch_bars,
         assets: list[str] | None = None, experimental_trend: bool = False,
         news_fn=upcoming_relevant) -> dict:
```

Then, immediately before the `return {` at the end of `scan`, insert:

```python
    # Noticias FF relevantes: divisas de los activos DESBLOQUEADOS que se escanean.
    allowed = PHASE_ALLOWED[phase]
    ccys: set[str] = set()
    for a in assets:
        if allowed == "ALL" or a in allowed:
            ccys.update(ASSET_CURRENCIES.get(a, ("USD",)))
    if not ccys:
        ccys = {"USD"}  # USD mueve todo el universo (oro/índices/cripto/EURUSD)
    news = news_fn(ccys, hours=48)
```

And add `"news": news,` as a new key inside the returned dict (e.g. right after `"goal_progress": _goal_progress(capital, phase),`).

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd shared/wally_core && .venv/bin/python -m pytest tests/test_fot_scout.py -q`
Expected: PASS (all existing fot_scout tests + 3 new)

- [ ] **Step 6: Smoke-test the live router**

Run: `.claude/scripts/.venv/bin/python .claude/scripts/fot_scout_router.py --json | python3 -c "import sys,json; d=json.load(sys.stdin); print('news keys:', list(d['news'].keys())); print('nearest:', d['news']['nearest'])"`
Expected: prints `news keys: ['events', 'nearest', 'stale', 'source']` and a nearest event (or `None`). No traceback.

- [ ] **Step 7: Commit**

```bash
git add .claude/scripts/fot_scout_router.py shared/wally_core/tests/test_fot_scout.py
git commit -m "feat(fot-scout): attach currency-filtered FF news block to router JSON"
```

---

## Task 3: Document the render block

**Files:**
- Modify: `system/commands/fot-scout.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add the render spec to the command doc**

In `system/commands/fot-scout.md`, after the "## Output esperado" section (after Caso C), add a new subsection:

````markdown
### 📰 Bloque de noticias (TODOS los casos)

Leído del campo `news` del JSON del router. Se muestra en APPROVED, override y WAIT.

```markdown
📰 Forex Factory — próximas 48h (USD/EUR)
   ⏰ 03 jun 06:15 CR · ADP Non-Farm Employment Change (USD) — en ~23h
   (sin otros high-impact relevantes hasta entonces)
```

- `news.events` vacío → `📰 FF: sin high-impact en 48h para tus assets.`
- `news.stale == true` → añadir `⚠️ calendario FF desactualizado (>24h) — refrescá: .claude/scripts/.venv/bin/python .claude/scripts/macro_calendar.py`
- Las divisas mostradas son las de los activos DESBLOQUEADOS escaneados (Fase 1 → USD/EUR).
- **Informativo** — nunca convierte un WAIT en GO ni bloquea (el gate real sigue siendo
  `macro_gate` en la cadena del agente).
````

- [ ] **Step 2: Add a one-line note to CLAUDE.md**

In `CLAUDE.md`, inside the `### `/fot-scout` (2026-05-31) — fotmarkets-only` section, append this line at the end of that section's prose:

```markdown
- **Noticias FF (2026-06-01):** el router adjunta un bloque `news` (eventos high-impact FF
  próximas 48h, filtrados a las divisas de los activos desbloqueados) al `--json`; se muestra
  en cada tick (incluido WAIT). Informativo, no gatea. Helper:
  `wally_core.macro.upcoming_relevant()`.
```

- [ ] **Step 3: Commit**

```bash
git add system/commands/fot-scout.md CLAUDE.md
git commit -m "docs(fot-scout): document FF news render block"
```

---

## Self-Review Notes

- **Spec coverage:** Function (Task 1) ✓, router wire-in with unlocked-currency union (Task 2) ✓, render block + stale/empty cases (Task 3) ✓, tests with synthetic fixtures (Tasks 1–2) ✓. Out-of-scope items (no re-fetch, no gating, no analyst/launchd/whitelist changes) are respected — none of the tasks touch those.
- **Type consistency:** `upcoming_relevant(currencies, hours, now)` returns `{events, nearest, stale, source}` in Task 1; consumed unchanged in Task 2 (`out["news"]`) and Task 3 (`news.events`, `news.nearest`, `news.stale`). Event dict keys `{name, currency, country, date, time_cr, hours_until}` consistent across function, tests, and render doc.
- **No placeholders:** every code/edit step shows the literal content.
