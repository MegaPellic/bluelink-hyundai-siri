from flask import Flask, jsonify, request
from hyundai_kia_connect_api import VehicleManager
from hyundai_kia_connect_api.ApiImpl import WindowRequestOptions
from hyundai_kia_connect_api.const import WINDOW_STATE
import time
import os
import hmac
import threading

app = Flask(__name__)

# ── Configurazione (passata con "docker run -e ...") ────────────
USERNAME = os.environ["BLUELINK_USERNAME"]
PASSWORD = os.environ["BLUELINK_PASSWORD"]
PIN      = os.environ["BLUELINK_PIN"]
API_KEY  = os.environ["API_KEY"]
COMMAND_COOLDOWN = 30  # secondi tra un comando e l'altro
# ────────────────────────────────────────────────────────────────

last_command_time = 0
_vm = None
_vm_lock = threading.Lock()

@app.before_request
def check_key():
    key = request.args.get("key") or request.headers.get("X-API-Key") or ""
    if not hmac.compare_digest(key, API_KEY):
        return jsonify({"ok": False, "error": "Non autorizzato"}), 401

def check_cooldown():
    global last_command_time
    now = time.time()
    elapsed = now - last_command_time
    if elapsed < COMMAND_COOLDOWN:
        remaining = int(COMMAND_COOLDOWN - elapsed)
        return False, remaining
    last_command_time = now
    return True, 0

def get_vm():
    # Una sola sessione riusata: ogni login completo può disconnettere l'app MyHyundai
    global _vm
    with _vm_lock:
        if _vm is None:
            _vm = VehicleManager(
                region=1,
                brand=2,
                username=USERNAME,
                password=PASSWORD,
                pin=PIN,
                language="it"
            )
        try:
            _vm.check_and_refresh_token()
            _vm.update_all_vehicles_with_cached_state()
        except Exception:
            _vm = None
            raise
        return _vm

def get_vehicle(vm):
    return list(vm.vehicles.values())[0]

@app.route("/status")
def status():
    try:
        vm = get_vm()
        v  = get_vehicle(vm)
        return jsonify({
            "ok": True,
            "nickname": v.name,
            "locked": v.is_locked,
            "odometer": v.odometer,
            "engine": v.engine_is_running,
            "climate": v.air_control_is_on,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/lock")
def lock():
    ok, remaining = check_cooldown()
    if not ok:
        return jsonify({"ok": False, "error": f"Aspetta {remaining} secondi"}), 429
    try:
        vm = get_vm()
        v  = get_vehicle(vm)
        vm.lock(v.id)
        return jsonify({"ok": True, "action": "lock"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/unlock")
def unlock():
    ok, remaining = check_cooldown()
    if not ok:
        return jsonify({"ok": False, "error": f"Aspetta {remaining} secondi"}), 429
    try:
        vm = get_vm()
        v  = get_vehicle(vm)
        vm.unlock(v.id)
        return jsonify({"ok": True, "action": "unlock"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/location")
def location():
    try:
        vm = get_vm()
        v  = get_vehicle(vm)
        lat = v.location_latitude
        lon = v.location_longitude
        return jsonify({
            "ok": True,
            "latitude": lat,
            "longitude": lon,
            "updated": str(v.location_last_updated_at),
            "maps_url": f"https://maps.apple.com/?ll={lat},{lon}&q=Hyundai",
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/windows/open")
def windows_open():
    ok, remaining = check_cooldown()
    if not ok:
        return jsonify({"ok": False, "error": f"Aspetta {remaining} secondi"}), 429
    try:
        vm = get_vm()
        v  = get_vehicle(vm)
        options = WindowRequestOptions(
            front_left=WINDOW_STATE.OPEN,
            front_right=WINDOW_STATE.OPEN,
            back_left=WINDOW_STATE.OPEN,
            back_right=WINDOW_STATE.OPEN,
        )
        vm.set_windows_state(v.id, options)
        return jsonify({"ok": True, "action": "windows_open"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/windows/close")
def windows_close():
    ok, remaining = check_cooldown()
    if not ok:
        return jsonify({"ok": False, "error": f"Aspetta {remaining} secondi"}), 429
    try:
        vm = get_vm()
        v  = get_vehicle(vm)
        options = WindowRequestOptions(
            front_left=WINDOW_STATE.CLOSED,
            front_right=WINDOW_STATE.CLOSED,
            back_left=WINDOW_STATE.CLOSED,
            back_right=WINDOW_STATE.CLOSED,
        )
        vm.set_windows_state(v.id, options)
        return jsonify({"ok": True, "action": "windows_close"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/windows/ventilation")
def windows_ventilation():
    ok, remaining = check_cooldown()
    if not ok:
        return jsonify({"ok": False, "error": f"Aspetta {remaining} secondi"}), 429
    try:
        vm = get_vm()
        v  = get_vehicle(vm)
        options = WindowRequestOptions(
            front_left=WINDOW_STATE.VENTILATION,
            front_right=WINDOW_STATE.VENTILATION,
            back_left=WINDOW_STATE.VENTILATION,
            back_right=WINDOW_STATE.VENTILATION,
        )
        vm.set_windows_state(v.id, options)
        return jsonify({"ok": True, "action": "windows_ventilation"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765)
