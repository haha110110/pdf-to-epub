import unittest
from collections import namedtuple

# Mocking the PdfToEpubConverter class for testing sorting logic
class MockConverter:
    def sort_blocks_by_layout(self, items, page_width):
        """
        Copy of the implemented logic for testing.
        """
        if not items:
            return []

        items.sort(key=lambda x: x['bbox'].y0)

        left = []
        right = []
        center = []
        mid = page_width / 2
        
        for item in items:
            x0, x1 = item['bbox'].x0, item['bbox'].x1
            w = x1 - x0
            if w > page_width * 0.6: 
                center.append(item)
            elif x1 < mid + (page_width * 0.05): 
                left.append(item)
            elif x0 > mid - (page_width * 0.05): 
                right.append(item)
            else:
                center.append(item) 
        
        left.sort(key=lambda x: x['bbox'].y0)
        right.sort(key=lambda x: x['bbox'].y0)
        center.sort(key=lambda x: x['bbox'].y0)
        
        final_order = []
        center_bounds = []
        for c in center:
            center_bounds.append( (c['bbox'].y0, c['bbox'].y1, c) )
        center_bounds.sort(key=lambda x: x[0])
        
        def get_in_range(source_list, y_min, y_max):
            subset = []
            remaining = []
            for it in source_list:
                y = it['bbox'].y0
                if y_min <= y < y_max:
                    subset.append(it)
                else:
                    remaining.append(it)
            return subset, remaining

        current_y = 0
        l_pool = left
        r_pool = right
        
        for (cy0, cy1, c_item) in center_bounds:
            if cy0 > current_y:
                l_sub, l_pool = get_in_range(l_pool, current_y, cy0)
                r_sub, r_pool = get_in_range(r_pool, current_y, cy0)
                final_order.extend(l_sub)
                final_order.extend(r_sub)
            
            final_order.append(c_item)
            current_y = cy1
            
        final_order.extend(l_pool)
        final_order.extend(r_pool)
        
        return final_order

# Helper to create mock items
Rect = namedtuple('Rect', ['x0', 'y0', 'x1', 'y1'])
def mk_item(id, x0, y0, x1, y1):
    return {'id': id, 'bbox': Rect(x0, y0, x1, y1)}

class TestSorting(unittest.TestCase):
    def setUp(self):
        self.converter = MockConverter()
        self.width = 600 # Page width

    def test_pure_single_column(self):
        # All "Left" or "Center" but treated as one flow if they align?
        # Actually our logic splits mostly-left items into L-col.
        # If a single column doc is narrow (like a book), it might be all 'center' or all 'left'.
        # If items are wider than 60% (360), they hit 'center'.
        
        # Case: Wide paragraphs (Center)
        title = mk_item('title', 50, 50, 550, 100) # Full width
        p1 = mk_item('p1', 50, 120, 550, 200)      # Full width
        p2 = mk_item('p2', 50, 220, 550, 300)      # Full width
        
        items = [p2, title, p1] # Scrambled input
        sorted_items = self.converter.sort_blocks_by_layout(items, self.width)
        ids = [x['id'] for x in sorted_items]
        self.assertEqual(ids, ['title', 'p1', 'p2'])

    def test_pure_double_column(self):
        # L1, L2, R1, R2
        l1 = mk_item('l1', 10, 100, 290, 200)
        l2 = mk_item('l2', 10, 210, 290, 300)
        r1 = mk_item('r1', 310, 100, 590, 200)
        r2 = mk_item('r2', 310, 210, 590, 300)
        
        items = [r2, l1, r1, l2]
        sorted_items = self.converter.sort_blocks_by_layout(items, self.width)
        ids = [x['id'] for x in sorted_items]
        # Expectation: No center items, so all Left then all Right
        self.assertEqual(ids, ['l1', 'l2', 'r1', 'r2'])

    def test_mixed_layout_header_body(self):
        # Header (Center), Body (L, R)
        header = mk_item('header', 50, 10, 550, 60) # Center
        l1 = mk_item('l1', 10, 100, 290, 200)
        r1 = mk_item('r1', 310, 100, 590, 200)
        
        items = [ l1, r1, header]
        sorted_items = self.converter.sort_blocks_by_layout(items, self.width)
        ids = [x['id'] for x in sorted_items]
        # Expect: Header -> L1 -> R1
        self.assertEqual(ids, ['header', 'l1', 'r1'])

    def test_mixed_complex_zones(self):
        # Title (Center)
        # Abstract (Center/Wide)
        # Body L1, R1
        # Figure (Center)
        # Body L2, R2
        
        title = mk_item('title', 50, 10, 550, 50)
        abst = mk_item('abstract', 50, 60, 550, 150)
        
        l1 = mk_item('l1', 10, 200, 290, 300)
        r1 = mk_item('r1', 310, 200, 590, 300)
        
        # Figure spans page in middle
        fig = mk_item('fig', 10, 350, 590, 500) 
        
        l2 = mk_item('l2', 10, 520, 290, 600)
        r2 = mk_item('r2', 310, 520, 590, 600)
        
        items = [r2, l1, fig, l2, title, r1, abst]
        sorted_items = self.converter.sort_blocks_by_layout(items, self.width)
        ids = [x['id'] for x in sorted_items]
        
        # Expected Order:
        # 1. title (Center zone 1)
        # 2. abstract (Center zone 2)
        # 3. Gap (200-350): l1, r1
        # 4. fig (Center zone 3)
        # 5. Gap (520+): l2, r2
        
        expected = ['title', 'abstract', 'l1', 'r1', 'fig', 'l2', 'r2']
        self.assertEqual(ids, expected)

if __name__ == '__main__':
    unittest.main()
