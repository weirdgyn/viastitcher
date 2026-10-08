import math
import unittest

from adaptive_fill import Region, ViaIndex, gap_candidates, capsule_section, refill, validate_settings


def rectangle(x0, y0, x1, y1, layer=0, holes=None):
    return Region(layer, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], holes or [])


class AdaptiveFillTests(unittest.TestCase):
    def run_fill(self, regions, existing=(), pitch=(1000, 1000), origin=(0, 0),
                 blocked=lambda p: False, **kwargs):
        index = ViaIndex(pitch)
        for point, ids in existing:
            index.add(point, ids)
        added = []
        def place(point):
            if blocked(point):
                return False
            added.append(point)
            return True
        sections = kwargs.pop('blocked_sections',None)
        result = refill(regions, index, origin, pitch, 100, .8, 1.5, place,
                        blocked=sections, **kwargs)
        return result, added

    def test_regular_grid_does_not_get_denser(self):
        region = rectangle(-100, -100, 2100, 2100)
        existing = [((x, y), [0]) for x in (0, 1000, 2000) for y in (0, 1000, 2000)]
        result, added = self.run_fill([region], existing)
        self.assertEqual(added, [])
        self.assertEqual(result.unserved, 0)

    def test_small_island_without_grid_point(self):
        region = rectangle(200, 200, 450, 450)
        result, added = self.run_fill([region])
        self.assertEqual(result.added, 1)
        self.assertTrue(region.fits(added[0], 50))
        self.assertEqual(result.unserved, 0)

    def test_neighboring_island_does_not_count_as_connected(self):
        regions = [rectangle(-100,-100,100,100), rectangle(850,100,1150,400)]
        result, added = self.run_fill(regions, [((0,0), [0])])
        self.assertEqual(result.added, 1)
        self.assertEqual(result.unserved, 0)
        self.assertTrue(regions[1].fits(added[0], 50))

    def test_obstructed_grid_point_gets_offset_candidate(self):
        region = rectangle(-100, -400, 2100, 400)
        blocked = lambda p: 900 < p[0] < 1100 and -100 < p[1] < 100
        result, added = self.run_fill([region], [((0,0),[0]), ((2000,0),[0])], blocked=blocked, blocked_sections=lambda axis,v:
            [(900,1100)] if axis == 0 and abs(v)<100 else
            [(-100,100)] if axis == 1 and 900<v<1100 else [])
        self.assertEqual(result.added, 1)
        self.assertNotEqual(added[0], (1000,0))
        self.assertFalse(blocked(added[0]))
        self.assertLess(abs(added[0][0]-1000), 500)

    def test_hole_and_narrow_impossible_island(self):
        hole = [(200,200),(800,200),(800,800),(200,800)]
        region = rectangle(-100,-100,1100,1100, holes=[hole])
        _, added = self.run_fill([region])
        self.assertTrue(all(region.fits(p,50) for p in added))
        result, added = self.run_fill([rectangle(200,200,240,500)])
        self.assertEqual(result.unserved, 1)
        self.assertFalse(added)

    def test_rectangular_metric_and_new_via_spacing(self):
        pitch = (2000,500)
        result, added = self.run_fill([rectangle(0,0,6000,2000)], pitch=pitch)
        self.assertGreater(result.added, 5)
        for i, a in enumerate(added):
            for b in added[:i]:
                self.assertGreaterEqual(math.hypot((a[0]-b[0])/2000, (a[1]-b[1])/500), .8)

    def test_layer_islands_tracked_separately(self):
        regions = [rectangle(-100,-100,100,100,0), rectangle(850,100,1150,400,2)]
        result, added = self.run_fill(regions, [((0,0),[0])])
        self.assertEqual(result.unserved,0)
        self.assertTrue(any(regions[1].fits(p,50) for p in added))

    def test_first_island_via_does_not_need_nearby_neighbor(self):
        result, _ = self.run_fill([rectangle(10000,10000,10300,10300)], [((0,0),[])])
        self.assertEqual(result.added,1)

    def test_full_obstruction_and_cancellation(self):
        result, added = self.run_fill([rectangle(0,0,1000,1000)], blocked=lambda p: True)
        self.assertEqual(result.unserved,1)
        self.assertFalse(added)
        result, _ = self.run_fill([rectangle(0,0,1000,1000)], progress=lambda count, examined: False)
        self.assertTrue(result.cancelled)

    def test_stagger_and_offset_are_deterministic(self):
        args = ([rectangle(0,0,4000,4000)],)
        a = self.run_fill(*args, origin=(200,100), stagger=True)
        b = self.run_fill(*args, origin=(200,100), stagger=True)
        self.assertEqual(a,b)
        self.assertIn((200,100), a[1])
        self.assertIn((700,1100), a[1])

    def test_capsule_sections_include_width_clearance_and_endcaps(self):
        self.assertEqual(capsule_section((0,0),(0,1000),100,0,500),(-100,100))
        self.assertEqual(capsule_section((0,0),(0,1000),100,1,0),(-100,1100))
        self.assertEqual(capsule_section((0,0),(0,0),100,0,0),(-100,100))
        self.assertIsNone(capsule_section((0,0),(0,1000),100,0,1200))
        a,b = capsule_section((0,0),(1000,1000),100,0,500)
        self.assertAlmostEqual(a,500-100*math.sqrt(2))
        self.assertAlmostEqual(b,500+100*math.sqrt(2))

    def test_different_track_widths_shift_free_interval_midpoint(self):
        region = rectangle(0,0,3000,3000)
        def obstacles(axis,value):
            return [section for a,b,r in [((500,0),(500,3000),300),
                                         ((2000,0),(2000,3000),600)]
                    for section in [capsule_section(a,b,r,axis,value)] if section]
        points = gap_candidates((1000,1000),region,(1000,1000),100,
                                ViaIndex((1000,1000)),.8,obstacles)
        self.assertIn((1100,1000),points)

    def test_geometry_centers_very_narrow_window_without_refinement(self):
        region = rectangle(0,0,3000,3000)
        index = ViaIndex((1000,1000))
        def obstacles(axis,value):
            return [(0,1234),(1236,3000)] if axis == 0 else []
        points = gap_candidates((1000,1000),region,(1000,1000),100,index,.8,obstacles)
        self.assertIn((1235,1000),points)
        self.assertLess(len(points),10)

    def test_large_distance_limit_does_not_enumerate_empty_buckets(self):
        index = ViaIndex((1000,1000))
        index.add((0,0),[0])
        self.assertEqual(list(index.nearby((1000,0),1e100)),[(1.0,frozenset([0]))])

    def test_frontier_revisits_cells_before_initial_seed(self):
        region = rectangle(-100,-100,5100,100)
        result, added = self.run_fill([region],[((5000,0),[0])])
        self.assertEqual(result.added,5)
        self.assertIn((0,0),added)

    def test_blocked_path_does_not_prevent_seeding_a_gap_on_same_plane(self):
        region = rectangle(-100, -100, 8100, 2100)
        result, added = self.run_fill([region], [((0, 0), [0])],
                                     blocked=lambda p: p[0] < 5000)
        self.assertGreater(result.added, 0)
        self.assertTrue(any(p[0] >= 5000 for p in added))

    def test_nearby_via_does_not_discard_entire_offset_cell(self):
        region = rectangle(-1000, -500, 500, 500)
        result, added = self.run_fill([region], [((-700, 0), [0])],
                                     blocked=lambda p: p[0] < 200)
        self.assertGreater(result.added, 0)
        self.assertTrue(any(p[0] >= 200 for p in added))

    def test_geometry_hint_still_obeys_spacing_and_physical_checks(self):
        region = rectangle(-100, -100, 5100, 1100)
        hints = lambda target: [(target[0] + 123, target[1])]
        result, added = self.run_fill([region], [((0, 0), [0])],
            candidate_hints=hints, blocked=lambda p: p[0] != 3123)
        self.assertGreater(result.added, 0)
        self.assertTrue(all(p[0] == 3123 for p in added))

    def test_default_cell_and_total_search_budgets(self):
        result, _ = self.run_fill([rectangle(0,0,100000,100000)],
                                  blocked=lambda p: True, candidate_limit=100)
        self.assertTrue(result.limited)
        self.assertEqual(result.examined,100)

    def test_time_limit_keeps_partial_result(self):
        ticks = iter([0,0,0,0,0,0,0,100])
        result, added = self.run_fill([rectangle(-100,-100,10000,10000)],
                                      clock=lambda: next(ticks,100), time_limit=10)
        self.assertTrue(result.limited)
        self.assertEqual(result.added,len(added))

    def test_default_search_finishes_without_global_timeout_or_candidate_cutoff(self):
        ticks = iter([0])
        result, _ = self.run_fill([rectangle(0,0,12000,12000)],
            blocked=lambda p: True, clock=lambda: next(ticks,100))
        self.assertFalse(result.limited)
        self.assertGreater(result.examined,0)
        self.assertLess(result.examined,5000)

    def test_unconnected_existing_via_still_excludes_refill(self):
        existing = [((500,500), []), ((900,500), [])]
        result, added = self.run_fill([rectangle(-100,-100,2100,2100)],existing)
        self.assertGreater(result.added,0)
        all_points = [p for p,_ in existing]
        for p in added:
            self.assertTrue(all(math.hypot((p[0]-q[0])/1000,
                                          (p[1]-q[1])/1000) >= .8 for q in all_points))
            all_points.append(p)

    def test_box_pruning_proves_union_coverage_and_preserves_free_center(self):
        index = ViaIndex((2000,1000))
        for p in [(0,0),(2000,0),(0,1000),(2000,1000)]:
            index.add(p, [])
        self.assertTrue(index.blocks_box((0,0,2000,1000),.8))
        self.assertFalse(index.blocks_box((0,0,2000,1000),.6))

    def test_exact_minimum_boundary_is_allowed(self):
        index = ViaIndex((1000,1000)); index.add((0,0),[])
        region = rectangle(790,-10,810,10)
        self.assertFalse(index.blocks_box(region.bounds,.8))

    def test_indexed_geometry_matches_full_edge_scan(self):
        from adaptive_fill import point_in_ring, segment_distance
        import random
        count = 4000
        ring = [(int(10000*math.cos(i*2*math.pi/count)),int(10000*math.sin(i*2*math.pi/count)))
                for i in range(count)]
        holes = [[(-500,-500),(500,-500),(500,500),(-500,500)]]
        region = Region(0,ring,holes)
        rng = random.Random(123)
        for _ in range(150):
            p = (rng.randrange(-11000,11000),rng.randrange(-11000,11000))
            radius = rng.randrange(1,500)
            expected = point_in_ring(p,ring) and not point_in_ring(p,holes[0]) and all(
                segment_distance(p,a,b)>=radius for r in [ring]+holes
                for a,b in zip(r,r[1:]+r[:1]))
            self.assertEqual(region.fits(p,radius),expected)

    def test_interior_disk_does_not_scan_all_polygon_edges(self):
        from unittest.mock import patch
        from adaptive_fill import segment_distance
        ring = [(int(10000*math.cos(i*2*math.pi/10000)),int(10000*math.sin(i*2*math.pi/10000)))
                for i in range(10000)]
        region = Region(0,ring,[])
        with patch('adaptive_fill.segment_distance',wraps=segment_distance) as distance:
            self.assertTrue(region.fits((0,0),100))
            self.assertLess(distance.call_count,10)

    def test_invalid_settings(self):
        for pitch, size, low, high in [((0,1000),100,.8,1.5), ((1000,1000),100,1.1,1.5),
                                       ((1000,1000),100,.8,.9), ((1000,1000),100,0,1.5),
                                       ((math.inf,1000),100,.8,1.5)]:
            with self.assertRaises(ValueError):
                validate_settings(pitch,size,low,high)


if __name__ == '__main__':
    unittest.main()
