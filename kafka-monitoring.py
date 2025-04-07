from kafka import KafkaConsumer
from prometheus_client import Counter, Histogram, start_http_server, Gauge

# TODO: Update the Kafka topic to the movie log of your team
topic = 'movielog26'

start_http_server(8765)

# Metrics like Counter, Gauge, Histogram, Summaries
# Refer https://prometheus.io/docs/concepts/metric_types/ for details of each metric
# TODO: Define metrics to show request count. Request count is total number of requests made with a particular http status
REQUEST_COUNT = Counter(
    'request_count', 'Recommendation Request Count',
    ['http_status']
)

REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency')

CTR_GAUGE = Gauge('click_through_rate', 'Overall Click Through Rate')


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
            # TODO: Increment the request count metric for the appropriate HTTP status code.
            # Hint: Extract the status code from the message and use it as a label for the metric.
            # print(values) - You can print values and see how to get the status
            # status = Eg. 200,400 etc
            # REQUEST_COUNT.?(status).inc()
            print(values)
            status = values[3].strip()
            REQUEST_COUNT.labels(status).inc()

            # Updating request latency histogram
            time_taken = float(values[-1].strip().split(" ")[0])
            REQUEST_LATENCY.observe(time_taken / 1000)
        elif 'ctr update' in values[1]:
            # Example: ...,ctr update,start=...,...,ctr=0.1432
            for part in values[2:]:
                if part.startswith('ctr='):
                    try:
                        raw_val = part.split('=')[1].strip().strip('"')  # <== fix is here
                        ctr_value = float(raw_val)
                        CTR_GAUGE.set(ctr_value)
                        print(f"📈 CTR updated: {ctr_value}")
                    except Exception as e:
                        print(f"⚠️ Failed to parse CTR value: {part} ({e})")


if __name__ == "__main__":
    main()
