# External integrations — status & configuration

Status vocabulary (also returned by `GET /api/v1/external/data-sources`, persisted in `data_source_status`):

| Status | Meaning |
|---|---|
| **LIVE** | Last authenticated request to the real provider succeeded (timestamp recorded). |
| **CONFIGURED** | Credentials/URL present, but no successful request has been recorded yet. |
| **MOCK** | Development-only adapter (`dev_log`). Never reports delivery. Refused when `ENVIRONMENT=production`. |
| **UNAVAILABLE** | Not configured, or the provider failed. The UI shows the data as unavailable, not substituted. |

Production (`ENVIRONMENT=production`) refuses to start if a selected provider is missing its credentials, and never falls back to mock adapters.

| Integration | Env vars | Default | Verified in this repo? | Behaviour when unavailable |
|---|---|---|---|---|
| NADRES (ICAR-NIVEDI) | `NADRES_API_URL`, `NADRES_API_KEY` | UNAVAILABLE | No — no public schema or credentials | No surveillance numbers are shown and nothing is fabricated. The status is UNAVAILABLE. |
| Government surveillance feed (DAHD/state) | `GOVERNMENT_API_URL`, `GOVERNMENT_API_KEY` | UNAVAILABLE | No | Same as above |
| Weather (Open-Meteo) | `WEATHER_PROVIDER=open_meteo` | CONFIGURED (no key needed) | Not reachable from the build sandbox. It becomes LIVE after the first successful fetch in deployment. | Weather factors are omitted from risk context. |
| Lab LIMS | `LAB_PROVIDER`, `LAB_API_URL`, `LAB_API_KEY` | UNAVAILABLE | No | Results are entered manually in the Lab module (`source=MANUAL_ENTRY`). |
| SMS (Fast2SMS) | `SMS_PROVIDER=fast2sms`, `SMS_API_KEY` | UNAVAILABLE | No | Notifications stay `PENDING`/`FAILED`. `DELIVERED` is set only from a provider delivery receipt. |
| WhatsApp Cloud API | `WHATSAPP_PROVIDER=whatsapp_cloud_api`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_APP_SECRET` | UNAVAILABLE | No | Same as above. The webhook requires a valid `X-Hub-Signature-256`. |
| Translation (Google) | `TRANSLATION_PROVIDER=google`, `TRANSLATION_API_KEY` | Local glossary | No | Responses carry `status=FALLBACK_GLOSSARY_PARTIAL` (term substitution only, not a full translation). UI strings use the bundled 8-language i18n files. |
| Routing (OSRM) | `ROUTING_PROVIDER=osrm`, `OSRM_URL` | UNAVAILABLE | No | Straight-line distance is labelled as such, and ETA is `ETA_UNAVAILABLE`. |
| IVR / telephony (Exotel inbound) | `TELEPHONY_PROVIDER=exotel`, `EXOTEL_ENABLED=true`, `EXOTEL_API_KEY`, `EXOTEL_API_TOKEN`, `EXOTEL_ACCOUNT_SID`, `EXOTEL_SUBDOMAIN`, `EXOTEL_PHONE_NUMBER`, `EXOTEL_APP_ID`, `EXOTEL_WEBHOOK_SECRET`, `PUBLIC_API_BASE_URL`, `IVR_ENABLED` | UNAVAILABLE (`TELEPHONY_PROVIDER=mock`, `EXOTEL_ENABLED=false`) | Webhook→ExoML→menu→survey→report→triage→case flow verified end-to-end by `tests/test_ivr_exotel.py` against `MockTelephonyProvider` (46 tests) and by `scripts/ivr_smoke.py` against a live uvicorn (36 checks). A *real* ExoPhone becomes LIVE after the first verified inbound call in deployment — no Exotel account was available here. | `/api/v1/ivr/*` returns a polite ExoML "unavailable" message when `IVR_ENABLED=false`, and `401` for any webhook without the shared secret. Exotel does **not** sign webhooks: trust comes from `EXOTEL_WEBHOOK_SECRET` in the action URL (`?t=`) or the `X-Exotel-Webhook-Secret` header, plus CallSid correlation and optional `EXOTEL_VERIFY_CALL_SID`. See [EXOTEL_SETUP.md](EXOTEL_SETUP.md). |
| Speech-to-text | bundled Whisper (browser, offline) | LIVE (on-device) | Runs locally, no network | — |

To mark an integration LIVE in a deployment, configure it and let the scheduled `external_refresh` job (worker) run. Check `last_success_at` on `/api/v1/external/data-sources`.
