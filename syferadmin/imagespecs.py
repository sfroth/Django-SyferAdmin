from imagekit import ImageSpec
from imagekit.processors import ResizeToFill
from syferadmin.utils import register_specs


class ThumbSpec(ImageSpec):
	processors = [ResizeToFill(228, 120)]


register_specs([
	('syferadmin:imageblock.thumb', ThumbSpec),
])
