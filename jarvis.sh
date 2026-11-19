#!/usr/bin/env bash
# Abre o Jarvis no Linux (o equivalente do Jarvis.vbs do Windows):
# servidor em segundo plano, janela própria do painel e ícone na área de notificação.
# Para ver os erros na tela:  ./jarvis.sh --terminal
SRC="$0"
while [ -L "$SRC" ]; do
  DIR="$(cd -P "$(dirname "$SRC")" && pwd)"
  SRC="$(readlink "$SRC")"
  case "$SRC" in /*) ;; *) SRC="$DIR/$SRC" ;; esac
done
cd -P "$(dirname "$SRC")" || exit 1
export PATH="$PATH:$HOME/.local/bin:/usr/local/bin:/snap/bin:$HOME/.npm-global/bin"
PY="python3"
[ -x ".venv/bin/python" ] && PY=".venv/bin/python"
if [ "$1" = "--terminal" ]; then
  exec "$PY" jarvis.py --janela
fi
mkdir -p dados
nohup "$PY" jarvis.py --janela </dev/null >> dados/jarvis-terminal.log 2>&1 &
