from pydantic import BaseModel


class FeatureFlags(BaseModel):
    force_rename: bool = True


active_feature_flags = FeatureFlags()
