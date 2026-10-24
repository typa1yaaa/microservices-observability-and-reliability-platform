# Runbook: витрина недоступна (`BoutiqueFastBurn`, `BoutiqueSlowBurn`)

**Серьезность:** `BoutiqueFastBurn` - critical, `BoutiqueSlowBurn` - warning
**Что означает:** blackbox-проверка главной страницы (`probe_success{job="boutique-frontend"}`) часто падает, бюджет ошибок SLO-1 расходуется быстрее нормы.
**Влияние:** пользователи не могут открыть магазин.

## 1. Быстрая проверка (первые 5 минут)

```bash
# что видит blackbox: 0 = недоступно, код ответа
#   probe_success{job="boutique-frontend"}
#   probe_http_status_code{job="boutique-frontend"}

kubectl get pods -n boutique -l app=frontend
kubectl get deploy -n boutique
```

Дальше выберите ветку по результату.

## 2. Ветки диагностики

### A. Подов `frontend` нет или 0 реплик
Деплой масштабирован до нуля или удален (эксперимент 1).
```bash
kubectl scale deploy/frontend -n boutique --replicas=1
kubectl rollout status deploy/frontend -n boutique --timeout=120s
```

### B. Под `Running 1/1`, но `probe_http_status_code` = 500
Процесс жив, но главная страница ломается из-за зависимости. Проверки Kubernetes этого не видят (эксперимент 2: `cartservice` до 0 реплик, главная отдает 500).
```bash
# какие сервисы лежат: колонка READY 0/1
kubectl get deploy -n boutique
# или в Prometheus:
#   kube_deployment_status_replicas_available{namespace="boutique"} == 0

# причина в логах frontend
kubectl logs deploy/frontend -n boutique --since=5m | grep -iE "error|connection refused|rpc"
```
Верните упавший сервис (`kubectl scale deploy/<сервис> -n boutique --replicas=1`). Если после этого под уходит в `CrashLoopBackOff`, переходите к [deployment-stuck.md](deployment-stuck.md).

### C. Под жив, главная отдает 200, но проба падает
Проблема на стороне проверки или сети.
```bash
kubectl get pods -n monitoring | grep blackbox
kubectl get svc frontend -n boutique
```
Убедитесь, что цель в `monitoring/probe-frontend.yaml` (`http://frontend.boutique.svc.cluster.local`) резолвится и blackbox-exporter запущен.

### D. Сбой начался сразу после выкатки
Смотрите [deployment-stuck.md](deployment-stuck.md) и откатите:
```bash
kubectl rollout undo deploy/frontend -n boutique
```

## 3. Как понять, что все починено
- `probe_success` вернулся к 1.
- `kube_deployment_status_replicas_available{deployment="frontend"} = 1`.
- Сам алерт погаснет не сразу: `BoutiqueFastBurn` держится еще ~10 минут (окно 5 мин и `for: 2m`), `BoutiqueSlowBurn` до ~30 минут (окно 6 ч). Это нормально.

## 4. Особенности
- `BoutiqueSlowBurn` может быть **хвостом уже закрытого инцидента**. Если `probe_success` сейчас равен 1, а ошибки только в окне 6 ч, алерт погаснет сам.
- Повторные учебные запуски искажают время срабатывания: окна 1 ч и 6 ч помнят прошлые прогоны.

## 5. Связанные эксперименты
- [Эксперимент 1: `frontend` до 0 реплик](../../chaos/2026-10-19/2026-10-19-incident-frontend-down.md)
- [Эксперимент 2: `cartservice` до 0 реплик](../../chaos/2026-10-21/2026-10-21-incident-cartservice-down-frontend-up.md)
