#!/usr/bin/env bash
# migrate-to-wally-trader.sh
#
# Migra el proyecto de `trading` → `wally-trader`:
#   1. Renombra el directorio local
#   2. Renombra la carpeta de memoria Claude Code (preserva conversación histórica)
#   3. Actualiza paths en .claude/settings.json
#   4. Guía para renombrar el repo en GitHub + actualizar git remote
#
# ⚠️  IMPORTANTE: EJECUTAR FUERA DE UNA SESIÓN ACTIVA DE CLAUDE CODE.
#     Claude Code cachea el cwd al arrancar; si está corriendo cuando
#     se renombra el dir, se rompen sus paths en caliente.
#
# Uso:
#   1. Cierra Claude Code (exit o cmd+Q)
#   2. bash ~/Documents/trading/bin/migrate-to-wally-trader.sh

set -euo pipefail

OLD_DIR="$HOME/Documents/trading"
NEW_DIR="$HOME/Documents/wally-trader"
OLD_MEM="$HOME/.claude/projects/-Users-josecampos-Documents-trading"
NEW_MEM="$HOME/.claude/projects/-Users-josecampos-Documents-wally-trader"

SETTINGS="$OLD_DIR/.claude/settings.json"

# ─── Colors ───
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
RESET=$'\033[0m'

say() { printf "${BLUE}→${RESET} %s\n" "$1"; }
ok()  { printf "${GREEN}✓${RESET} %s\n" "$1"; }
warn(){ printf "${YELLOW}⚠${RESET}  %s\n" "$1"; }
die() { printf "${RED}✗${RESET} %s\n" "$1" >&2; exit 1; }

# ─── Safety checks ───
say "Verificando precondiciones..."

[[ -d "$OLD_DIR" ]] || die "No existe $OLD_DIR — ¿ya fue migrado?"
[[ ! -d "$NEW_DIR" ]] || die "Ya existe $NEW_DIR — aborta para no sobrescribir"

# Verifica que NO hay una sesión activa de Claude Code usando este dir
if pgrep -af "claude.*trading" > /dev/null 2>&1; then
  warn "Parece que hay un proceso Claude Code corriendo con path 'trading'."
  warn "Ciérralo antes de continuar (exit o cmd+Q)."
  warn "Procesos detectados:"
  pgrep -af "claude.*trading" | head -5
  read -r -p "¿Continuar de todas formas? [y/N] " answer
  [[ "$answer" == "y" || "$answer" == "Y" ]] || die "Cancelado por el usuario"
fi

ok "Precondiciones OK"

# ─── Paso 1: Renombrar directorio del proyecto ───
say "Paso 1/4: Renombrando directorio del proyecto"
mv "$OLD_DIR" "$NEW_DIR"
ok "Directorio renombrado: $OLD_DIR → $NEW_DIR"

# ─── Paso 2: Migrar memoria de Claude Code ───
say "Paso 2/4: Migrando memoria Claude Code (preserva conversación histórica)"
if [[ -d "$OLD_MEM" ]]; then
  if [[ -d "$NEW_MEM" ]]; then
    BACKUP="$NEW_MEM.bak.$(date +%s)"
    warn "$NEW_MEM ya existe, haciendo backup a $BACKUP"
    mv "$NEW_MEM" "$BACKUP"
  fi
  mv "$OLD_MEM" "$NEW_MEM"
  ok "Memoria Claude migrada: $OLD_MEM → $NEW_MEM"
else
  warn "No existe $OLD_MEM — saltando migración memoria"
fi

# ─── Paso 3: Actualizar paths en .claude/settings.json ───
say "Paso 3/4: Actualizando paths hardcoded en settings.json"
NEW_SETTINGS="$NEW_DIR/.claude/settings.json"
if [[ -f "$NEW_SETTINGS" ]]; then
  # Backup primero
  cp "$NEW_SETTINGS" "$NEW_SETTINGS.bak.$(date +%s)"
  # Sed in-place (macOS requiere '')
  sed -i '' 's|~/Documents/trading/|~/Documents/wally-trader/|g' "$NEW_SETTINGS"
  ok "settings.json actualizado (5 paths)"
else
  warn "No existe $NEW_SETTINGS"
fi

# ─── Paso 4: Instrucciones para Git remote ───
say "Paso 4/4: Git remote (requiere acción manual en GitHub)"
cd "$NEW_DIR"
CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "(sin remote)")

cat <<EOF

${GREEN}✓ Migración local completa.${RESET}

${YELLOW}Faltan 2 pasos manuales:${RESET}

${BLUE}A) Renombrar repo en GitHub${RESET}
   1. Ve a: https://github.com/sasasamaes/trading/settings
   2. Sección "Repository name" → cambia a: ${GREEN}wally-trader${RESET}
   3. Click "Rename"

${BLUE}B) Actualizar git remote local${RESET}
   Remote actual: ${CURRENT_REMOTE}

   Corre estos comandos:

   ${YELLOW}cd $NEW_DIR${RESET}
   ${YELLOW}git remote set-url origin git@github.com:sasasamaes/wally-trader.git${RESET}
   ${YELLOW}git remote -v${RESET}  # verificar

${BLUE}C) Abrir Claude Code desde el nuevo path${RESET}

   ${YELLOW}cd $NEW_DIR${RESET}
   ${YELLOW}claude${RESET}

${GREEN}🌭 Wally Trader está listo.${RESET}
EOF
