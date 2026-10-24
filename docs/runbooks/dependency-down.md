# Runbook: сервис микросервисного приложения недоступен (0 реплик)

**Алерта нет** (пока). Runbook для ситуации, когда вы заметили, что Deployment в `boutique` имеет 0 доступных реплик, или планируете добавить такой алерт.
**Серьезность:** зависит от сервиса, см. таблицу.

## 1. Как заметить
```bash
kubectl get deploy -n boutique # колонка READY: 0/1
```
В Prometheus:
```PromQL
kube_deployment_status_replicas_available{namespace="boutique"} == 0
```
  
`K8sDeploymentStuck` здесь молчит: при `--replicas=0` недоступных реплик нет. Нужен отдельный алерт (см. «Планы»).

## 2. Насколько это срочно

| Сервис | Что происходит у пользователя | Срочность | Эксперимент |
|---|---|---|---|
| `frontend` | витрина недоступна | **критично**, см. [frontend-down.md](frontend-down.md) | 1 |
| `cartservice` | главная отдает HTTP 500 | **критично**, см. [frontend-down.md](frontend-down.md) | 2 |
| `paymentservice` | витрина работает, оформление заказа падает | **высокая**, см. [journey-failing.md](journey-failing.md) | 3 |
| `adservice` | страницы работают без блока рекламы | низкая, не будить | 6 |
| `recommendationservice` | страницы работают без блока рекомендаций | низкая, не будить | 6 |
| остальные (`checkoutservice`, `shippingservice`, `emailservice`, `currencyservice`, `productcatalogservice`, `redis-cart`) | не проверялось | считать влияющими на покупку, проверить вручную | - |

## 3. Починка
```bash
kubectl scale deploy/<сервис> -n boutique --replicas=1
kubectl rollout status deploy/<сервис> -n boutique --timeout=120s
```
Если под уходит в `CrashLoopBackOff` (эксперимент 6: `recommendationservice`, около 8 минут), см. [deployment-stuck.md](deployment-stuck.md), помогает удаление пода:
```bash
kubectl delete pod -n boutique <под>
```

## 4. Проверка
- `kube_deployment_status_replicas_available{deployment="<сервис>"} = 1`.
- Для `adservice` и `recommendationservice` визуально: блок вернулся на странице товара.

## 5. Почему «некритичный» не значит «неважный»
Graceful degradation скрывает проблему и от пользователя, и от пользовательского мониторинга: `probe_success` и `journey_runs_total{result="success"}` остаются в норме. Только состояние подов показывает, что сервис лежит.

## 6. Планы
Алерт `kube_deployment_status_replicas_available{namespace="boutique"} == 0` с `for: 2m`, уровень warning (для некритичных сервисов можно info).

## 7. Связанные эксперименты
- [Эксперимент 6: `adservice` и `recommendationservice`](../../chaos/2026-10-24/2026-10-25-incident-adservice-down.md)
