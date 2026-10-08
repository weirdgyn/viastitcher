"""Deterministic, bounded island refill, independent of pcbnew and wx.

Coordinates are board internal units. Spacing is measured in the metric
hypot(dx / horizontal_pitch, dy / vertical_pitch), so rectangular grids work.
"""
import math
import time
from dataclasses import dataclass


def point_in_ring(point, ring):
    x, y = point
    inside = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[1] > y) != (b[1] > y):
            if x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
                inside = not inside
    return inside


def segment_distance(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = dx * dx + dy * dy
    t = max(0, min(1, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length)) if length else 0
    return math.hypot(point[0] - a[0] - t * dx, point[1] - a[1] - t * dy)


@dataclass
class Region:
    layer: int
    outline: list
    holes: list

    def __post_init__(self):
        xs, ys = zip(*self.outline)
        self.bounds = (min(xs), min(ys), max(xs), max(ys))
        # Index edges by Y band once. Detailed zones can contain tens of
        # thousands of vertices; scanning every edge per candidate is quadratic.
        self.edges = [(a, b) for ring in [self.outline] + self.holes
                      for a, b in zip(ring, ring[1:] + ring[:1])]
        count = min(256, max(1, int(math.sqrt(len(self.edges))) * 2))
        self.band_height = max(1, (self.bounds[3] - self.bounds[1]) / count)
        self.bands = [[] for _ in range(count)]
        for i, (a, b) in enumerate(self.edges):
            for band in range(self._band(min(a[1], b[1])), self._band(max(a[1], b[1])) + 1):
                self.bands[band].append(i)

    def _band(self, y):
        return max(0, min(len(self.bands) - 1,
                          int((y - self.bounds[1]) / self.band_height)))

    def contains(self, point):
        x, y = point
        left, top, right, bottom = self.bounds
        if not (left <= x <= right and top <= y <= bottom):
            return False
        inside = False
        for i in self.bands[self._band(y)]:
            a, b = self.edges[i]
            if (a[1] > y) != (b[1] > y):
                if x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
                    inside = not inside
        return inside

    def nearby_edges(self, point, radius):
        x, y = point
        seen = set()
        for band in range(self._band(y - radius), self._band(y + radius) + 1):
            for i in self.bands[band]:
                if i in seen:
                    continue
                seen.add(i)
                a, b = self.edges[i]
                if (max(a[0], b[0]) >= x - radius and min(a[0], b[0]) <= x + radius
                        and max(a[1], b[1]) >= y - radius and min(a[1], b[1]) <= y + radius):
                    yield a, b

    def fits(self, point, radius):
        return self.contains(point) and all(
            segment_distance(point, a, b) >= radius
            for a, b in self.nearby_edges(point, radius))


class ViaIndex:
    """Spatial buckets; entries carry the layer/island IDs they actually touch."""
    def __init__(self, pitch):
        self.pitch = pitch
        self.buckets = {}
        self.covered = set()

    def cell(self, point):
        return tuple(math.floor(p / step) for p, step in zip(point, self.pitch))

    def add(self, point, regions):
        self.buckets.setdefault(self.cell(point), []).append((point, frozenset(regions)))
        self.covered.update(regions)

    def nearby(self, point, distance):
        for other, regions in self.nearby_points(point, distance):
            yield math.hypot((other[0] - point[0]) / self.pitch[0],
                             (other[1] - point[1]) / self.pitch[1]), regions

    def nearby_points(self, point, distance):
        cx, cy = self.cell(point)
        reach = math.ceil(distance)
        if (2 * reach + 1) ** 2 > len(self.buckets):
            buckets = self.buckets.values()
        else:
            buckets = (self.buckets.get((x, y), ())
                       for x in range(cx - reach, cx + reach + 1)
                       for y in range(cy - reach, cy + reach + 1))
        for bucket in buckets:
            for other, regions in bucket:
                d = math.hypot((other[0] - point[0]) / self.pitch[0],
                               (other[1] - point[1]) / self.pitch[1])
                if d <= distance:
                    yield other, regions

    def blocks_box(self, bounds, minimum):
        """Prove a rectangle covered by exclusion disks; uncertain stays open.

        Work in the normalized pitch metric. A disk containing all corners
        contains the whole rectangle. Subdivision also proves coverage by a
        union of disks without mistaking four blocked corners for full cover.
        """
        x0, y0, x1, y1 = bounds
        center = ((x0+x1)/2, (y0+y1)/2)
        radius = math.hypot((x1-x0)/self.pitch[0], (y1-y0)/self.pitch[1])/2
        points = [(p[0]/self.pitch[0], p[1]/self.pitch[1])
                  for p, _ in self.nearby_points(center, minimum + radius)]
        def covered(left, top, right, bottom, depth):
            if any(max((x-left)**2, (x-right)**2) +
                   max((y-top)**2, (y-bottom)**2) < minimum**2 for x,y in points):
                return True
            if not depth:
                return False
            mx, my = (left+right)/2, (top+bottom)/2
            return all(covered(*box, depth-1) for box in (
                (left,top,mx,my), (mx,top,right,my),
                (left,my,mx,bottom), (mx,my,right,bottom)))
        return bool(points) and covered(x0/self.pitch[0], y0/self.pitch[1],
                                       x1/self.pitch[0], y1/self.pitch[1], 2)


def validate_settings(pitch, diameter, minimum, maximum):
    if not all(math.isfinite(v) and v > 0 for v in (*pitch, diameter, minimum, maximum)):
        raise ValueError("Spacing, size and distance limits must be finite and positive")
    if not minimum <= 1 <= maximum:
        raise ValueError("Distance limits must include 100% of the grid spacing")


def capsule_section(a, b, radius, axis, value):
    """Cross-section of a track expanded by via radius and clearance."""
    other = 1-axis
    cuts = []
    for p in (a,b):
        delta = value-p[other]
        if abs(delta) <= radius:
            extent = math.sqrt(max(0, radius*radius-delta*delta))
            cuts.extend((p[axis]-extent, p[axis]+extent))
    dx,dy = b[0]-a[0], b[1]-a[1]
    length = math.hypot(dx,dy)
    if length:
        nx,ny = -dy*radius/length, dx*radius/length
        ring = [(a[0]+nx,a[1]+ny),(b[0]+nx,b[1]+ny),
                (b[0]-nx,b[1]-ny),(a[0]-nx,a[1]-ny)]
        for p,q in zip(ring,ring[1:]+ring[:1]):
            if (p[other]>value)!=(q[other]>value):
                cuts.append(p[axis]+(q[axis]-p[axis])*(value-p[other])/(q[other]-p[other]))
    return (min(cuts),max(cuts)) if cuts else None


def gap_candidates(target, region, pitch, diameter, index, minimum, blocked=None):
    """Centers of free X/Y intervals, not a progressively refined point mesh.

    Copper intervals are eroded by the via radius; obstacle cross-sections
    already include the required clearance. Circular exclusion zones use the
    normalized X/Y pitch. Final disk geometry and physical checks stay shared.
    """
    radius = diameter/2
    bounds = region.bounds
    low = [max(bounds[i]+radius, target[i]-pitch[i]/2) for i in (0,1)]
    high = [min(bounds[i+2]-radius, target[i]+pitch[i]/2) for i in (0,1)]
    if any(low[i]>high[i] for i in (0,1)):
        return []
    def centers(axis, value):
        other = 1-axis
        # The band index accelerates horizontal sections of detailed polygons.
        edges = (region.edges[i] for i in region.bands[region._band(value)]) if axis == 0 else region.edges
        cuts = sorted(a[axis]+(b[axis]-a[axis])*(value-a[other])/(b[other]-a[other])
                      for a,b in edges if (a[other]>value)!=(b[other]>value))
        intervals = [(max(a+radius,low[axis]),min(b-radius,high[axis]))
                     for a,b in zip(cuts[::2],cuts[1::2])
                     if max(a+radius,low[axis]) <= min(b-radius,high[axis])]
        exclusions = list(blocked(axis,value)) if blocked else []
        center = list(target); center[other] = value
        for point,_ in index.nearby_points(center, minimum+1):
            delta = (point[other]-value)/pitch[other]
            if abs(delta)<minimum:
                extent = pitch[axis]*math.sqrt(minimum**2-delta**2)
                exclusions.append((point[axis]-extent,point[axis]+extent))
        for a,b in sorted(exclusions):
            remaining = []
            for left,right in intervals:
                if b<=left or a>=right:
                    remaining.append((left,right))
                else:
                    if left<a: remaining.append((left,a))
                    if b<right: remaining.append((b,right))
            intervals = remaining
            if not intervals: break
        return [(a+b)/2 for a,b in intervals]
    points = set()
    for axis in (0,1):
        other = 1-axis
        fixed = min(high[other],max(low[other],target[other]))
        for value in centers(axis,fixed):
            p = [0,0]; p[axis],p[other] = value,fixed
            points.add(tuple(int(round(v)) for v in p))
            # Also center the perpendicular direction. This handles pockets
            # whose free center is offset in both X and Y.
            for cross in centers(other,value):
                p[other] = cross
                points.add(tuple(int(round(v)) for v in p))
    return points


@dataclass
class FillResult:
    added: int = 0
    unserved: int = 0
    cancelled: bool = False
    limited: bool = False
    examined: int = 0


def refill(regions, index, origin, pitch, diameter, minimum, maximum,
           place, stagger=False, progress=None, time_limit=None, candidate_limit=None,
           clock=time.monotonic, candidate_hints=None, blocked=None):
    """Visit each island's grid cells. place(point) checks and commits a via.

    The caller indexes pre-existing and first-pass vias. An empty island or
    an unreachable gap may receive a seed without a nearby neighbor. Physical
    collisions are always checked by place, including across different islands.
    """
    validate_settings(pitch, diameter, minimum, maximum)
    result = FillResult()
    visited = set()
    outside = set()
    started = clock()
    last_progress = started - 1

    def stop():
        nonlocal last_progress
        now = clock()
        if progress and now - last_progress >= 0.1:
            last_progress = now
            if not progress(result.added, result.examined):
                result.cancelled = True
        if ((time_limit is not None and now - started >= time_limit)
                or (candidate_limit is not None and result.examined >= candidate_limit)):
            result.limited = True
        if result.cancelled or result.limited:
            result.unserved = len(set(range(len(regions))) - index.covered)
            return True
        return False

    def cells(region):
        left, top, right, bottom = region.bounds
        y0 = math.ceil((top - origin[1]) / pitch[1] - 0.5)
        y1 = math.floor((bottom - origin[1]) / pitch[1] + 0.5)
        for row in range(y0, y1 + 1):
            shift = pitch[0] // 2 if stagger and row % 2 else 0
            x0 = math.ceil((left - origin[0] - shift) / pitch[0] - 0.5)
            x1 = math.floor((right - origin[0] - shift) / pitch[0] + 0.5)
            for col in range(x0, x1 + 1):
                yield (origin[0] + col * pitch[0] + shift, origin[1] + row * pitch[1])

    # Try ALL nominal sites before any offsets, so boundary-cell fallbacks
    # cannot steal space from an otherwise feasible nominal grid position.
    # Revisit deferred cells when new vias extend the reachable frontier.
    completed = set()
    # Each successful iteration completes another cell. Stop when a complete
    # traversal adds nothing; there is no elapsed-time or board-wide work cap.
    for nominal in (True, False):
        seed_gaps = False
        while True:
            previous_count = result.added
            # Try unserved islands before expanding coverage on large planes.
            order = sorted(range(len(regions)), key=lambda i: (
                i in index.covered,
                (regions[i].bounds[2] - regions[i].bounds[0]) *
                (regions[i].bounds[3] - regions[i].bounds[1]), i))
            for region_id in order:
                region = regions[region_id]
                if stop():
                    return result
                left, top, right, bottom = region.bounds
                if right - left < diameter or bottom - top < diameter:
                    continue
                for target in cells(region):
                    if (region_id, target) in completed:
                        continue
                    if stop():
                        return result
                    # Discard a cell only when its whole area is proven covered
                    # by spacing exclusions, never just because corners fail.
                    bounds = (max(left, target[0]-pitch[0]/2),
                              max(top, target[1]-pitch[1]/2),
                              min(right, target[0]+pitch[0]/2),
                              min(bottom, target[1]+pitch[1]/2))
                    if index.blocks_box(bounds, minimum):
                        completed.add((region_id, target))
                        continue
                    def spacing_error(point):
                        distances = [d for d, _ in index.nearby(point, maximum)]
                        return abs(min(distances) - 1) if distances else 0
                    if nominal:
                        candidates = (target,)
                    else:
                        suggestions = gap_candidates(target, region, pitch, diameter,
                                                     index, minimum, blocked)
                        if candidate_hints:
                            suggestions = set(suggestions).union(candidate_hints(target))
                        candidates = sorted(suggestions, key=lambda p: (
                            spacing_error(p), sum(((p[i]-target[i])/pitch[i])**2
                                                  for i in (0,1)), p))
                    for point in candidates:
                        if stop():
                            return result
                        if point in visited or (region_id, point) in outside:
                            continue
                        result.examined += 1
                        # Cheap spacing rejection before polygon/clearance checks.
                        neighbors = list(index.nearby(point, maximum))
                        if any(d < minimum for d, _ in neighbors):
                            visited.add(point)
                            continue
                        if (not seed_gaps and region_id in index.covered
                                and not any(region_id in ids for _, ids in neighbors)):
                            continue
                        if not region.fits(point, diameter / 2):
                            outside.add((region_id, point))
                            continue
                        # Failed physical candidates never become valid as vias are added.
                        visited.add(point)
                        if place(point):
                            touched = [i for i, r in enumerate(regions) if r.fits(point, diameter / 2)]
                            index.add(point, touched)
                            result.added += 1
                            completed.add((region_id, target))
                            break
            if result.added == previous_count:
                if seed_gaps:
                    break
                # Obstacles can disconnect feasible via positions even within
                # one connected copper polygon. After extending all reachable
                # neighbors, seed those gaps too; otherwise a distant via on
                # the same plane prevents the entire gap from ever filling.
                seed_gaps = True
    result.unserved = len(set(range(len(regions))) - index.covered)
    return result
