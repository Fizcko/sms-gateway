# Business rules

## Inbox: messages, not parts

- **R1.** The API exposes one entry per message: all parts sharing a `MessageID`.
- **R2.** The text of a message is the concatenation of its parts by `SequencePosition`. SMSD
  either stores the whole text in the first part (the others stay empty) or each part's own text.
- **R3.** An incomplete message is still returned, with `Complete=false`, `PartCount` and
  `ReceivedParts`. No received SMS is invisible, even when a part never arrives.
- **R4.** The identifier of a message is its `MessageID`: the `ID` of its first stored part. The
  `ID` of a later part gives a 404 on GET, and deletes nothing on DELETE.
- **R5.** DELETE removes every part of the message.
- **R6.** Pagination counts messages. `before` and `after` apply to the message date, which is the
  reception date of its earliest part.
- **R7.** A row whose `MessageID` is still 0 is being written by SMSD and belongs to no message.
- **R8.** Other attributes (`UDH`, `Class`, `SenderNumber`…) come from the lowest position received.
  `Processed` is `true` only when every part is.

## Sending

- **R9.** A request queues one message per recipient and returns each outbox ID.
- **R10.** A message is limited to 480 characters.
- **R26.** A recipient is an optional `+` followed by 3 to 20 digits. One invalid recipient refuses
  the whole request, and nothing is queued.

## Listing filters and deletion

- **R11.** On outbox and sent items, `before` and `after` apply to `SendingDateTime`, `destination`
  to `DestinationNumber`. Each filter works alone.
- **R12.** Sent items stay part-level when reading: the list has one entry per part and GET returns
  the first part. DELETE removes all the parts of the SMS.
- **R27.** Deleting from the outbox also removes the other parts in `outbox_multipart`.
- **R13.** Deleting something that does not exist still answers 204.

## Authentication

- **R14.** `API_SECURITY` protects the SMS routes. `/healthz`, `/v1/login` and the documentation
  are always open. Any value other than `None`, `Bearer` or `Basic` refuses the start.
- **R15.** `/v1/refresh` always needs a valid bearer token, whatever the mode.
- **R16.** `JWT_ACCESS_TOKEN_EXPIRES` is in seconds, and `0` disables expiration.
- **R17.** The service refuses to start when a secret needed by the mode is missing: `API_USERNAME`
  and `API_PASSWORD` for `Basic` and `Bearer`, plus `JWT_SECRET` for `Bearer`. `MYSQL_PASSWORD` is
  always required, and `WEBHOOK_SECRET` with `WEBHOOK_URL`.
- **R18.** Without configured credentials, every login is refused.
- **R28.** After 5 failed logins from one client in 5 minutes, its logins get a 429 with `Retry-After`,
  even with the right password. A success resets the count. The client is the direct peer, never
  `X-Forwarded-For`.

## Errors

- **R19.** An unexpected error returns a generic message to the client. The stack trace goes to the
  logs only.

## Schema

- **R20.** The database is at the Gammu schema version of the bundled Gammu before SMSD or the API
  starts. Only versions 17 and 18 can be migrated: anything else stops the start.
- **R21.** Migrating never links historical parts: each existing inbox row becomes its own message,
  as Gammu prescribes. Queued messages stay eligible every day (`SendDays = 127`).

- **R25.** The schema is identical to the one of the bundled Gammu, on tables, columns and indexes.
  The storage engine is the only accepted difference. A Gammu upgrade that changes the schema needs
  a migration: see *Upgrading Gammu* in `docs/architecture.md`.

## Health

- **R22.** The phone is `connected` when gammu-smsd has a `phones` row whose `TimeOut` is not past,
  on the database clock. No row, or only expired rows, means `disconnected`. Detection can take up
  to `StatusFrequency` + 10 seconds (70 s by default).
- **R23.** `/healthz` answers 200 only when both the database and the phone are connected, and 500
  otherwise, because the gateway cannot send. When the database is down, the phone state is unknown
  and left out.
