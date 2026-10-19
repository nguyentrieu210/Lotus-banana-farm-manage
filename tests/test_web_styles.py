"""Vite shared chunks must deliver their CSS to every server-rendered entry."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


class TestWebStyles(unittest.TestCase):
    def test_shared_dependencies_load_once_before_entry_css(self):
        entries={'_base':{'css':['base.css']},'_theme':{'imports':['_base'],'css':['theme.css']}}
        for key in ('index.html','assign.html','stock.html'):
            entries[key]={'file':key+'.js','imports':['_base','_theme'],'css':[key+'.css']}
        with tempfile.TemporaryDirectory() as directory:
            manifest=Path(directory)/'manifest.json'
            manifest.write_text(json.dumps(entries))
            frappe=types.SimpleNamespace(session=types.SimpleNamespace(user='test'),get_app_path=lambda *args:str(manifest))
            spec=importlib.util.spec_from_file_location('lotus_web_styles',Path(__file__).parents[1]/'lotus_farm/www/lotus.py')
            module=importlib.util.module_from_spec(spec)
            with patch.dict(sys.modules,{'frappe':frappe}):
                spec.loader.exec_module(module)
            # One workspace shell serves every /lotus route (docs/WORKSPACE_UI_STANDARD.md).
            for path,key in [('/lotus/mobile','index.html'),('/lotus/giao-viec','index.html'),('/lotus/kho','index.html')]:
                with self.subTest(path=path):
                    frappe.request=types.SimpleNamespace(path=path)
                    context=types.SimpleNamespace()
                    module.get_context(context)
                    self.assertEqual(context.styles,['/assets/lotus_farm/frontend/'+p for p in ['base.css','theme.css',key+'.css']])
                    self.assertEqual(context.script,'/assets/lotus_farm/frontend/'+key+'.js')
