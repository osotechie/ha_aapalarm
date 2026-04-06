# Changelog

## 2026.4.6 — Security & Quality Improvements

### Security Fixes (P0 — Critical)

- **Disarm code validation** — disarm now verifies the user-supplied code matches the configured area code before sending to the alarm. During exit delay (PENDING state), codeless disarm is still permitted. The configured code is always sent to the controller, never raw user input.
- **Keypress input sanitization** — the `aap_alarm_keypress` service now validates all input against an allowlist of valid AAP keypad characters (`0-9`, `A`, `B`, `C`, `E`, `H`, `N`, `R`, `S`, `X`). The `P` (PROG) key is excluded for safety. Input is normalised to uppercase and capped at 16 characters.
- **Removed hardcoded "0000" code** — the vestigial `code = "0000"` passed to the `AAPAlarmPanel` constructor has been removed. An empty string is passed instead; per-area codes are handled separately.
- **Panic trigger code verification** — new `code_panic_required` option (per area, defaults to true) controls whether a valid code is needed to trigger panic. Configurable during setup.
- **Arm code validation** — `arm_home` and `arm_away` now validate the user-supplied code when `code_arm_required` is true. `arm_away` no longer sends the code via `send_keypress()` — it uses `arm_away()` as intended.

### Security Fixes (P1 — High Priority)

- **Sensitive logging downgraded** — host, port, connection type, keepalive, and timeout are now logged at DEBUG level instead of INFO. Lifecycle messages remain at INFO.

### Reliability & Best Practices (P2)

- **Connection timeout** — `await sync_connect` is now wrapped with `asyncio.wait_for()` using the configured timeout. Config entry path raises `ConfigEntryNotReady` for automatic retry with exponential backoff.
- **YAML connection failure fix** — the YAML path `connection_fail_callback` now correctly sets `set_result(False)` instead of `True`. Removed unnecessary stop listener registration on failure.
- **Dispatcher subscription cleanup** — all entities now register dispatcher unsubscribe callbacks via `self.async_on_remove()`, preventing memory leaks on reload/remove.
- **Config flow connection testing** — IP connections are now tested with a TCP socket connection (5s timeout) before proceeding. Serial port paths are validated against `/dev/tty*` and `COM*` patterns, blocking path traversal attacks.
- **Unique ID in config flow** — `async_set_unique_id()` and `_abort_if_unique_id_configured()` prevent duplicate config entries for the same alarm panel connection.
- **HA stop listener for config entries** — `EVENT_HOMEASSISTANT_STOP` listener is now registered on successful connection in the config entry path, ensuring clean shutdown and avoiding stale connections on restart.
- **Deprecated `hass.loop` replaced** — replaced with `asyncio.get_event_loop()` in both setup paths.

### Code Quality (P3)

- **Fixed duplicate error logging** in `switch.py` — removed copy-paste duplicate `_LOGGER.error` line.
- **Pure `is_on` property** in switch — removed side effect that was mutating `self._state` inside the property getter.
- **Removed unused import** — `AAPAlarmPanel` import removed from `config_flow.py`.
- **Added `iot_class`** to `manifest.json` — set to `"local_push"`.
- **Dynamic `sw_version`** — `DeviceInfo` now reads the version from `manifest.json` at module load instead of a hardcoded value.
- **Unit test suite** — added `tests/test_security.py` with 37 tests covering disarm/arm/panic code validation, keypress sanitization, serial port validation, and switch property purity.

## 2025.10.6 — Setup Improvements

1. Setup now done via Integrations page within HA (no more YAML 😁)
2. The integration will create 4 devices with sub entities (Areas, Zones, Outputs and System)
3. Zone Entity names have been cleaned up to just reflect the Zone Name you provide
4. Output Entity names have also been cleaned up to just reflect the Output Name you provide
5. System Status are now individual entities instead of a single entity with attributes to make it easier to create automations of system status changes
6. Including a number of other minor tweaks and fixes