$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot

Push-Location (Join-Path $repo 'backend')
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.realtime.tests apps.realtime.tests_request_id apps.services.tests.test_general_settings_read_only apps.vehicles.tests.test_vehicle_list_query_budget --keepdb --verbosity 1
python manage.py report_db_capacity --json
Pop-Location

Push-Location (Join-Path $repo 'frontend')
npm test
npm run build
Pop-Location

Push-Location $repo
docker compose --env-file .env.production.example config --quiet
git diff --check
Pop-Location
