"""Keep the browser Origin for Frappe's same-host websocket authentication."""
from pathlib import Path

path = Path('/templates/nginx/frappe.conf.template')
source = path.read_text()
old = 'proxy_set_header Origin $proxy_x_forwarded_proto://${FRAPPE_SITE_NAME_HEADER};'
new = 'proxy_set_header Origin $http_origin;'
if old in source:
    assert source.count(old) == 1, 'Unexpected nginx websocket template'
    path.write_text(source.replace(old, new))
else:
    assert new in source, 'Unexpected nginx websocket template'
