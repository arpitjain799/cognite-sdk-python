from typing import Dict, Optional

from cognite.client.data_classes.annotation_types.primitives import (
    BoundingBox,
    CdfResourceRef,
    Polygon,
    PolyLine,
    VisionResource,
)


class ObjectDetection(VisionResource):
    label: str
    confidence: Optional[float]
    bounding_box: Optional[BoundingBox] = None
    polygon: Optional[Polygon] = None
    polyline: Optional[PolyLine] = None

    def __init__(self, *a, **kw):
        raise NotImplementedError("Not support in Python 3.6")

    def __post_init__(self):
        if isinstance(self.bounding_box, Dict):
            self.bounding_box = BoundingBox(**self.bounding_box)
        if isinstance(self.polygon, Dict):
            self.polygon = Polygon(**self.polygon)
        if isinstance(self.polyline, Dict):
            self.polyline = PolyLine(**self.polyline)


class TextRegion(VisionResource):
    text: str
    text_region: BoundingBox
    confidence: Optional[float] = None

    def __init__(self, *a, **kw):
        raise NotImplementedError("Not support in Python 3.6")

    def __post_init__(self):
        if isinstance(self.text_region, Dict):
            self.text_region = BoundingBox(**self.text_region)


class AssetLink(VisionResource):
    text: str
    text_region: BoundingBox
    asset_ref: CdfResourceRef
    confidence: Optional[float] = None

    def __init__(self, *a, **kw):
        raise NotImplementedError("Not support in Python 3.6")

    def __post_init__(self):
        if isinstance(self.text_region, Dict):
            self.text_region = BoundingBox(**self.text_region)
        if isinstance(self.asset_ref, Dict):
            self.asset_ref = CdfResourceRef(**self.asset_ref)
