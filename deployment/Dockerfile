FROM frappe/erpnext:v16.50.0
USER frappe
WORKDIR /home/frappe/frappe-bench
RUN bench get-app --branch v16.50.0 --skip-assets https://github.com/frappe/hrms.git \
 && bench build --app hrms
USER root
COPY --chown=frappe:frappe . /home/frappe/frappe-bench/apps/lotus_farm
USER frappe
RUN ./env/bin/pip install --no-cache-dir -e apps/lotus_farm \
 && cd apps/lotus_farm/frontend && npm ci && npm run build \
 && rm -rf node_modules
RUN ln -sfn /home/frappe/frappe-bench/apps/lotus_farm/lotus_farm/public /home/frappe/frappe-bench/assets/lotus_farm \
 && ln -sfn /home/frappe/frappe-bench/apps/hrms/hrms/public /home/frappe/frappe-bench/assets/hrms
