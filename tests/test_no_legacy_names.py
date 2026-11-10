"""The 76 legacy DocTypes of the field area are gone for good (spec 002, US7): nothing in the code may name them again.
A name counts when quoted ('Crop Cycle'), as a table (`tabCrop Cycle`) or as the snake_case word (crop_cycle,
lotus_crop_cycle). Only the purge tool, its patch and this test carry the list."""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOTS = ("lotus_farm", "frontend/src", "frontend/tests", "tests", "tools")
SUFFIXES = {".py", ".js", ".vue", ".json", ".mjs", ".cjs", ".html", ".txt", ".css"}
ALLOWED = {"lotus_farm/legacy_purge.py", "lotus_farm/patches/purge_legacy_doctypes.py", "lotus_farm/patches.txt", "tests/test_no_legacy_names.py",
           "tests/integration/verify_legacy_purge.py"}
SKIP_DIRS = {"node_modules", "__pycache__"}


def legacy_names():
    tree = ast.parse((ROOT / "lotus_farm/legacy_purge.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "LEGACY" for t in node.targets):
            return [name for names in ast.literal_eval(node.value).values() for name in names]
    raise AssertionError("LEGACY not found in legacy_purge.py")


def files():
    for root in ROOTS:
        for path in sorted((ROOT / root).rglob("*")):
            relative = path.relative_to(ROOT).as_posix()
            if not path.is_file() or path.suffix not in SUFFIXES or SKIP_DIRS & set(path.parts) or relative in ALLOWED:
                continue
            if relative.startswith("lotus_farm/public/frontend/"):
                continue
            yield relative, path


class NoLegacyNames(unittest.TestCase):
    def test_the_list_is_the_76_tables(self):
        names = legacy_names()
        self.assertEqual(len(names), 76)
        self.assertEqual(len(set(names)), 76)

    def test_no_legacy_doctype_folder_is_left(self):
        left = [name for name in legacy_names() if (ROOT / "lotus_farm/lotus_farm/doctype" / name.lower().replace(" ", "_")).exists()]
        self.assertEqual(left, [])

    def test_no_file_names_a_legacy_doctype(self):
        names = legacy_names()
        words = {name: re.compile(r"(^|[^a-z0-9_])(lotus_)?" + re.escape(name.lower().replace(" ", "_")) + r"($|[^a-z0-9_])", re.M) for name in names}
        found = {}
        for relative, path in files():
            text = path.read_text(encoding="utf-8", errors="replace")
            hits = [name for name in names if f"'{name}'" in text or f'"{name}"' in text or f"`tab{name}`" in text or words[name].search(text)]
            if hits:
                found[relative] = hits
        self.assertEqual(found, {}, "\n" + "\n".join(f"{f}: {', '.join(n)}" for f, n in sorted(found.items())))


if __name__ == "__main__":
    unittest.main()
