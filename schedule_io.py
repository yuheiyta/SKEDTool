"""Text-only exchange shared by desktop and browser editors."""
from pathlib import Path
import flet as ft

from schedule_text import normalize_text


def show_outputs(page, outputs):
    """Copy and manual-selection fallback; no server download URL."""
    controls = []
    def close(e):
        dialog.open = False
        page.update()
    for name, text in outputs.items():
        controls.extend([
            ft.Text(name),
            ft.TextField(value=text, multiline=True, read_only=True,
                         min_lines=6, max_lines=12),
            ft.ElevatedButton('Copy ' + name,
                on_click=lambda e, value=text: page.set_clipboard(value)),
        ])
    dialog = ft.AlertDialog(title=ft.Text('出力（コピーして保存）'),
        content=ft.Container(ft.Column(controls, scroll=ft.ScrollMode.ALWAYS),
                             width=700, height=500),
        actions=[ft.TextButton('Close', on_click=close)])
    page.dialog = dialog
    dialog.open = True
    page.update()


def show_paste(page, apply):
    field = ft.TextField(label='DRG / VEX テキストを貼り付け', multiline=True)
    status = ft.Text('')
    def submit(e):
        try:
            apply(normalize_text(field.value))
        except Exception as error:
            status.value = str(error)
        else:
            dialog.open = False
        page.update()
    def close(e):
        dialog.open = False
        page.update()
    dialog = ft.AlertDialog(title=ft.Text('テキストから読み込み'),
        content=ft.Container(ft.Column([field, status], scroll=ft.ScrollMode.ALWAYS),
                             width=700, height=450),
        actions=[ft.TextButton('Apply', on_click=submit), ft.TextButton('Close', on_click=close)])
    page.dialog = dialog
    dialog.open = True
    page.update()
