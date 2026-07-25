from datetime import datetime


metrics_history = []


def save_metric(data):
    metrics_history.append(
        {
            **data,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


def get_history():
    return metrics_history
