from .base import KubeApiBase
from .oneshot import KubeApiOneshot
from .service import KubeApiService


class KubeApi(KubeApiService, KubeApiOneshot, KubeApiBase): ...
