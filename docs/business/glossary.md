# Glossary

| Term | Meaning | Name in the code |
|---|---|---|
| Gateway | This service: a REST API in front of a modem driven by Gammu | `sms_gateway` |
| Gammu | Library and tools that talk to phones and modems | `libGammu`, `python-gammu` |
| SMSD | The Gammu daemon: sends the outbox and stores received SMS in the database | `gammu-smsd`, `libgsmsd` |
| Gammu schema version | Structure version of the tables. SMSD refuses any other version than its own | `gammu.Version`, `GAMMU_SCHEMA_VERSION` |
| Part (physical SMS) | One SMS on the network. A long text is split into several parts | one row of `Inbox`, `SentItem`, `OutboxMultipart` |
| Message (logical SMS) | The text as written by the sender, made of one or more parts | `InboxMessage`, identified by `MessageID` |
| Inbox | Received SMS | table `inbox`, route `/v1/inbox` |
| Outbox | SMS waiting to be sent by SMSD. They leave the table once processed | tables `outbox`, `outbox_multipart`, route `/v1/outbox` |
| Sent items | SMS processed by SMSD, one row per part | table `sentitems`, route `/v1/sentitems` |
| Incomplete message | A message with fewer stored parts than announced | `Complete = false` |
| Injection | Writing a message to the outbox tables through python-gammu | `GammuSmsSender`, `InjectSMS` |
| Security mode | How the SMS routes are protected: `None`, `Bearer` or `Basic` | `API_SECURITY`, `AuthMode` |
| Webhook | `POST` sent to the application at `WEBHOOK_URL` for each new complete message | `WebhookWorker` |
| Marker | The highest `MessageID` at first activation: the webhook only sends what comes after | `webhook_state.StartMessageID` |
| Retention | Number of days SMS are kept when the purge is enabled | `RETENTION_DAYS`, `purge_old_messages` |
| Dummy phone | Gammu's simulated phone, backed by a folder. Used by the end-to-end tests | `model = dummy` |
| Heartbeat | The regular refresh of `phones.TimeOut` by SMSD. A past value means SMSD stopped reporting | `read_phone_status` |
