# Runbook: пользовательский сценарий падает (`BoutiqueJourneyFailing`)

**Серьезность:** critical
**Что означает:** более 20% прогонов синтетического сценария `home - product - add_to_cart - checkout` завершаются ошибкой (окно 5 мин, `for: 5m`).
**Влияние:** пользователи могут не мочь добавить товар или оформить заказ. Главная при этом может работать (`probe_success = 1`).

## 1. Быстрая проверка

```bash
# на каком шаге падает (самый частый шаг, см. оговорку ниже)
#   sum by (step) (increase(journey_step_failures_total[10m]))

# сколько секунд назад был последний успешный прогон
#   time() - journey_last_success_timestamp_seconds

# есть ли вообще данные (если нет, см. journey-exporter-down.md)
#   journey_runs_total

kubectl get deploy -n boutique
```

**Оговорка:** сценарий останавливается на первой ошибке, поэтому счетчик растет **только для первого упавшего шага**. Если `cartservice` лежит, провалы будут на шаге `home`, а не `add_to_cart` (эксперимент 2).

## 2. Шаг - какие сервисы проверять

| Шаг | Сервисы | Что известно из экспериментов |
|---|---|---|
| `home` | `frontend`, `cartservice`, `productcatalogservice`, `currencyservice` | `cartservice` лежит - главная отдает 500 (эксперимент 2) |
| `product` | `frontend`, `productcatalogservice`, `currencyservice` | отказ `recommendationservice` и `adservice` страницу не ломает (эксперимент 6) |
| `add_to_cart` | `cartservice`, `redis-cart` | не проверялось отдельно |
| `checkout` | `checkoutservice`, `paymentservice`, `shippingservice`, `emailservice`, `cartservice`, `currencyservice` | `paymentservice` лежит - падает только `checkout`, blackbox зеленый (эксперимент 3) |

## 3. Диагностика по шагу

```bash
# какой из перечисленных сервисов не готов
kubectl get deploy -n boutique
kubectl get pods -n boutique

# логи frontend и сервиса выбранного шага
kubectl logs deploy/frontend -n boutique --since=5m | grep -iE "error|failed"
kubectl logs deploy/checkoutservice -n boutique --since=5m | grep -iE "payment|error"
```

Обратите внимание на число рестартов (`kubectl get pods -n boutique`): у нестабильных сервисов (например, `emailservice`) сценарий может падать и без вашего вмешательства.

## 4. Починка
```bash
kubectl scale deploy/<сервис> -n boutique --replicas=1
kubectl rollout status deploy/<сервис> -n boutique --timeout=120s
```
Если под уходит в `CrashLoopBackOff`, см. [deployment-stuck.md](deployment-stuck.md).

## 5. Как понять, что все починено
- `journey_runs_total{result="success"}` снова растет.
- `time() - journey_last_success_timestamp_seconds` сбросилось до ~0–50 с.
- Алерт погаснет примерно через 5 минут (окно 5 мин), а уведомление `Resolved` может прийти еще позже из-за группировки в Alertmanager.

## 6. Связанные эксперименты
- [Эксперимент 3: `paymentservice` до 0 реплик](../../chaos/2026-10-22/2026-10-22-incident.md)
- [Эксперимент 2: `cartservice` до 0 реплик](../../chaos/2026-10-21/2026-10-21-incident-cartservice-down-frontend-up.md)
