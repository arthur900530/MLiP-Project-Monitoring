from kafka import KafkaConsumer
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import json

topic = 'movielog26'

start_http_server(8765)

# Request Metrics
REQUEST_COUNT = Counter(
    'request_count',
    'Recommendation Request Count',
    ['http_status']
)

REQUEST_LATENCY = Histogram(
    'request_latency_seconds',
    'Request latency'
)

# CTR Metrics
CTR_MODEL_GAUGE = Gauge(
    'click_through_rate_model',
    'Click Through Rate by Model',
    ['model']
)

CTR_TOTAL_GAUGE = Gauge(
    'click_through_rate_total',
    'Overall Click Through Rate'
)

CTR_COMPARISON_SIGNIFICANT = Gauge(
    'ctr_significance',
    'CTR statistical significance result (1 = significant, 0 = not)',
    ['model1', 'model2']
)

CTR_COMPARISON_ZSCORE = Gauge(
    'ctr_z_score',
    'Z-score for CTR comparison between models',
    ['model1', 'model2']
)


def parse_ctr_log(values):
    # Example: [..., ctr update, start=..., end=..., model=..., ctr=0.1234]
    ctr_data = {}
    for part in values:
        keyval = part.strip().replace('"', '').split('=')
        if len(keyval) == 2:
            k, v = keyval
            ctr_data[k.strip()] = v.strip()
    return ctr_data


def main():
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers='localhost:9092',
        auto_offset_reset='latest',
        group_id=topic,
        enable_auto_commit=True,
        auto_commit_interval_ms=1000
    )

    for message in consumer:
        event = message.value.decode('utf-8')
        values = event.split(',')

        if 'recommendation request' in values[2]:
            status = values[3].strip()
            REQUEST_COUNT.labels(status).inc()
            time_taken = float(values[-1].strip().split(" ")[0])
            REQUEST_LATENCY.observe(time_taken / 1000)

        elif 'ctr_update' in event:
            try:
                data = json.loads(event.strip())
                ctr_data = data.get('ctr_update', {})
                model = ctr_data.get('model', 'unknown')
                ctr = float(ctr_data.get('ctr', 0.0))

                if model == 'total':
                    CTR_TOTAL_GAUGE.set(ctr)
                else:
                    CTR_MODEL_GAUGE.labels(model).set(ctr)

                print(f"📈 CTR for {model}: {ctr}")
            except Exception as e:
                print(f"⚠️ Failed to parse CTR update: {event} ({e})")

        elif 'ctr_comparison' in event:
            try:
                data = json.loads(event.strip())
                comp = data.get('ctr_comparison', {})
                model1 = comp.get('model1', 'model1')
                model2 = comp.get('model2', 'model2')
                z_score = float(comp.get('z_score', 0))
                significant = 1 if comp.get('significant', False) else 0

                CTR_COMPARISON_ZSCORE.labels(model1, model2).set(z_score)
                CTR_COMPARISON_SIGNIFICANT.labels(model1, model2).set(significant)

                print(f"🔬 CTR comparison: {model1} vs {model2} → z={z_score}, significant={significant}")
            except Exception as e:
                print(f"⚠️ Failed to parse CTR comparison message: {event} ({e})")


if __name__ == "__main__":
    main()
