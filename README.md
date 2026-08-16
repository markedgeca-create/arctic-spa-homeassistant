# Arctic Spa for Home Assistant

A custom integration that connects a Home Assistant instance to an Arctic Spas hot tub
through the official [Arctic Spas public API](https://api.myarcticspa.com/docs) — the same
cloud service the Arctic Spas iPhone/Android app and myarcticspa.com use.

Setup is a single API token pasted into a UI config flow. No YAML, no Balboa module,
no reverse engineering.

## What you get

Entities are created only for hardware your spa actually reports, so a tub without a
fogger or a second blower simply won't get those entities.

| Entity | Type | Notes |
| --- | --- | --- |
| Arctic Spa | `climate` | Water temperature and setpoint, 59–104 °F |
| Lights | `light` | On/off |
| Pump 1–5 | `switch` | Only the pumps your spa has |
| Pump 1 speed | `select` | `off` / `low` / `high` for the two-speed pump |
| Blower 1–2 | `switch` | Only the blowers your spa has |
| SDS, YESS, Fogger | `switch` | Only if enabled on the spa |
| Filtration | `switch` | Write-only on the API, so it shows as an assumed state |
| Easy Mode | `switch` | Write-only on the API, so it shows as an assumed state |
| Suspend filtering when hot | `switch` | Filter suspension during overtemp |
| Filter frequency / duration | `number` | Cycles per day, hours per cycle |
| Boost | `button` | Fires a one-shot boost cycle |
| pH, ORP, and their status | `sensor` | Spa Boy® equipped tubs only |
| Filter status | `sensor` | Idle / Purge / Filtering / Suspended / … |
| Error | `sensor` | First active error code, full list on attributes |
| Problem | `binary_sensor` | On whenever the spa reports any error |
| Connectivity | `binary_sensor` | Whether the cloud can reach the spa |
| Spa Boy / Spa Boy producing | `binary_sensor` | Spa Boy® equipped tubs only |

## Requirements

- Home Assistant 2025.2 or newer
- An Arctic Spas account with the spa already connected to Wi‑Fi and visible in the app
- An API token (below)

## Getting an API token

1. Sign in at <https://myarcticspa.com> with the same account you use in the Arctic Spas app.
2. Go to <https://myarcticspa.com/spa/SpaAPIManagement.aspx> (**My Spa → Spa API Management**).
3. Generate a token and copy it. Treat it like a password — it grants full control of the spa.

If the API Management page isn't available on your account, contact Arctic Spas support and
ask for API access to be enabled.

## Installation

### Via HACS (recommended)

1. In Home Assistant, open **HACS**.
2. Click the three-dot menu (⋮) in the top-right corner, then **Custom repositories**.
3. Paste this repository's URL, choose category **Integration**, and click **Add**.
4. Find **Arctic Spa** in HACS, click **Download**, and restart Home Assistant.

### Manual

Copy `custom_components/arctic_spa` into your Home Assistant `config/custom_components/`
directory and restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & services**.
2. Click **+ Add integration** and search for **Arctic Spa**.
3. Paste the API token and submit.

To change how often the spa is polled, click **Configure** on the integration entry.
The default is 60 seconds.

## Rate limits

Arctic Spas caps the status endpoint at **15 calls per minute**. This integration makes one
status call per polling interval, plus one extra roughly 12 seconds after any command
(the cloud lags the spa, so an immediate re-read would return stale values). The default
60-second interval leaves ample headroom; the minimum configurable interval is 30 seconds.

If the API starts returning HTTP 429, raise the polling interval.

## Known limitations

- **Cloud only.** Everything goes through Arctic Spas' servers; there is no local API on the
  spa's controller. If your internet or their service is down, the integration goes
  unavailable. The `connected` binary sensor reflects whether their cloud can reach the spa.
- **Filtration and Easy Mode are write-only.** The status endpoint never reports them back,
  so those two switches show their last commanded state and are marked as assumed state.
- **No heater relay state.** `hvac_action` is inferred by comparing current temperature to
  setpoint.
- **Temperatures are Fahrenheit at the API.** Home Assistant converts them to your configured
  unit automatically.

## Example automation

Notify when the spa reports a fault (such as a FLO flow error):

```yaml
alias: Spa - Notify On Error
id: spa_notify_on_error
triggers:
  - trigger: state
    entity_id: binary_sensor.arctic_spa_problem
    to: "on"
    for: "00:05:00"
conditions: []
actions:
  - action: notify.persistent_notification
    data:
      title: Hot tub error
      message: >-
        The spa is reporting {{ states('sensor.arctic_spa_error') }}
        (water is {{ states('sensor.arctic_spa_temperature') }}°).
mode: single
```

## Disclaimer

Not affiliated with, endorsed by, or supported by Arctic Spas / Blue Falls Manufacturing.
"Arctic Spas", "Spa Boy", and "YESS" are trademarks of their respective owners.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
