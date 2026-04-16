#!/bin/bash

# Script pour automatiser le commit avec pre-commit
# Usage: ./scripts/dev/smart_commit.sh "message de commit"

if [ -z "$1" ]; then
    echo "Usage: $0 \"message de commit\""
    exit 1
fi

COMMIT_MESSAGE="$1"
MAX_ATTEMPTS=3
ATTEMPT=1

echo "🚀 Début du processus de commit..."

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    echo "📝 Tentative $ATTEMPT/$MAX_ATTEMPTS..."

    # Exécuter pre-commit
    if uv run --group dev pre-commit run --all-files; then
        echo "✅ Pre-commit réussi!"

        # Ajouter les fichiers modifiés par pre-commit
        git add -A

        # Faire le commit
        if git commit -m "$COMMIT_MESSAGE"; then
            echo "🎉 Commit réussi!"
            exit 0
        else
            echo "❌ Échec du commit"
            exit 1
        fi
    else
        echo "⚠️  Pre-commit a modifié des fichiers..."

        # Ajouter les fichiers modifiés
        git add -A

        ATTEMPT=$((ATTEMPT + 1))

        if [ $ATTEMPT -le $MAX_ATTEMPTS ]; then
            echo "🔄 Nouvelle tentative..."
        fi
    fi
done

echo "❌ Échec après $MAX_ATTEMPTS tentatives"
exit 1
