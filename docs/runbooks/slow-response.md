# Runbook: витрина отвечает медленно (`BoutiqueSlowResponse`)

**Серьезность:** warning
**Что означает:** p95 времени ответа главной страницы по blackbox-пробе больше 1 секунды в течение 10 минут (SLO-2).
**Влияние:** страница открывается, но медленно, пользователи могут уходить.

> Этот алерт в хаос-экспериментах пока не срабатывал: ни один из шести сценариев не вызывал задержку. Runbook составлен по логике правила и нуждается в проверке отдельным экспериментом с сетевой задержкой.

## 1. Быстрая проверка

```bash
# актуальное значение и динамика
#   quantile_over_time(0.95, probe_duration_seconds{job="boutique-frontend"}[5m])
#   probe_duration_seconds{job="boutique-frontend"}

# frontend сам пишет время обработки запросов (http.resp.took_ms)
kubectl logs deploy/frontend -n boutique --since=5m | grep took_ms | tail -20

kubectl get pods -n boutique
```

## 2. Возможные причины

| Признак | Причина | Что делать |
|---|---|---|
| рестарты подов растут | нехватка памяти или падающие пробы | `kubectl describe pod`, `kubectl logs --previous` |
| высокая загрузка CPU | перегрузка | в Prometheus: `rate(container_cpu_usage_seconds_total{namespace="boutique"}[5m])`, ищите лидеров |
| тормозит один бэкенд | медленная зависимость | в логах `frontend` большие `took_ms` на страницах, зависящих от этого сервиса |
| скачок после выкатки | регрессия новой версии | `kubectl rollout undo deploy/<сервис> -n boutique` |
| нагрузка выше обычной | `loadgenerator` | в лабораторном стенде можно снизить: `kubectl scale deploy/loadgenerator -n boutique --replicas=0` |

## 3. Как понять, что все починено
`probe_duration_seconds` снова ниже 1 с, p95 за 5 минут ниже порога. Алерт погаснет вскоре после этого.

## 4. Планы
Проверить гипотезу экспериментом: добавить задержку 1.5–2 с на обращения к `productcatalogservice` (Chaos Mesh) и убедиться, что `probe_success` остается 1, а `BoutiqueSlowResponse` срабатывает.
