"""Text-only exchange shared by desktop and browser editors."""
from pathlib import Path
from functools import wraps
from threading import RLock
import flet as ft

from schedule_text import normalize_text
from iers_status import check_iers

_PLOT_LOCK = RLock()


def plot_action(page):
    """Keep progress visible through IERS lookup, calculation and rendering."""
    def decorate(function):
        @wraps(function)
        def run(*args, **kwargs):
            message = ft.Text('Preparing plot. Please wait...')
            dialog = ft.AlertDialog(modal=True, title=ft.Text('Processing'),
                content=ft.Column([ft.ProgressRing(), message], tight=True))
            previous = getattr(page, 'dialog', None)
            page.dialog = dialog
            page._schedule_progress = message
            dialog.open = True
            page.update()
            try:
                # pyplot has process-global state; serialize plots across sessions.
                with _PLOT_LOCK:
                    return function(*args, **kwargs)
            finally:
                dialog.open = False
                page.update()
                page.dialog = previous
                page._schedule_progress = None
        return run
    return decorate


def prepare_iers(page, status, scans):
    """Show acquisition status on any tab before blocking on network access."""
    message = 'Checking IERS data; downloading if needed. Please wait...'
    status.value = message
    progress = getattr(page, '_schedule_progress', None)
    if progress is not None:
        progress.value = message
        page.update()
        try:
            status.value = check_iers(scans)
        except Exception as error:
            status.value = str(error)
            raise
        progress.value = 'Computing and rendering plot. Please wait...'
        page.update()
        return status.value
    dialog = ft.AlertDialog(modal=True, title=ft.Text('IERS data'),
        content=ft.Column([ft.ProgressRing(), ft.Text(message)], tight=True))
    previous = getattr(page, 'dialog', None)
    page.dialog = dialog
    dialog.open = True
    page.update()
    try:
        status.value = check_iers(scans)
        return status.value
    except Exception as error:
        status.value = str(error)
        raise
    finally:
        dialog.open = False
        page.update()
        page.dialog = previous


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
    dialog = ft.AlertDialog(title=ft.Text('Output (copy and save)'),
        content=ft.Container(ft.Column(controls, scroll=ft.ScrollMode.ALWAYS),
                             width=700, height=500),
        actions=[ft.TextButton('Close', on_click=close)])
    page.dialog = dialog
    dialog.open = True
    page.update()


def show_paste(page, apply, title='Import from text', label='Paste DRG / VEX text'):
    field = ft.TextField(label=label, multiline=True)
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
    dialog = ft.AlertDialog(title=ft.Text(title),
        content=ft.Container(ft.Column([field, status], scroll=ft.ScrollMode.ALWAYS),
                             width=700, height=450),
        actions=[ft.TextButton('Apply', on_click=submit), ft.TextButton('Close', on_click=close)])
    page.dialog = dialog
    dialog.open = True
    page.update()
