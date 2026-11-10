"""The screens call only server methods that exist, and the committed build is the build of the committed source.

Every literal 'lotus_farm.<module>.<function>' in frontend/src and in the committed bundle (lotus_farm/public/frontend)
must name a function that exists and is whitelisted; every source file listed in the bundle manifest must still exist.
A stale bundle (source changed, `npm run build` not committed) or a screen left calling a removed endpoint fails here."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHOD = re.compile(r"""['"`]lotus_farm\.([a-z0-9_]+(?:\.[a-z0-9_]+)+)['"`]""")


def _function(dotted):
    """(file, source) of the module holding the last part of a dotted path, or None."""
    *module, function = dotted.split(".")
    base = ROOT / "lotus_farm" / Path(*module)
    for candidate in (base.with_suffix(".py"), base / "__init__.py"):
        if candidate.is_file():
            return candidate, function
    return None


def _whitelisted(path, function):
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"\s*def {re.escape(function)}\(", line):
            above = index - 1
            while above >= 0 and lines[above].lstrip().startswith("@"):
                if "whitelist" in lines[above]:
                    return True
                above -= 1
            return False
    return None


def _problems(text):
    problems = set()
    for dotted in set(METHOD.findall(text)):
        found = _function(dotted)
        if not found:
            problems.add(f"lotus_farm.{dotted}: no such module")
            continue
        state = _whitelisted(*found)
        if state is None:
            problems.add(f"lotus_farm.{dotted}: no such function")
        elif not state:
            problems.add(f"lotus_farm.{dotted}: not whitelisted")
    return problems


class FrontendCalls(unittest.TestCase):
    def test_source_calls_resolve(self):
        problems = {}
        for path in sorted((ROOT / "frontend/src").rglob("*")):
            if path.suffix in (".js", ".vue") and path.is_file():
                found = _problems(path.read_text(encoding="utf-8"))
                if found:
                    problems[path.relative_to(ROOT).as_posix()] = sorted(found)
        self.assertEqual(problems, {}, "\n" + "\n".join(f"{f}: {'; '.join(p)}" for f, p in problems.items()))

    def test_committed_bundle_matches_the_source(self):
        manifest = json.loads((ROOT / "lotus_farm/public/frontend/.vite/manifest.json").read_text(encoding="utf-8"))
        missing = sorted({entry["src"] for entry in manifest.values() if entry.get("src") and not (ROOT / "frontend" / entry["src"]).exists()})
        self.assertEqual(missing, [], "the bundle was built from files that are gone: rebuild and commit lotus_farm/public/frontend")
        problems = {}
        for path in sorted((ROOT / "lotus_farm/public/frontend/assets").glob("*.js")):
            found = _problems(path.read_text(encoding="utf-8", errors="replace"))
            if found:
                problems[path.name] = sorted(found)
        self.assertEqual(problems, {}, "\n" + "\n".join(f"{f}: {'; '.join(p)}" for f, p in problems.items()))


if __name__ == "__main__":
    unittest.main()
