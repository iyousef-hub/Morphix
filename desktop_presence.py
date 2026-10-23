"""Keep the small Morphix background helper out of the Dock/taskbar.

Only explicitly opening Studio shows a regular macOS Dock entry. Windows taskbar
naturally hides the application when no normal top-level windows are visible.
Runs exclusively on the Qt/AppKit GUI thread.
"""
from __future__ import annotations
import platform


def set_studio_visible(visible: bool):
    if platform.system() != 'Darwin':
        return
    try:
        from AppKit import (NSApplication, NSApplicationActivationPolicyAccessory,
                            NSApplicationActivationPolicyRegular)
        app = NSApplication.sharedApplication()
        policy = (NSApplicationActivationPolicyRegular if visible
                  else NSApplicationActivationPolicyAccessory)
        app.setActivationPolicy_(policy)
        if visible:
            app.activateIgnoringOtherApps_(True)
    except Exception as exc:
        print(f'[Morphix] Dock visibility adjustment unavailable: {exc}', flush=True)
