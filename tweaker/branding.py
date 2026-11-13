"""Product branding and on-disk compatibility identifiers (never migrate journals)."""
import os
from pathlib import Path

APP_NAME = 'ApexxTweaks'
# These identifiers must remain byte-for-byte stable for older installs.
LEGACY_APP_NAME = 'FrameWise'
OPTIONAL_TASK_PATHS = (f'\\{APP_NAME}Optional\\', f'\\{LEGACY_APP_NAME}Optional\\')
JOURNAL_MUTEX = f'Local\\{LEGACY_APP_NAME}Journal'


def data_directory(base=None):
    """Reuse existing data in place so absolute snapshot paths and undo stay valid.

    New installs use the product name. Never silently choose between two populated
    stores, merge journals, move backups, or rewrite historical action identifiers.
    """
    base = Path(base) if base is not None else Path(os.environ.get('LOCALAPPDATA', Path.home()/'.local/share'))
    current, legacy = base / APP_NAME, base / LEGACY_APP_NAME
    legacy_used = legacy.is_dir() and any(legacy.iterdir())
    current_used = current.is_dir() and any(current.iterdir())
    if legacy_used and current_used:
        raise RuntimeError(
            f'Two populated application data stores found: {current} and {legacy}. '
            'Neither was modified. Preserve both folders and resolve the stores before applying changes; '
            'see the upgrade instructions for restoring each journal separately.'
        )
    return legacy if legacy_used else current


def branded_text(text):
    """Rebrand human-readable saved metadata, never machine targets or backup paths."""
    text = text.replace(OPTIONAL_TASK_PATHS[1], 'the legacy optional-app task folder')
    return text.replace(LEGACY_APP_NAME, APP_NAME).replace(LEGACY_APP_NAME.upper(), APP_NAME)
