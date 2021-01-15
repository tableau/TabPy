web: export TABPY_PORT=$PORT && tabpy
worker: sed -i "s/# TABPY_PORT = 9004/TABPY_PORT=$PORT/" /app/tabpy/tabpy_server/common/default.conf && tabpy-deploy-models /app/tabpy/tabpy_server/common/default.conf
