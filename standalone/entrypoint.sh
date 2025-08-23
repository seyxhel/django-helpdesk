#!/bin/bash
# Install extra deps from /opt/extra-deps.txt if it exists
if [ -f /opt/extra-dependencies.txt ]; then
    pip install -r /opt/extra-dependencies.txt
fi

cd /opt/django-helpdesk/standalone/
# Wait for DB to be ready before running migrations. This helps platforms
# (like Railway) where the Postgres container may come up slightly later.
# Configuration:
#  DB_WAIT_TIMEOUT (seconds, default 300)
#  DB_WAIT_INTERVAL (seconds between attempts, default 5)
DB_WAIT_TIMEOUT=${DB_WAIT_TIMEOUT:-300}
DB_WAIT_INTERVAL=${DB_WAIT_INTERVAL:-5}

wait_for_db() {
	# If pg_isready is available, use it (fast).
	if command -v pg_isready >/dev/null 2>&1; then
		host=${POSTGRES_HOST:-$(python -c "import os,urllib.parse,sys
import os
db=os.environ.get('DATABASE_URL')
if db:
	parsed=urllib.parse.urlparse(db)
	print(parsed.hostname or '')
else:
	print(os.environ.get('POSTGRES_HOST',''))")}
		port=${POSTGRES_PORT:-5432}
		echo "Waiting for Postgres at ${host}:${port} (pg_isready)..."
		end=$((SECONDS+DB_WAIT_TIMEOUT))
		while [ $SECONDS -lt $end ]; do
			if pg_isready -h "$host" -p "$port" >/dev/null 2>&1; then
				echo "Postgres is ready"
				return 0
			fi
			sleep $DB_WAIT_INTERVAL
		done
		return 1
	else
		# Fallback: try connecting by running a lightweight migrate attempt
		echo "pg_isready not found; will retry migrations until DB is reachable"
		end=$((SECONDS+DB_WAIT_TIMEOUT))
		while [ $SECONDS -lt $end ]; do
			if python manage.py migrate --noinput; then
				echo "Migrations applied (DB reachable)"
				return 0
			fi
			echo "DB not ready yet; sleeping ${DB_WAIT_INTERVAL}s and retrying..."
			sleep $DB_WAIT_INTERVAL
		done
		return 1
	fi
}

# Ensure media directory exists (MEDIA_ROOT may be a mounted volume in production)
if [ -n "$MEDIA_ROOT" ]; then
	mkdir -p "$MEDIA_ROOT"
fi

# Wait for DB then run migrations/collectstatic
if wait_for_db; then
	# If pg_isready path was used, run migrations now
	if ! python manage.py showmigrations >/dev/null 2>&1; then
		# If showmigrations fails, still try migrate once
		python manage.py migrate --noinput || true
	else
		python manage.py migrate --noinput || true
	fi
else
	echo "Database did not become ready within ${DB_WAIT_TIMEOUT}s" >&2
	# Fail fast so orchestrators can restart or show an error
	exit 1
fi

# Collect static files (safe to run multiple times)
python manage.py collectstatic --noinput || true

# Starting cron to check emails
printenv > /etc/env
env | awk -F= '{printf "export %s=\"%s\"\n", $1, $2}' > /etc/env
cron &&
# Start Gunicorn processes
echo Starting Gunicorn.
exec gunicorn standalone.config.wsgi:application \
	   --name django-helpdesk \
	   --bind 0.0.0.0:${GUNICORN_PORT:-"8000"} \
	   --workers ${GUNICORN_NUM_WORKERS:-"6"} \
	   --timeout ${GUNICORN_TIMEOUT:-"60"} \
	   --preload \
	   --log-level=debug \
	   --log-file=- \
	   --access-logfile=- \
	   "$@"
