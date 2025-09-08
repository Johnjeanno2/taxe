#!/usr/bin/env bash
# Collecte des diagnostics pour 403 Forbidden sur retam.limitedsn.com
# Usage: scp diagnose_403.sh user@host:~/ && ssh user@host './diagnose_403.sh'
set -euo pipefail
OUT=diagnostic_403.txt
echo "Diagnostic run at: $(date -u)" > "$OUT"

DOMAIN=retam.limitedsn.com
IP=91.234.195.123
USER_HOME=/home/c2461288c
PROJECT_DIR="$USER_HOME/retam/retam"

echo "\n=== CURL bypass CDN (HTTPS) ===" >> "$OUT"
curl -I -H "Host: $DOMAIN" -H 'Cache-Control: no-cache' --resolve $DOMAIN:443:$IP https://$DOMAIN/ >> "$OUT" 2>&1 || true

echo "\n=== Passenger log tail (last 200 lines) ===" >> "$OUT"
if [ -f "$USER_HOME/logs/passenger.log" ]; then
  tail -n 200 "$USER_HOME/logs/passenger.log" >> "$OUT" 2>&1 || true
else
  echo "Passenger log not found at $USER_HOME/logs/passenger.log" >> "$OUT"
fi

echo "\n=== Recent logs in $USER_HOME/logs (grep 403) ===" >> "$OUT"
ls -la "$USER_HOME/logs" >> "$OUT" 2>&1 || true
grep -i "403" "$USER_HOME/logs"/* 2>/dev/null | tail -n 100 >> "$OUT" || true

echo "\n=== Apache global error_log tail (paths) ===" >> "$OUT"
if [ -f /usr/local/apache/logs/error_log ]; then
  tail -n 200 /usr/local/apache/logs/error_log >> "$OUT" 2>&1 || true
else
  echo "/usr/local/apache/logs/error_log not found" >> "$OUT"
fi

echo "\n=== .htaccess files in project and public_html ===" >> "$OUT"
find "$PROJECT_DIR" -maxdepth 3 -name '.htaccess' -exec echo "---- {} ----" >> "$OUT" \; -exec sed -n '1,200p' {} >> "$OUT" \; || true
find "$USER_HOME/public_html" -maxdepth 2 -name '.htaccess' -exec echo "---- {} ----" >> "$OUT" \; -exec sed -n '1,200p' {} >> "$OUT" \; || true

echo "\n=== File ownership & perms (project root) ===" >> "$OUT"
if [ -d "$PROJECT_DIR" ]; then
  ls -la "$PROJECT_DIR" >> "$OUT" 2>&1 || true
  echo "\n--- passenger_wsgi.py ---" >> "$OUT"
  if [ -f "$PROJECT_DIR/passenger_wsgi.py" ]; then
    ls -l "$PROJECT_DIR/passenger_wsgi.py" >> "$OUT" 2>&1 || true
    sed -n '1,200p' "$PROJECT_DIR/passenger_wsgi.py" >> "$OUT" 2>&1 || true
  else
    echo "passenger_wsgi.py not found in $PROJECT_DIR" >> "$OUT"
  fi
else
  echo "Project dir $PROJECT_DIR not found" >> "$OUT"
fi

echo "\n=== Python virtualenv site-packages (if exists) ===" >> "$OUT"
if [ -d "$USER_HOME/virtualenv/retam/3.12/lib" ]; then
  python - <<'PY' >> "$OUT" 2>&1
import sys, pkgutil
for pkg in ('django','psycopg2','osgeo','django.contrib.gis'):
    loader = pkgutil.find_loader(pkg)
    print(pkg, 'found' if loader else 'not found')
PY
else
  echo "virtualenv path not found: $USER_HOME/virtualenv/retam/3.12/lib" >> "$OUT"
fi

echo "\n=== mod_security audit log (common locations) ===" >> "$OUT"
# Look for mod_security or audit logs
grep -R "ModSecurity\|mod_security\|audit_log" /var/log /usr/local/apache/logs 2>/dev/null | tail -n 200 >> "$OUT" || true

echo "\nDiagnostic finished. Output: $OUT" >> "$OUT"

echo "Diagnostic written to $OUT. You can download it with:
scp $USER@HOST:$OUT ./"
