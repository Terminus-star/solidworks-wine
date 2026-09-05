#!/usr/bin/env python3
"""Control SOLIDWORKS Installation Manager when WebView2 is not presented by Wine."""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

import websocket

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from solidworks_wine.credentials import redact


DEBUG_URL = os.environ.get("SOLIDWORKS_CDP_URL", "http://127.0.0.1:9222")


class BridgeError(RuntimeError):
    pass


class DevTools:
    def __init__(self) -> None:
        candidates = [DEBUG_URL]
        if 'SOLIDWORKS_CDP_URL' not in os.environ:
            candidates.append('http://[::1]:9222')
        targets = None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for candidate in candidates:
            try:
                with opener.open(f"{candidate}/json/list", timeout=2) as response:
                    targets = json.load(response)
                break
            except Exception:
                continue
        if targets is None:
            raise BridgeError(f"WebView2 bridge is unavailable at {', '.join(candidates)}")

        pages = [target for target in targets if target.get("type") == "page"]
        if not pages:
            raise BridgeError("WebView2 did not publish an installer page.")

        target = next(
            (page for page in pages if "Installation%20Manager%20Data" in page.get("url", "")),
            pages[0],
        )
        try:
            self.socket = websocket.create_connection(
                target["webSocketDebuggerUrl"],
                timeout=10,
                http_proxy_host=None,
                http_no_proxy=['127.0.0.1', '::1', 'localhost'],
                suppress_origin=True,
            )
        except Exception as exc:
            raise BridgeError(f"Could not connect to the installer page: {exc}") from exc
        self.message_id = 0

    def call(self, method: str, params: dict | None = None) -> dict:
        self.message_id += 1
        request_id = self.message_id
        try:
            self.socket.send(
                json.dumps({"id": request_id, "method": method, "params": params or {}})
            )
            while True:
                message = json.loads(self.socket.recv())
                if message.get("id") != request_id:
                    continue
                if "error" in message:
                    raise BridgeError(f"DevTools {method} failed: {message['error']}")
                return message.get("result", {})
        except (websocket.WebSocketException, OSError) as exc:
            self.socket.close()
            raise BridgeError(f"Installer page connection interrupted during {method}; check status before repeating an action") from exc

    def evaluate(self, expression: str):
        response = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": True,
                "returnByValue": True,
            },
        )
        result = response.get("result", {})
        if "exceptionDetails" in response:
            raise BridgeError(f"Installer script failed: {response['exceptionDetails']}")
        return result.get("value")

    def text(self) -> str:
        return redact(self.evaluate("document.body ? document.body.innerText : ''") or "")


def connect_when_ready(timeout: float = 120.0) -> DevTools:
    deadline = time.monotonic() + timeout
    last_error = "installer page is not ready"
    while time.monotonic() < deadline:
        bridge = None
        try:
            bridge = DevTools()
            if bridge.evaluate("document.readyState") == "complete":
                return bridge
            last_error = "installer page has not finished loading"
        except BridgeError as exc:
            last_error = str(exc)
        if bridge is not None:
            bridge.socket.close()
        time.sleep(1)
    raise BridgeError(last_error)


def wait_for_new_page(previous_text: str, timeout: float = 60.0) -> str:
    deadline = time.monotonic() + timeout
    last_text = previous_text
    while time.monotonic() < deadline:
        bridge = None
        try:
            bridge = DevTools()
            current_text = bridge.text()
            if current_text and current_text != previous_text:
                return current_text
            last_text = current_text
        except BridgeError:
            pass
        finally:
            if bridge is not None:
                bridge.socket.close()
        time.sleep(1)
    return last_text


def click_button(button_id: str, wait: bool = True) -> None:
    bridge = connect_when_ready()
    previous_text = bridge.text()
    argument = button_id if button_id.isdecimal() else json.dumps(button_id)
    bridge.evaluate(f"OnHTML_BUTTON({argument})")
    if not wait:
        return
    current_text = wait_for_new_page(previous_text)
    if current_text == previous_text:
        raise BridgeError("The installer did not advance after the button action.")
    print(current_text)


def click_text_button(label: str, wait: bool = True) -> None:
    bridge = connect_when_ready()
    previous_text = bridge.text()
    quoted_label = json.dumps(label)
    point = bridge.evaluate(f"""(() => {{
        const normalize = text => (text || '').replace(/\\s+/g, ' ').trim();
        const element = Array.from(document.querySelectorAll('.footerbutton .button_enabled, button, [role=button], .footerbutton'))
            .find(item => normalize(item.textContent || item.value) === {quoted_label});
        if (!element) return null;
        const rect = element.getBoundingClientRect();
        return {{x: rect.left + rect.width / 2, y: rect.top + rect.height / 2}};
    }})()""")
    if not point:
        raise BridgeError(f"Missing installer button labeled {label!r}.")
    bridge.call("Input.dispatchMouseEvent", {
        "type": "mouseMoved", "x": point["x"], "y": point["y"],
    })
    bridge.call("Input.dispatchMouseEvent", {
        "type": "mousePressed", "x": point["x"], "y": point["y"],
        "button": "left", "buttons": 1, "clickCount": 1,
    })
    bridge.call("Input.dispatchMouseEvent", {
        "type": "mouseReleased", "x": point["x"], "y": point["y"],
        "button": "left", "buttons": 0, "clickCount": 1,
    })
    if not wait:
        return
    current_text = wait_for_new_page(previous_text)
    if current_text == previous_text:
        raise BridgeError("The installer did not advance after the text button action.")
    print(current_text)