- **R24.** `/healthz` is open: it exposes the signal and network name, never the IMEI or the IMSI.

## Webhook

- **R29.** Only new messages are sent: those received after the first activation. History is neither
  sent nor modified. Messages received while the webhook is disabled afterwards are sent when it returns.
- **R30.** A complete message gives one `POST`, with the reassembled text and a signature of the body.
  Only a 2xx marks it `Processed='true'`.
- **R31.** Anything else is retried, with delays growing from 5 s to 5 min. Order is kept: later messages
  wait. Delivery is at-least-once, so the receiver must ignore an `ID` already seen.
- **R32.** An incomplete message is not sent, and does not block the others. After
  `WEBHOOK_INCOMPLETE_DELAY` it is logged and marked processed. It stays in the inbox. If a late part
  completes it, it is sent.

## Retention

- **R33.** Without `RETENTION_DAYS`, nothing is ever purged. With it, a message older than this limit
  goes as a whole, once its latest part is, and so do sent items by sending date.
- **R34.** The purge never touches the outbox, nor a message waiting for the webhook.

## Coverage

| Rule | Test |
|---|---|
| R1 | `tests/integration/test_inbox_api.py::test_list_returns_one_entry_per_message` |
| R1 | `tests/integration/test_gammu_end_to_end.py::test_received_multipart_is_exposed_as_one_complete_message` |
| R2 | `tests/unit/test_inbox_assembly.py::test_text_is_joined_in_sequence_order_whatever_the_row_order` |
| R2 | `tests/unit/test_inbox_assembly.py::test_whole_text_stored_in_first_part_is_not_duplicated` |
| R3 | `tests/integration/test_inbox_api.py::test_incomplete_message_is_listed_and_flagged` |
| R3 | `tests/unit/test_inbox_assembly.py::test_message_with_a_missing_part_is_incomplete` |
| R4 | `tests/integration/test_inbox_api.py::test_get_by_message_id_returns_the_whole_message` |
| R4 | `tests/integration/test_inbox_api.py::test_get_by_id_of_a_later_part_is_404` |
| R4 | `tests/integration/test_inbox_api.py::test_delete_by_id_of_a_later_part_removes_nothing` |
| R5 | `tests/integration/test_inbox_api.py::test_delete_removes_every_part_of_the_message` |
| R6 | `tests/integration/test_inbox_api.py::test_pagination_counts_messages_not_parts` |
| R6 | `tests/integration/test_inbox_api.py::test_before_filter_uses_the_message_date` |
| R6 | `tests/integration/test_inbox_api.py::test_after_filter_uses_the_message_date` |
| R6 | `tests/unit/test_inbox_assembly.py::test_message_date_is_the_earliest_part_date` |
| R7 | `tests/integration/test_inbox_api.py::test_part_without_message_id_yet_is_hidden` |
| R8 | `tests/unit/test_inbox_assembly.py::test_part_attributes_come_from_the_lowest_position` |
| R8 | `tests/unit/test_inbox_assembly.py::test_processed_only_when_every_part_is_processed` |
| R9 | `tests/unit/test_api_without_database.py::test_send_queues_one_message_per_recipient` |
| R9 | `tests/unit/test_api_without_database.py::test_send_returns_the_outbox_id_of_each_recipient` |
| R10 | `tests/unit/test_api_without_database.py::test_send_accepts_a_message_of_480_characters` |
| R10 | `tests/unit/test_api_without_database.py::test_send_refuses_a_message_over_480_characters` |
| R11 | `tests/integration/test_outbox_sentitems_api.py::test_outbox_before_filter_alone` |
| R11 | `tests/integration/test_outbox_sentitems_api.py::test_outbox_after_filter_alone` |
| R11 | `tests/integration/test_outbox_sentitems_api.py::test_outbox_destination_filter_alone` |
| R11 | `tests/integration/test_outbox_sentitems_api.py::test_sentitems_before_filter` |
| R11 | `tests/integration/test_outbox_sentitems_api.py::test_sentitems_after_filter` |
| R11 | `tests/integration/test_outbox_sentitems_api.py::test_sentitems_destination_filter` |
| R12 | `tests/integration/test_outbox_sentitems_api.py::test_sentitems_list_has_one_entry_per_part` |
| R12 | `tests/integration/test_outbox_sentitems_api.py::test_sentitems_get_returns_the_first_part` |
| R12 | `tests/integration/test_outbox_sentitems_api.py::test_sentitems_delete_removes_all_parts` |
| R13 | `tests/integration/test_inbox_api.py::test_delete_unknown_message_is_204` |
| R14 | `tests/unit/test_api_without_database.py::test_no_auth_mode_leaves_sms_routes_open` |
| R14 | `tests/unit/test_api_without_database.py::test_bearer_mode_refuses_a_request_without_token` |
| R14 | `tests/unit/test_api_without_database.py::test_basic_mode_refuses_a_request_without_credentials` |
| R14 | `tests/unit/test_settings.py::test_unknown_security_value_refuses_the_start` |
| R15 | `tests/unit/test_api_without_database.py::test_refresh_without_token_is_401_in_every_mode` |
| R16 | `tests/unit/test_settings.py::test_token_lifetime_is_expressed_in_seconds` |
| R16 | `tests/unit/test_settings.py::test_token_lifetime_zero_disables_expiration` |
| R16 | `tests/unit/test_api_without_database.py::test_token_has_no_expiration_when_lifetime_is_zero` |
| R17 | `tests/unit/test_settings.py::test_database_password_is_required` |
| R17 | `tests/unit/test_settings.py::test_bearer_mode_requires_jwt_secret` |
| R17 | `tests/unit/test_settings.py::test_secured_modes_require_api_credentials` |
| R17 | `tests/unit/test_settings.py::test_webhook_url_requires_a_secret` |
| R18 | `tests/unit/test_api_without_database.py::test_login_is_refused_when_no_credentials_are_configured` |
| R19 | `tests/unit/test_api_without_database.py::test_unexpected_error_does_not_expose_internals` |
| R19 | `tests/unit/test_api_without_database.py::test_unexpected_error_is_logged_with_its_stack_trace` |
| R20 | `tests/integration/test_migrations.py::test_new_database_reaches_the_schema_version_of_gammu` |
| R20 | `tests/integration/test_migrations.py::test_legacy_database_reaches_the_schema_version_of_gammu` |
| R20 | `tests/integration/test_migrations.py::test_older_gammu_schema_is_refused` |
| R21 | `tests/integration/test_migrations.py::test_legacy_inbox_rows_become_single_part_messages` |
| R21 | `tests/integration/test_migrations.py::test_legacy_queued_messages_stay_eligible_every_day` |
| R22 | `tests/integration/test_health_api.py::test_phone_with_a_fresh_heartbeat_is_connected` |
| R22 | `tests/integration/test_health_api.py::test_expired_heartbeat_is_disconnected` |
| R22 | `tests/integration/test_health_api.py::test_fresh_row_wins_over_an_expired_one` |
| R22 | `tests/integration/test_gammu_end_to_end.py::test_health_follows_the_real_smsd_heartbeat` |
| R23 | `tests/integration/test_health_api.py::test_no_phone_row_is_unhealthy` |
| R23 | `tests/unit/test_api_without_database.py::test_health_reports_an_unreachable_database_without_details` |
| R24 | `tests/integration/test_health_api.py::test_health_never_exposes_phone_identifiers` |
| R25 | `tests/integration/test_gammu_schema_parity.py::test_schema_version_is_the_one_of_the_bundled_gammu` |
| R25 | `tests/integration/test_gammu_schema_parity.py::test_bundled_schema_version_can_be_adopted` |
| R25 | `tests/integration/test_gammu_schema_parity.py::test_same_tables_as_the_bundled_gammu` |
| R25 | `tests/integration/test_gammu_schema_parity.py::test_same_columns_as_the_bundled_gammu` |
| R25 | `tests/integration/test_gammu_schema_parity.py::test_same_indexes_as_the_bundled_gammu` |
| R26 | `tests/unit/test_api_without_database.py::test_send_accepts_international_national_and_short_numbers` |
| R26 | `tests/unit/test_api_without_database.py::test_send_refuses_a_malformed_number` |
| R26 | `tests/unit/test_api_without_database.py::test_send_refuses_the_whole_request_on_one_malformed_number` |
| R27 | `tests/integration/test_outbox_sentitems_api.py::test_outbox_delete_removes_its_other_parts` |
| R27 | `tests/integration/test_outbox_sentitems_api.py::test_outbox_delete_keeps_the_parts_of_other_messages` |
| R27 | `tests/integration/test_outbox_sentitems_api.py::test_outbox_delete_all_removes_every_part` |
| R27 | `tests/integration/test_migrations.py::test_migration_removes_orphan_outbox_parts` |
| R28 | `tests/unit/test_api_without_database.py::test_login_is_blocked_after_five_failures` |
| R28 | `tests/unit/test_api_without_database.py::test_blocked_login_says_when_to_retry` |
| R28 | `tests/unit/test_api_without_database.py::test_successful_login_resets_the_failures` |
| R28 | `tests/unit/test_api_without_database.py::test_forwarded_header_does_not_escape_the_login_limit` |
| R28 | `tests/unit/test_api_without_database.py::test_failures_expire_after_the_window` |
| R29 | `tests/integration/test_webhook.py::test_history_is_not_sent_on_first_activation` |
| R29 | `tests/integration/test_webhook.py::test_history_is_left_untouched_on_first_activation` |
| R29 | `tests/integration/test_webhook.py::test_message_after_activation_is_sent` |
| R29 | `tests/integration/test_webhook.py::test_message_received_while_stopped_is_sent_at_the_next_start` |
| R30 | `tests/integration/test_webhook.py::test_complete_multipart_is_one_post_with_the_whole_text` |
| R30 | `tests/integration/test_webhook.py::test_signature_is_the_hmac_of_the_raw_body` |
| R30 | `tests/integration/test_webhook.py::test_accepted_message_is_marked_processed` |
| R30 | `tests/integration/test_gammu_end_to_end.py::test_webhook_receives_a_real_multipart_sms_as_one_post` |
| R31 | `tests/integration/test_webhook.py::test_refused_message_stays_pending` |
| R31 | `tests/integration/test_webhook.py::test_refused_message_blocks_the_following_ones` |
| R31 | `tests/integration/test_webhook.py::test_messages_are_delivered_in_order_once_the_app_is_back` |
| R31 | `tests/integration/test_webhook.py::test_retry_delay_grows_up_to_five_minutes` |
| R32 | `tests/integration/test_webhook.py::test_incomplete_multipart_is_not_sent` |
| R32 | `tests/integration/test_webhook.py::test_incomplete_multipart_does_not_block_the_next_message` |
| R32 | `tests/integration/test_webhook.py::test_expired_incomplete_multipart_is_marked_processed_without_post` |
| R32 | `tests/integration/test_webhook.py::test_late_part_completing_an_expired_message_sends_it` |
| R33 | `tests/integration/test_webhook.py::test_purge_removes_old_messages` |
| R33 | `tests/integration/test_webhook.py::test_purge_keeps_a_message_with_a_recent_part` |
| R33 | `tests/integration/test_webhook.py::test_purge_removes_old_sent_items` |
| R33 | `tests/unit/test_settings.py::test_blank_retention_means_no_purge` |
| R34 | `tests/integration/test_webhook.py::test_purge_never_touches_the_outbox` |
| R34 | `tests/integration/test_webhook.py::test_purge_keeps_a_message_waiting_for_the_webhook` |
