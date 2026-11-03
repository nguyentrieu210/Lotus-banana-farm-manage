"""Build and verify Vietnamese MO catalogs inside the immutable release image."""
import gettext
import sys
from pathlib import Path

from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po

bench = Path("/home/frappe/frappe-bench")
check_only = "--check-only" in sys.argv
for app in ("frappe", "erpnext", "hrms"):
    source = bench / "apps" / app / app / "locale" / "vi.po"
    target = bench / "assets" / "locale" / "vi" / "LC_MESSAGES" / f"{app}.mo"
    with source.open("rb") as stream:
        catalog = read_po(stream)
    assert all(message.string for message in catalog if message.id), app
    if not check_only:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as stream:
            write_mo(stream, catalog)
        target.chmod(0o644)
    with target.open("rb") as stream:
        binary = gettext.GNUTranslations(stream)
    for message in catalog:
        if message.id and isinstance(message.id, str):
            actual = binary.pgettext(message.context, message.id) if message.context else binary.gettext(message.id)
            assert actual == message.string, (app, message.id)
    print(f"{app}: {len(catalog)} Vietnamese messages verified")