def list_buttons() -> None:
    bridge = connect_when_ready()
    buttons = bridge.evaluate("""Array.from(new Set([
        ...document.querySelectorAll('button, input[type=button], input[type=submit], [onclick], a, [role=button]'),
        ...Array.from(document.querySelectorAll('*')).filter(element =>
            /^(Back|Next|Cancel|Finish|Help)$/i.test((element.textContent || '').trim()))
    ])).map(button => ({
        tag: button.tagName || '',
        id: button.id || '',
        className: button.className || '',
        checked: typeof button.checked === 'boolean' ? button.checked : null,
        value: /^EDIT\\d+$/.test(button.id)
            ? (button.value ? '[redacted:set]' : '[redacted:empty]')
            : (button.value || button.innerText || ''),
        onclick: button.getAttribute('onclick') || '',
        href: button.getAttribute('href') || ''
    }))""")
    print(json.dumps(buttons, indent=2))


def set_checkbox(checkbox_id: int, checked: bool) -> None:
    bridge = connect_when_ready()
    result = bridge.evaluate(f"""(() => {{
        const field = document.getElementById('checkBox_{checkbox_id}');
        if (!field) throw new Error('Missing checkbox {checkbox_id}');
        field.checked = {str(checked).lower()};
        OnHTML_CHECKBOX(field, {checkbox_id});
        return field.checked;
    }})()""")
    if result is not checked:
        raise BridgeError(f"Installer rejected checkbox {checkbox_id}.")
    time.sleep(1)
    print(connect_when_ready().text())


def select_radio(radio_id: int) -> None:
    bridge = connect_when_ready()
    result = bridge.evaluate(f"""(() => {{
        const field = Array.from(document.querySelectorAll('input[type=radio]'))
            .find(item => item.getAttribute('onClick')?.includes(', {radio_id})'));
        if (!field) throw new Error('Missing radio {radio_id}');
        field.checked = true;
        OnHTML_RADIO(field, {radio_id});
        return field.checked;
    }})()""")
    if result is not True:
        raise BridgeError(f"Installer rejected radio {radio_id}.")
    time.sleep(1)
    print(connect_when_ready().text())


def enter_serial() -> None:
    serial_input = (
        getpass.getpass("SOLIDWORKS serial (input hidden): ")
        if sys.stdin.isatty()
        else sys.stdin.readline()
    )
    serial = re.sub(
        r"[^A-Za-z0-9]",
        "",
        serial_input,
    ).upper()
    serial_input = ""
    if not re.fullmatch(r"[0-9]{16}[A-Z0-9]{8}", serial):
        raise BridgeError("The serial must contain 16 digits followed by 8 letters/digits.")

    bridge = connect_when_ready()
    previous_text = bridge.text()
    if "Serial Number" not in previous_text:
        raise BridgeError("Installation Manager is not on the serial-number page.")

    for index in range(6):
        field_value = serial[index * 4 : (index + 1) * 4]
        expression = f"""(() => {{
            const field = document.getElementById('EDIT{index}');
            if (!field) throw new Error('Missing serial field EDIT{index}');
            field.value = {json.dumps(field_value)};
            OnHTML_EDIT(field, {index}, 99);
            OnHTML_EDIT(field, {index}, 97);
            return field.value.length;
        }})()"""
        if bridge.evaluate(expression) != 4:
            raise BridgeError(f"Installer rejected serial field {index + 1}.")

    combined = bridge.evaluate(
        "Array.from({length: 6}, (_, i) => "
        "document.getElementById('EDIT' + i).value).join('')"
    )
    if combined != serial:
        raise BridgeError("Serial verification failed before submission.")

    # Do not retain or print the credential after its fields are populated.
    serial = ""
    combined = ""
    bridge.evaluate("OnHTML_BUTTON(5002)")
    current_text = wait_for_new_page(previous_text, timeout=120)
    if current_text == previous_text:
        raise BridgeError("The installer did not advance after serial submission.")
    print(current_text)


def capture(path: Path) -> None:
    bridge = connect_when_ready()
    response = bridge.call(
        "Page.captureScreenshot",
        {"format": "png", "captureBeyondViewport": False},
    )
    path.write_bytes(base64.b64decode(response["data"]))
    print(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="Print the current installer page text.")
    subparsers.add_parser("buttons", help="List the current installer page buttons.")
    button_parser = subparsers.add_parser("button", help="Invoke an installer button ID.")
    button_parser.add_argument("button_id")
    button_parser.add_argument("--no-wait", action="store_true")
    text_button_parser = subparsers.add_parser("text-button", help="Click a visible installer button label.")
    text_button_parser.add_argument("label")
    text_button_parser.add_argument("--no-wait", action="store_true")
    checkbox_parser = subparsers.add_parser("checkbox", help="Set an installer checkbox ID.")
    checkbox_parser.add_argument("checkbox_id", type=int)
    checkbox_parser.add_argument("state", choices=("on", "off"))
    radio_parser = subparsers.add_parser("radio", help="Select an installer radio ID.")
    radio_parser.add_argument("radio_id", type=int)
    subparsers.add_parser("serial", help="Prompt privately for a serial and submit it.")
    capture_parser = subparsers.add_parser("capture", help="Capture the internal page framebuffer.")
    capture_parser.add_argument("path", type=Path)
    args = parser.parse_args()

    try:
        if args.command == "status":
            print(connect_when_ready().text())
        elif args.command == "buttons":
            list_buttons()
        elif args.command == "button":
            click_button(args.button_id, not args.no_wait)
        elif args.command == "text-button":
            click_text_button(args.label, not args.no_wait)
        elif args.command == "checkbox":
            set_checkbox(args.checkbox_id, args.state == "on")
        elif args.command == "radio":
            select_radio(args.radio_id)
        elif args.command == "serial":
            enter_serial()
        elif args.command == "capture":
            capture(args.path)
    except BridgeError as exc:
        print(f"installer-bridge: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
