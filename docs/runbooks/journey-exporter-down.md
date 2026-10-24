# Runbook: синтетический мониторинг не отдает данные (`JourneyExporterDown`)

**Серьезность:** warning
**Что означает:** метрика `journey_runs_total` отсутствует в Prometheus уже 2 минуты. `journey-exporter` не работает или Prometheus не может его опросить.
**Влияние:** пользователи не затронуты, но **мониторинг слеп**: `BoutiqueJourneyFailing` молчит, потому что считается по пустому вектору (эксперимент 4, мониторинг был слеп около 27 минут).

## 1. Быстрая проверка

```bash
kubectl get pods -n monitoring -l app=journey-exporter
kubectl get deploy journey-exporter -n monitoring
kubectl logs deploy/journey-exporter -n monitoring --since=10m
```

## 2. Ветки диагностики

### A. Подов нет или 0 реплик
```bash
kubectl scale deploy/journey-exporter -n monitoring --replicas=1
kubectl rollout status deploy/journey-exporter -n monitoring --timeout=120s
```

### B. Под в `CrashLoopBackOff` или `ImagePullBackOff`
```bash
kubectl describe pod -n monitoring -l app=journey-exporter
kubectl logs -n monitoring -l app=journey-exporter --previous
```
Для kind образ должен быть загружен в кластер:
```bash
kind load docker-image journey-exporter:0.1.0 --name sre-lab
```

### C. Под `Running`, но метрик в Prometheus нет
Проблема в сборе. Проверьте, отдает ли сам экспортер метрики:
```bash
kubectl port-forward -n monitoring svc/journey-exporter 8000:8000
curl -s localhost:8000/metrics | grep journey_runs_total
```
Если метрики есть, проверьте ServiceMonitor (селекторы, namespace, порт `metrics`) и страницу Targets в Prometheus.

## 3. Пока мониторинг слеп
Автоматически сбои сценария не обнаруживаются. Проверьте вручную, что витрина и покупка работают: откройте магазин и оформите тестовый заказ, посмотрите `probe_success`.

## 4. Как понять, что все починено
- `journey_runs_total` снова появилась в Prometheus.
- Через 15–30 секунд после старта растет `journey_runs_total{result="success"}`.
- Алерт гаснет в Prometheus почти сразу после восстановления (~6 с в эксперименте 4), а уведомление `Resolved` приходит позже.

## 5. Связанные эксперименты
- [Эксперимент 4: `journey-exporter` до 0 реплик](../../chaos/2026-10-23/2026-10-23-incident-journey-exporter-down.md)
