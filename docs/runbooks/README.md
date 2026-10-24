# Runbooks

Инструкции для дежурного: что проверить и как починить по каждому алерту. Каждый runbook опирается на реальные хаос-эксперименты стенда.

| Алерт / ситуация | Runbook | Эксперименты |
|---|---|---|
| `BoutiqueFastBurn`, `BoutiqueSlowBurn` | [frontend-down.md](frontend-down.md) | [1](../../chaos/2026-10-19/2026-10-19-incident-frontend-down.md), [2](../../chaos/2026-10-21/2026-10-21-incident-cartservice-down-frontend-up.md) |
| `BoutiqueJourneyFailing` | [journey-failing.md](journey-failing.md) | [3](../../chaos/2026-10-22/2026-10-22-incident.md), [2](../../chaos/2026-10-21/2026-10-21-incident-cartservice-down-frontend-up.md) |
| `BoutiqueSlowResponse` | [slow-response.md](slow-response.md) | не проверялся |
| `JourneyExporterDown` | [journey-exporter-down.md](journey-exporter-down.md) | [4](../../chaos/2026-10-23/2026-10-23-incident-journey-exporter-down.md) |
| `K8sDeploymentStuck` | [deployment-stuck.md](deployment-stuck.md) | [5](../../chaos/2026-10-24/2026-10-24-incident-bad-deploy.md), [6](../../chaos/2026-10-24/2026-10-25-incident-adservice-down.md) |
| Сервис с 0 реплик (алерта нет) | [dependency-down.md](dependency-down.md) | [6](../../chaos/2026-10-24/2026-10-25-incident-adservice-down.md) |

## Если алерт не пришел в Телеграмм

Сначала определите, где потерялось сообщение.

```bash
# 1. Алерт вообще сработал? В Prometheus:
#    ALERTS{alertstate="firing"}

# 2. Видит ли Alertmanager алерт и отправляет ли его
kubectl logs -n monitoring -l app.kubernetes.io/name=alertmanager -c alertmanager --since=30m | grep -iE "error|telegram|timeout|retry"
#    alertmanager_notifications_failed_total{integration="telegram"}
```

Что известно из экспериментов 4 и 5:
- Уведомление о `FIRING` приходило с задержкой до 14 минут: Alertmanager отправляет через сторонний прокси Телеграмм API, прокси возвращал `TLS handshake timeout`, отправка повторялась. В это время срабатывали `AlertmanagerFailedToSendAlerts` и `AlertmanagerClusterFailedToSendAlerts`.
- Уведомление `Resolved` приходит с задержкой около 5 минут. В `kps-values.yaml` стоит `group_interval: 5m`, и вероятно именно он определяет эту задержку. Это не проверялось по логам.

Само состояние алерта всегда можно посмотреть в Prometheus (вкладка Alerts), не дожидаясь Телеграмм.
