#!/usr/bin/env bash
# install.sh — Instala ClaudeBridge.mq5 en MetaTrader 5 (macOS con Bottles)
# Crea symlinks entre MQL5/Files/ y .claude/profiles/ftmo/memory/
#
# Uso:
#   cd .claude/profiles/ftmo/mt5_ea
#   bash install.sh
#
# Pre-requisito: abrir MT5 al menos una vez para que cree el bottle.
set -euo pipefail

# ─── Rutas base ───────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
EA_SOURCE="$SCRIPT_DIR/ClaudeBridge.mq5"
MEM_DIR="$REPO_ROOT/.claude/profiles/ftmo/memory"
ENV_FILE="$REPO_ROOT/.claude/.env"

# ─── Cargar .env si existe ────────────────────────────────────────────────────
if [ -f "$ENV_FILE" ]; then
  # shellcheck source=/dev/null
  set -a
  source "$ENV_FILE"
  set +a
  echo "✓ .env cargado desde $ENV_FILE"
fi

# ─── Auto-detect bottle path si MT5_FILES_PATH no está definido ──────────────
if [ -z "${MT5_FILES_PATH:-}" ]; then
  echo "🔍 Buscando bottle MT5 en macOS..."

  # Buscar directorios Files que estén bajo una ruta MQL5 dentro del Application Support de MT5
  CANDIDATES=$(find "$HOME/Library/Application Support/MetaTrader 5" \
    -type d -name "Files" -path "*/MQL5/*" 2>/dev/null | head -10 || true)

  COUNT=$(echo "$CANDIDATES" | grep -c . 2>/dev/null || echo "0")

  # grep -c retorna 1 si hay 1+ líneas no vacías; ajustar si CANDIDATES está vacío
  if [ -z "$CANDIDATES" ] || [ "$COUNT" = "0" ]; then
    echo ""
    echo "❌ No encontré bottle MT5 en:"
    echo "   $HOME/Library/Application Support/MetaTrader 5"
    echo ""
    echo "SOLUCIÓN:"
    echo "  1. Abre MetaTrader 5 al menos una vez y espera que cargue completamente."
    echo "  2. Cierra MT5."
    echo "  3. Vuelve a correr este script."
    echo ""
    echo "Alternativa manual:"
    echo "  Agrega en $ENV_FILE:"
    echo '  MT5_FILES_PATH="/ruta/completa/a/MQL5/Files"'
    echo ""
    echo "  Ejemplo típico macOS:"
    echo '  MT5_FILES_PATH="$HOME/Library/Application Support/MetaTrader 5/Bottles/metatrader5/drive_c/users/$USER/AppData/Roaming/MetaQuotes/Terminal/<HASH>/MQL5/Files"'
    exit 1
  elif [ "$COUNT" = "1" ]; then
    MT5_FILES_PATH="$CANDIDATES"
    echo "✓ Bottle detectado automáticamente:"
    echo "  $MT5_FILES_PATH"
  else
    echo "Encontré $COUNT bottles de MT5. Elige cuál usar:"
    # Mostrar opciones numeradas
    i=1
    while IFS= read -r line; do
      echo "  $i) $line"
      i=$((i + 1))
    done <<< "$CANDIDATES"

    printf "Número [1-%d]: " "$COUNT"
    read -r CHOICE

    MT5_FILES_PATH=$(echo "$CANDIDATES" | sed -n "${CHOICE}p")
    if [ -z "$MT5_FILES_PATH" ]; then
      echo "❌ Opción inválida."
      exit 1
    fi
    echo "✓ Seleccionaste: $MT5_FILES_PATH"
  fi
fi

# ─── Derivar rutas desde MT5_FILES_PATH ──────────────────────────────────────
BOTTLE_MQL5="$(dirname "$MT5_FILES_PATH")"
BOTTLE_EXPERTS="$BOTTLE_MQL5/Experts"

echo ""
echo "Rutas MT5:"
echo "  MQL5 root : $BOTTLE_MQL5"
echo "  Experts   : $BOTTLE_EXPERTS"
echo "  Files     : $MT5_FILES_PATH"
echo ""

# ─── Crear directorios si no existen ─────────────────────────────────────────
mkdir -p "$BOTTLE_EXPERTS"
mkdir -p "$MT5_FILES_PATH"
mkdir -p "$MEM_DIR"

