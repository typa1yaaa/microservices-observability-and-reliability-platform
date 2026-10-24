# Runbook: деплой застрял (`K8sDeploymentStuck`)

**Серьезность:** warning
**Что означает:** у Deployment в `boutique` есть недоступные реплики (`kube_deployment_status_replicas_unavailable > 0`) дольше 5 минут. Обновление или запуск пода не завершается.
**Влияние:** часто нулевое: Rolling Update оставляет старый под, пока новый не станет `Ready` (эксперимент 5). Но система работает без запаса, а новая версия не выкатилась.

> Алерт **не срабатывает при масштабировании до 0 реплик** (недоступных реплик при этом нет). Этот случай описан в [dependency-down.md](dependency-down.md).

## 1. Быстрая проверка

```bash
kubectl get deploy -n boutique
kubectl rollout status deploy/<сервис> -n boutique --timeout=60s
kubectl get pods -n boutique -l app=<сервис>
kubectl describe pod -n boutique <под-в-проблеме>
```

Пользовательский эффект: `probe_success` и `kube_pod_status_ready` для `frontend`. Если они в норме, срочности нет.

## 2. Причины по статусу пода

| Статус | Причина | Что делать |
|---|---|---|
| `ImagePullBackOff` / `ErrImagePull` | неверный тег или образ недоступен | проверить образ в `kubectl describe pod`, откатить выкатку |
| `CrashLoopBackOff` | приложение падает при старте | `kubectl logs <под> --previous`, при необходимости пересоздать под |
| `OOMKilled` (в `describe`) | нехватка памяти | увеличить `resources.limits.memory` |
| `Pending` | нет ресурсов на узле или не подходят условия размещения | `kubectl describe pod` - раздел Events |

Для диагностики в Prometheus:
```PromQL
kube_pod_container_status_waiting_reason{namespace="boutique", reason=~"ImagePullBackOff|ErrImagePull|CrashLoopBackOff"} > 0
```

## 3. Починка

**Откатить выкатку** (эксперимент 5):
```bash
kubectl rollout history deploy/<сервис> -n boutique
kubectl rollout undo deploy/<сервис> -n boutique
```

**Пересоздать завязший под** (эксперимент 6: `recommendationservice` пробыл в `CrashLoopBackOff` около 8 минут после запуска, помогло удаление пода):
```bash
kubectl delete pod -n boutique <под>
```

## 4. Как понять, что все починено
`kube_deployment_status_replicas_unavailable = 0`, `kubectl rollout status` завершается успешно. В эксперименте 5 алерт вышел из `FIRING` через ~30 секунд после отката.

## 5. Связанные эксперименты
- [Эксперимент 5: образ с несуществующим тегом](../../chaos/2026-10-24/2026-10-24-incident-bad-deploy.md)
- [Эксперимент 6: `CrashLoopBackOff` при восстановлении `recommendationservice`](../../chaos/2026-10-24/2026-10-24-incident-adservice-down.md)
