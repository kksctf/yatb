from threading import Lock
import pickle
from typing import Callable
from prometheus_client.metrics import MetricWrapperBase
from prometheus_fastapi_instrumentator.metrics import Info
from prometheus_client import Counter, Gauge

# some flag statistic
solves_per_user = Counter(
    "solves_per_user",
    "Number of solves, per users",
    labelnames=("user_id", "username",)
)

bad_solves_per_user = Counter(
    "bad_solves_per_user",
    "Number of solves, per users",
    labelnames=("user_id", "username",)
)

solves_per_task = Counter(
    "solves_per_task",
    "Number of solves, per tasks",
    labelnames=("task_id", "task_name",)
)

score_per_user = Gauge(
    "score_per_user",
    "Score per user",
    labelnames=("user_id", "username",)
)

# some users statistic

users = Counter(
    "users",
    "Number of registred users"
)

logons_per_user = Counter(
    "logons_per_user",
    "Number of logons, per users",
    labelnames=("user_id", "username",)
)


def save_all_metrics():
    data = {}
    try:
        for metric in [
            "solves_per_user",
            "bad_solves_per_user",
            "solves_per_task",
            "score_per_user",
            "users",
            "logons_per_user",
        ]:
            m: MetricWrapperBase = globals()[metric]
            k = data[metric] = {}

            if hasattr(m, "_value"):
                k["_val"] = m._value
                k["_val"]._lock = None

            for _k, _v in m._metrics.items():
                if hasattr(_v, "_value"):
                    k[_k] = _v._value
                    k[_k]._lock = None

        with open("metrics_dump.pickle", 'wb') as f:
            pickle.dump(data, f)
    except Exception as ex:
        print(ex)


def load_all_metrics():
    data = {}
    try:
        with open("metrics_dump.pickle", 'rb') as f:
            data = pickle.load(f)

        for metric in [
            "solves_per_user",
            "bad_solves_per_user",
            "solves_per_task",
            "score_per_user",
            "users",
            "logons_per_user",
        ]:
            m: MetricWrapperBase = globals()[metric]
            k: dict = data[metric]

            if "_val" in k:
                m._value = k["_val"]
                m._value._lock = Lock()

            for _k, _v in k.items():
                if _k == "_val":
                    continue
                m._metrics[_k] = _v
                _v._lock = Lock()

    except Exception as ex:
        print(ex)
