"""Shared desktop entry point for the JVN and VERA editors."""
import os
from pathlib import Path
from threading import Lock

import flet as ft

ROOT = Path(__file__).resolve().parent
import SKED_GUITool
import SKED_GUITool_vex


def main(page):
    page.title = "SKEDTool_JP — JVN / VERA"
    start_lock = Lock()
    started = False

    def start(editor):
        nonlocal started
        with start_lock:
            if started:
                return
            page.controls.clear()
            editor(page)
            started = True

    page.add(ft.Column([
        ft.Text("SKEDTool_JP", size=28),
        ft.Text("Select an observing network."),
        ft.ElevatedButton("JVN — DRG", on_click=lambda _: start(SKED_GUITool.main)),
        ft.ElevatedButton("VERA — VEX", on_click=lambda _: start(SKED_GUITool_vex.main)),
    ]))


if __name__ == "__main__":
    if os.environ.get('FLET_FORCE_WEB_SERVER', '').lower() in ('1', 'true') or os.environ.get('PORT'):
        ft.app(target=main, view=None, host='0.0.0.0',
               assets_dir=str(ROOT / 'assets'),
               port=int(os.environ.get('PORT', os.environ.get('FLET_SERVER_PORT', '8000'))))
    else:
        ft.app(target=main, assets_dir=str(ROOT / 'assets'))
