# Admin Operations

## Export Retention Policy

PocketSage's admin export task writes zipped bundles to the instance's export directory and automatically manages disk usage. The task keeps only the **five** most recent export archives, as controlled by the `EXPORT_RETENTION = 5` constant in `pocketsage/services/admin_tasks.py`. Older archives beyond that threshold are deleted each time a new export completes, so operators should retrieve or mirror any exports they need to retain before triggering additional runs.

### Adjusting the Retention Count

If teams require a longer history, update the `EXPORT_RETENTION` constant to the desired number of archives and redeploy the service. A higher value increases disk consumption, so ensure the target environment has adequate storage capacity or pair the change with external archival tooling.
