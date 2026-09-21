"""Shared desktop entry point for the JVN and VERA editors."""
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parent
import SKED_GUITool
import SKED_GUITool_vex


def main(page):
    page.title = "JVN / VERA Schedule Tool"

    def start(editor):
        page.controls.clear()
        editor(page)

    page.add(ft.Column([
        ft.Text("Schedule Tool", size=28),
        ft.Text("使用する観測網を選択してください。"),
        ft.ElevatedButton("JVN — DRG", on_click=lambda _: start(SKED_GUITool.main)),
        ft.ElevatedButton("VERA — VEX", on_click=lambda _: start(SKED_GUITool_vex.main)),
    ]))


if __name__ == "__main__":
    ft.app(target=main)
