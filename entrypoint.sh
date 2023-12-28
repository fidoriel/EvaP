
set -e # exit on error

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py compilemessages --locale de
python manage.py loaddata test_data.json
python manage.py refresh_results_cache

sleep infinity

cp deployment/localsettings.template.py evap/localsettings.py
sed -i -e "s/\${SECRET_KEY}/$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)/" evap/localsettings.py
