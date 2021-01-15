web: export TABPY_PORT=$PORT && tabpy& && cp /app/tabpy/tabpy_server/common/default.conf . && sed -i "s/# TABPY_PORT = 9004/TABPY_PORT=$PORT/" default.conf && tabpy-deploy-models default.conf