# ─── Copiar EA ───────────────────────────────────────────────────────────────
cp "$EA_SOURCE" "$BOTTLE_EXPERTS/ClaudeBridge.mq5"
echo "✓ EA copiado: $BOTTLE_EXPERTS/ClaudeBridge.mq5"

# ─── Pre-crear JSON files vacíos si no existen ───────────────────────────────
STATE_JSON="$MT5_FILES_PATH/claude_mt5_state.json"
CMDS_JSON="$MT5_FILES_PATH/claude_mt5_commands.json"

if [ ! -f "$STATE_JSON" ]; then
  echo '{}' > "$STATE_JSON"
  echo "✓ Creado: $STATE_JSON"
else
  echo "✓ Ya existe: $STATE_JSON"
fi

if [ ! -f "$CMDS_JSON" ]; then
  echo '{"commands":[]}' > "$CMDS_JSON"
  echo "✓ Creado: $CMDS_JSON"
else
  echo "✓ Ya existe: $CMDS_JSON"
fi

# ─── Crear symlinks en memory/ ───────────────────────────────────────────────
ln -sf "$STATE_JSON" "$MEM_DIR/mt5_state.json"
echo "✓ Symlink: $MEM_DIR/mt5_state.json → $STATE_JSON"

ln -sf "$CMDS_JSON" "$MEM_DIR/mt5_commands.json"
echo "✓ Symlink: $MEM_DIR/mt5_commands.json → $CMDS_JSON"

# ─── Guardar MT5_FILES_PATH en .env si no estaba ─────────────────────────────
if ! grep -q "MT5_FILES_PATH=" "$ENV_FILE" 2>/dev/null; then
  echo "MT5_FILES_PATH=\"$MT5_FILES_PATH\"" >> "$ENV_FILE"
  echo "✓ MT5_FILES_PATH guardado en $ENV_FILE"
else
  echo "✓ MT5_FILES_PATH ya estaba en .env"
fi

# ─── Instrucciones finales ────────────────────────────────────────────────────
cat <<EOF

✅ Instalación completa.

════════════════════════════════════════════════════════
PRÓXIMOS PASOS EN MetaTrader 5
════════════════════════════════════════════════════════

1. Abrir MetaTrader 5.

2. Habilitar Expert Advisors:
   Tools → Options → Expert Advisors
   ☑ Allow algorithmic trading
   ☑ Allow DLL imports (por si fuera necesario)
   → OK

3. Compilar el EA (si no compila automáticamente):
   Tools → MetaEditor (o F4)
   File → Open → navegar a:
     $BOTTLE_EXPERTS/ClaudeBridge.mq5
   → Compilar con F7
   → Cerrar MetaEditor

4. Refrescar Navigator:
   Navigator (Ctrl+N) → Expert Advisors → F5 (refresh)
   Debe aparecer "ClaudeBridge" en la lista.

5. Activar en un chart:
   Arrastra "ClaudeBridge" a cualquier chart (recomendado: BTCUSD).
   En el diálogo:
   ☑ Allow Automated Trading
   → OK

6. Verificar inicio correcto:
   View → Terminal → Experts tab (Ctrl+T)
   Debe aparecer:
   "ClaudeBridge EA v1.0 starting magic=77777 heartbeat=5s"

7. Verificar que escribe estado (espera ~10 segundos):
   En terminal:
   cat "$MEM_DIR/mt5_state.json"
   Debe mostrar JSON con "last_update" reciente.

════════════════════════════════════════════════════════
TROUBLESHOOTING
════════════════════════════════════════════════════════

• EA no aparece en Navigator:
  Verificar que compiló sin errores (MetaEditor → Errors tab).
  Si hay errores de compilación, abrir issue en el repo.

• AutoTrading icon rojo (botón en toolbar MT5):
  Presionar Ctrl+E en MT5 para habilitarlo.
  O click en el icono "AutoTrading" en la toolbar.

• mt5_state.json no se actualiza:
  1. Verificar Experts tab — buscar errores "cannot open file".
  2. Asegurarse de que MT5_FILES_PATH apunta al directorio correcto.
  3. En MT5: Tools → Options → Expert Advisors → verificar permisos.

• "DLL imports not allowed":
  Tools → Options → Expert Advisors → ☑ Allow DLL imports → OK.
  Luego recargar el EA (drag de nuevo al chart).

• Magic number conflict (el EA ve posiciones de otro EA):
  Cambiar input Magic a otro valor (default: 77777).
  Actualizar también en el profile Claude config.

════════════════════════════════════════════════════════
EOF
