#!/bin/bash
# Sincroniza memoria entre repo y ~/.claude/projects/.../memory/
# Uso:
#   ./sync_memory.sh pull   # Claude (home) → repo
#   ./sync_memory.sh push   # repo → Claude (home)
#   ./sync_memory.sh status # muestra diferencias

CLAUDE_MEM="$HOME/.claude/projects/<project-path-encoded>/memory"
REPO_MEM="~/Documents/trading/.claude/memory"

ACTION="${1:-status}"

case "$ACTION" in
    pull)
        echo "📥 PULL: Claude (home) → repo"
        mkdir -p "$REPO_MEM"
        cp -v "$CLAUDE_MEM"/*.md "$REPO_MEM/" 2>/dev/null
        echo ""
        echo "✓ Memoria copiada al repo"
        echo "Siguiente: git add .claude/memory/ && git commit -m 'memory: sync from Claude'"
        ;;

    push)
        echo "📤 PUSH: repo → Claude (home)"
        mkdir -p "$CLAUDE_MEM"
        cp -v "$REPO_MEM"/*.md "$CLAUDE_MEM/" 2>/dev/null
        # NO copiar el README.md del repo a Claude memory
        rm -f "$CLAUDE_MEM/README.md"
        echo ""
        echo "✓ Memoria cargada a Claude"
        echo "Claude la leerá automáticamente en próxima sesión"
        ;;

    status)
        echo "🔍 STATUS de sincronización:"
        echo ""
        echo "Claude memory: $CLAUDE_MEM"
        echo "Repo memory:   $REPO_MEM"
        echo ""

        if [ ! -d "$CLAUDE_MEM" ]; then
            echo "⚠️ Claude memory NO existe. Ejecuta: ./sync_memory.sh push"
            exit 1
        fi

        if [ ! -d "$REPO_MEM" ]; then
            echo "⚠️ Repo memory NO existe. Ejecuta: ./sync_memory.sh pull"
            exit 1
        fi

        echo "Diferencias:"
        DIFF=$(diff -rq "$CLAUDE_MEM" "$REPO_MEM" 2>/dev/null | grep -v README.md)

        if [ -z "$DIFF" ]; then
            echo "✅ En sincronía"
        else
            echo "$DIFF"
            echo ""
            echo "Acciones sugeridas:"
            echo "  - Si Claude tiene cambios nuevos → ./sync_memory.sh pull"
            echo "  - Si repo tiene cambios nuevos  → ./sync_memory.sh push"
        fi
        ;;

    *)
        echo "Uso: $0 {pull|push|status}"
        echo ""
        echo "  pull    Copia memoria de Claude (~/.claude/) al repo"
        echo "  push    Copia memoria del repo a Claude"
        echo "  status  Muestra diferencias entre ambos"
        exit 1
        ;;
esac
