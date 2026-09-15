from prometheus_client import Counter, Gauge

# some flag statistic
solves_per_user = Counter(
    "solves_per_user",
    "Number of solves, per users",
    labelnames=(
        "user_id",
        "username",
    ),
)

bad_solves_per_user = Counter(
    "bad_solves_per_user",
    "Number of solves, per users",
    labelnames=(
        "user_id",
        "username",
    ),
)

solves_per_task = Counter(
    "solves_per_task",
    "Number of solves, per tasks",
    labelnames=(
        "task_id",
        "task_name",
    ),
)

score_per_user = Gauge(
    "score_per_user",
    "Score per user",
    labelnames=(
        "user_id",
        "username",
    ),
)

# some users statistic

users = Counter("users", "Number of registred users")

logons_per_user = Counter(
    "logons_per_user",
    "Number of logons, per users",
    labelnames=(
        "user_id",
        "username",
    ),
)
