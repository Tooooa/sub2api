# OAuth authorization failure alerts

This standalone Python 3.9+ monitor reads current OpenAI OAuth account error
metadata from both relay databases over existing SSH keys. It never changes
accounts, credentials, scheduling, quota or subscriptions, and never generates
model requests. OAuth tokens are not selected. Raw provider errors are reduced
to known error markers on the server before being returned to the Mac.

All currently registered OpenAI OAuth accounts are inspected, but an identity is
eligible for alerts only if it had a successful request within the last seven
days, is still configured for scheduling, or was observed healthy and scheduled
within that window. A new authorization failure can disable scheduling, so
disabled status alone never excludes an account that was recently in use.
Disabled historical accounts without recent usage are omitted. This is a usage
filter, not a claim that the owner intentionally retired those accounts.

Private `ignored_accounts` entries (case-insensitive emails or `upstream:ID` keys)
override all eligibility rules for accounts the owner explicitly no longer uses.
`recent_use_days` adjusts the seven-day window. Removed accounts, API-key
providers and local-only Cockpit accounts are excluded. Account identity is the
upstream ChatGPT account ID, falling back to a case-insensitive email, so
duplicate records across both sites are reported together.

Each alert identifies the email, site and account ID, registered plan (which may
be stale), current scheduling status, per-site last successful request, and
successful request count over the last seven days. Missing usage is labelled
"no success found in retained logs", never "never used". The account/time index
on usage_logs is used for the bounded usage queries; database statement timeout
is 20 seconds. No request payload or response content is selected.

## Delivery rules

- Poll every five minutes. An authorization error must be observed twice with
  at least five minutes between first and confirming observation. Normal delay
  is approximately five to ten minutes; sleep and network failure extend it.
- Recognize revoked/expired/invalid OAuth credentials, reused refresh tokens
  and upstream 401. Expiry timestamps alone, HTTP 403, quota exhaustion and
  network failures are insufficient evidence of authorization failure.
- Each incident is notified once, even if its error text or affected site
  changes. Rearm only after two fully observed healthy checks at least five
  minutes apart. An unreachable site never clears a previous failure.
- Three failed site checks spanning ten minutes produce a separate monitoring
  outage notification, explicitly stating that account status is unknown.
- Batch current incidents into messages of up to 20 accounts. A failed delivery
  remains pending. State updates are atomic and concurrent invocations use an
  exclusive OS file lock. Corrupt state stops the run without sending; preserve
  it for diagnosis instead of deleting it and generating repeat alerts.
- Delivery uses the owner's `feishu-ask notify` bot and a dedicated persistent
  topic. No response or auto-resume listener is started. A crash after remote
  delivery but before local persistence can cause one duplicate on retry.

These are server-reported runtime errors, not fresh independent upstream probes.
Healthy credentials with stale server error state require operator reconciliation;
the monitor reports the remaining server error rather than testing or fixing it.

## Run and install

Copy `config.example.json` to a private directory outside Git and set the two
SSH targets, owner-installed `feishu_ask` path and external `state_path`. Optional
`lark_cli` chooses the installed Lark CLI in the LaunchAgent environment.

```sh
python3 tools/account-auth-alerts/monitor.py --config /external/private/auth-alerts/config.json
python3 tools/account-auth-alerts/monitor.py --config /external/private/auth-alerts/config.json --send
python3 -m unittest discover -s tools/account-auth-alerts -p 'test_*.py' -v
python3 tools/account-auth-alerts/install-macos.py \
  --config /external/private/auth-alerts/config.json \
  --runtime-dir /external/tools/account-auth-alerts \
  --backup-dir /external/backups/auth-alerts-install
```

Preview does not send or persist incident state. For an explicitly requested
initial summary of already-known persistent failures, use `--send
--confirmations 1 --minimum-age 0` once; later scheduled runs retain the default
two-observation policy. Preserve `state.json` between upgrades. The installer
backs up files it replaces and writes an installation manifest. It preserves
config and incident state.

The LaunchAgent is `com.toooa.sub2api.account-auth-alerts`. Runtime, configuration,
state, reports and backups remain on the external volume. The required plist,
small launcher and a startup log capped at about 1 MiB reside under the user's
Library because launchd can reject startup/log files on removable volumes.
This local task does not need Codex or a model session to run; the Mac must be
awake, logged in, and able to access both SSH targets and Feishu.

```sh
launchctl print "gui/$(id -u)/com.toooa.sub2api.account-auth-alerts"
launchctl kickstart "gui/$(id -u)/com.toooa.sub2api.account-auth-alerts"
launchctl bootout "gui/$(id -u)/com.toooa.sub2api.account-auth-alerts"
```

The older daily `account-pro-alerts` job has separate scope, renewal rules and
state; this monitor does not change that policy. Its installed wrapper was
observed still targeting retired Los Angeles on 2026-11-15, so it must not be
treated as proof that current authorization alerts are covered.

The installed Codex heartbeat `automation-8` runs a daily 09:05 health check of
this LaunchAgent and one deduplicated script pass. The five-minute polling itself
does not consume a model session and does not depend on Codex being open.
