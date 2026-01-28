import fitz  # PyMuPDF
import os
import re
import shutil
from PIL import Image
import io
import argparse

class PdfToEpubConverter:
    def __init__(self, pdf_path, output_dir="output"):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.images_dir = os.path.join(output_dir, "images")
        self.doc = fitz.open(pdf_path)
        
        # Regex for capturing references (e.g., "Table 1", "表 1")
        # Supports Chinese and English
        self.ref_pattern = re.compile(r'(?:表|图|Table|Figure)\s*(\d+)', re.IGNORECASE)
        self.caption_pattern = re.compile(r'^(?:表|图|Table|Figure)\s*(\d+)', re.IGNORECASE)
        
        # Map: "Table 1" -> { 'image_path': '...', 'caption': '...' }
        self.image_ref_map = {}
        # List of images that haven't been bound to a caption yet
        self.unbound_images = []
        
        os.makedirs(self.images_dir, exist_ok=True)

    def compress_image(self, img_bytes, img_name):
        """Compress image to JPEG and save."""
        try:
            image = Image.open(io.BytesIO(img_bytes))
            
            # Convert RGBA to RGB if necessary for JPEG
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
                
            save_path = os.path.join(self.images_dir, img_name)
            # Save as JPEG with 75% quality
            image.save(save_path, "JPEG", quality=75)
            
            # Return relative path for Markdown
            return f"images/{img_name}"
        except Exception as e:
            print(f"Warning: Failed to compress image {img_name}: {e}")
            return None

    def analyze_page(self, page_num):
        """
        Extract text blocks and images from a page.
        Sort them by Column -> Y-position.
        Try to associate images with captions.
        """
        page = self.doc[page_num]
        width = page.rect.width
        midpoint = width / 2
        
        blocks = page.get_text("blocks") # (x0, y0, x1, y1, text, block_no, block_type)
        images = page.get_images(full=True)
        
        # 1. Process Images
        page_images = []
        for img_idx, img in enumerate(images):
            xref = img[0]
            try:
                # Extract image bytes
                base_image = self.doc.extract_image(xref)
                image_bytes = base_image["image"]
                img_ext = base_image["ext"]
                img_name = f"p{page_num+1}_img{img_idx}.{img_ext}"
                
                # Get BBox on page
                # Note: get_image_bbox is sometimes expensive or tricky if image is used multiple times
                # simplified approach: find first rect
                rects = page.get_image_rects(xref)
                if not rects:
                    continue
                bbox = rects[0] # Take the first occurrence
                
                saved_path = self.compress_image(image_bytes, img_name)
                if saved_path:
                    page_images.append({
                        'type': 'image',
                        'bbox': bbox,
                        'path': saved_path,
                        'xref': xref
                    })
            except Exception as e:
                print(f"Error extracting image {xref}: {e}")

        # 2. Process Text Blocks
        text_blocks = []
        for b in blocks:
            # b[4] is text content
            text_content = b[4].strip()
            if not text_content:
                continue
            text_blocks.append({
                'type': 'text',
                'bbox': fitz.Rect(b[:4]),
                'text': text_content
            })

        # 3. Detect Captions & Bind to Images
        # Heuristic: Caption is usually immediately below (or above) the image.
        # We look for text blocks heavily overlapping in X, and close in Y.
        
        # Separation threshold (points)
        Y_THRESHOLD = 30 
        
        bound_indices = set()
        
        for img in page_images:
            best_caption = None
            best_dist = float('inf')
            
            # Look for closest text block
            for i, txt in enumerate(text_blocks):
                if i in bound_indices: continue
                
                # Check vertical proximity (text below image)
                # Text Top - Image Bottom
                dist_below = txt['bbox'].y0 - img['bbox'].y1
                
                # Check vertical proximity (text above image)
                # Image Top - Text Bottom
                dist_above = img['bbox'].y0 - txt['bbox'].y1
                
                # Simple check: is it "close"?
                is_close_below = 0 < dist_below < Y_THRESHOLD
                is_close_above = 0 < dist_above < Y_THRESHOLD
                
                if is_close_below or is_close_above:
                    # Check regex
                    match = self.caption_pattern.search(txt['text'])
                    if match:
                        # Found a candidate
                        dist = min(abs(dist_below), abs(dist_above))
                        if dist < best_dist:
                            best_dist = dist
                            best_caption = txt
            
            if best_caption:
                # Bind them
                key = self.normalize_ref_key(best_caption['text'])
                if key:
                    self.image_ref_map[key] = {
                        'path': img['path'],
                        'caption': best_caption['text']
                    }
                    best_caption['type'] = 'caption_consumed' # Mark text as consumed
                    img['type'] = 'image_consumed' # Mark image as consumed
                    print(f"Bound Image {img['path']} to Caption '{key}'")

        # 4. Sort Remaining Items (Reading Order)
        # Filter out consumed items
        raw_items = [t for t in text_blocks if t['type'] != 'caption_consumed']
        remaining_images = [i for i in page_images if i['type'] != 'image_consumed']
        
        # Add remaining images as raw items
        for img in remaining_images:
            raw_items.append({
                'type': 'image_fallback',
                'bbox': img['bbox'],
                'path': img['path']
            })

        # New Sorting Algorithm: Adaptive Vertical Segmentation
        sorted_items = self.sort_blocks_by_layout(raw_items, width)
        
        return sorted_items

    def sort_blocks_by_layout(self, items, page_width):
        """
        Sorts blocks by detecting vertical bands (rows) and then sorting L->R within columnar bands.
        Handles mixed Single/Double column layouts.
        """
        if not items:
            return []

        # 1. Sort all items by Top position (y0)
        # This gives us a rough flow.
        items.sort(key=lambda x: x['bbox'].y0)

        # 2. Group into vertical segments (visual rows)
        # We process items and group them if they vertically overlap significantly.
        # But simply overlapping isn't enough for 2-column (e.g. col1-para1 and col2-para1 might not align perfectly).
        
        # Better approach for academic papers:
        # Detect "Page Columns" dynamically? No, too complex.
        
        # "XY-Cut" simplified:
        # We iterate and build "bands". A band ends when there is a vertical gap > threshold.
        # Inside a band, we verify if it looks like columns.
        
        final_sorted = []
        current_band = []
        
        # We need to detect "Y gaps" to split bands.
        # Let's iterate.
        
        # Helper to get bottom of a list of items
        def get_band_bottom(band_items):
             return max(item['bbox'].y1 for item in band_items)

        current_band = [items[0]]
        
        # Threshold for "gap" that defines a new reading section (e.g. header vs body)
        # If gap is small, it might just be line spacing.
        # If gap is negative (overlap), it's definitely same band.
        # We want to group "Parallel" blocks.
        
        for item in items[1:]:
            # Compare with current band's bounds
            # If this item starts "significantly below" the current band, break band.
            # "Significantly" = logic.
            # Actually, standard XY cut looks for ANY horizontal projection gap.
            
            # Simple Heuristic:
            # If item.y0 > min(band.y1) - tolerance? No.
            
            # Let's try a robust "Geometric Clustering":
            # 1. Project all blocks onto Y axis. 
            # 2. Find gaps in Y projection.
            # 3. These gaps define "Rows".
            # 4. In each "Row", sort by X.
            
            # Implementation of Y-Projection Gap separation:
            # But we must be careful: a strictly 2-col page has NO gap in Y projection often!
            # Col 1 text might fill the gaps of Col 2 text.
            
            # OK, the user problem: text merged, order wrong.
            # Likely the previous "Left/Right" split was TOO aggressive or blindly split.
            # And full_width items were dropped.
            
            # Let's revert to the Standard "Recursive XY Cut" logic simplified?
            # Or the "Two Column" Assumption Check?
            
            # HYBRID Strategy:
            # 1. Identify "Full Width" items (Header, Titles). Separate them out.
            # 2. Identify "content body".
            # 3. Check if content body is 2-col or 1-col.
            
            pass 
        
        # ... Re-thinking implementation for stability ...
        # If we assume standard scientific paper:
        # We process strictly top-down.
        # If we see blocks that are "Side by Side" (overlap in Y), we group them.
        
        # Algorithm:
        # 1. Sort all by y0.
        # 2. Iterate. If item.y0 overlaps with previous_item.y_range, they are "simultaneous".
        #    BUT only if they are separate columns!
        #    If they are just normal paragraphs in 1-column, they don't overlap (y0 > prev.y1).
        
        # Let's try this:
        # Define a "Column Boundary" at x = page_width/2.
        # Split items into Left, Right, Center (spanning).
        
        left = []
        right = []
        center = []
        mid = page_width / 2
        
        for item in items:
            x0, x1 = item['bbox'].x0, item['bbox'].x1
            w = x1 - x0
            if w > page_width * 0.6: # Wide element -> Center
                center.append(item)
            elif x1 < mid + (page_width * 0.05): # Mostly Left
                left.append(item)
            elif x0 > mid - (page_width * 0.05): # Mostly Right
                right.append(item)
            else:
                center.append(item) # Crossing middle weirdly -> Center
        
        # Now, we need to interleave them properly in Y sections.
        # E.g. Header (Center) -> Body (Left, Right) -> Footer (Center)
        # We can treat this as a sequence of "Zones".
        
        # Sort each sub-list by Y
        left.sort(key=lambda x: x['bbox'].y0)
        right.sort(key=lambda x: x['bbox'].y0)
        center.sort(key=lambda x: x['bbox'].y0)
        
        # We merge these queues.
        # While we have items:
        # 1. Peek at top of all 3 queues.
        # 2. If Center item is "above" Left/Right items (by some margin), take Center.
        # 3. If Left/Right allow, take them. 
        #    Issue: Left and Right are independent in 2-col.
        #    We want to exhaust Left, THEN Right? NO.
        #    We want to exhaust Left/Right for the *current vertical section*.
        
        # Making "Sections" based on Center items.
        # Center items act as "Breaks".
        
        final_order = []
        
        current_section_y0 = 0
        
        # We use the 'center' items to split the vertical space.
        # Then for each vertical space, we output Left items then Right items.
        
        # Add a dummy 'end' marker
        center_bounds = []
        for c in center:
            center_bounds.append( (c['bbox'].y0, c['bbox'].y1, c) )
        
        # Sort center bounds
        center_bounds.sort(key=lambda x: x[0])
        
        # Iterate through zones defined by center items
        # Zone 0: Top to Center[0].y0
        # Zone 1: Center[0] itself
        # Zone 2: Center[0].y1 to Center[1].y0 ...
        
        # Helper to extract items in Y-range
        def get_in_range(source_list, y_min, y_max):
            # source_list must be sorted by y0
            # We assume source items fully contained or mostly contained?
            # Or just start point? Start point is safer.
            subset = []
            remaining = []
            for it in source_list:
                # If item starts within this range (or slightly before/after?)
                # We use y0.
                y = it['bbox'].y0
                # Special Check:
                # If item started before y_min but continues? (Rare for para)
                if y_min <= y < y_max:
                    subset.append(it)
                else:
                    remaining.append(it)
            return subset, remaining

        # We process the center items as delimiters.
        # But wait, what if no center items? Then just Left -> Right.
        
        current_y = 0
        l_pool = left
        r_pool = right
        
        for (cy0, cy1, c_item) in center_bounds:
            # Process distinct region above this center item
            if cy0 > current_y:
                # Extract L and R in this gap
                l_sub, l_pool = get_in_range(l_pool, current_y, cy0)
                r_sub, r_pool = get_in_range(r_pool, current_y, cy0)
                
                # In a gap, we assume 2-column flow: Left Read then Right Read.
                # Sort sub-lists just in case (already sorted)
                final_order.extend(l_sub)
                final_order.extend(r_sub)
            
            # Add the center item
            final_order.append(c_item)
            current_y = cy1
            
        # Process remaining after last center item
        # Everything remaining in pools
        # If pool has items, they are below the last center item (or page top if no center)
        # Wait, get_in_range filtered them out. 
        # But since we use 'remaining' as new pool, we might miss items if they were skipped?
        # get_in_range logic: "if y_min <= y < y_max". 
        # If y >= y_max, it goes to remaining. correct.
        
        final_order.extend(l_pool)
        final_order.extend(r_pool)
        
        return final_order

    def normalize_ref_key(self, text):
        """
        Extract 'Table 1' from 'Table 1: Statistics...'
        Returns 'table1' or '表1' normalized string.
        """
        match = self.caption_pattern.search(text)
        if match:
            # Construct key like "table1" or "表1"
            # We treat strict grouping.
            # match.group(0) is "Table 1"
            return re.sub(r'\s+', '', match.group(0)).lower()
        return None

    def extract_refs_from_text(self, text):
        """Finds all references in a text block, e.g. 'see Table 1'"""
        matches = self.ref_pattern.findall(text)
        # ref_pattern returns group(1) (the number) or full?
        # My regex was `(Table|Figure)\s*(\d+)`. findall returns matches.
        # Actually findall returns tuples if groups match.
        
        # We want the full string "Table 1" to normalize.
        # Let's iterate finditer for better control
        found_keys = []
        for m in self.ref_pattern.finditer(text):
            raw = m.group(0) # "Table 1"
            key = re.sub(r'\s+', '', raw).lower()
            found_keys.append(key)
        return found_keys

    def convert(self):
        full_markdown = ""
        
        print(f"Processing {len(self.doc)} pages...")
        
        all_content_blocks = []
        
        # Step 1: Analyze all pages, build ref_map, get sorted blocks
        for page_num in range(len(self.doc)):
            page_items = self.analyze_page(page_num)
            all_content_blocks.extend(page_items)

        # Step 2: Generate Markdown & Inject Images
        print("Generating Markdown with Smart Insertion...")
        
        for item in all_content_blocks:
            if item['type'] == 'text':
                text = item['text']
                
                # Append text
                full_markdown += f"{text}\n\n"
                
                # Check for references
                refs = self.extract_refs_from_text(text)
                for ref_key in refs:
                    if ref_key in self.image_ref_map:
                        data = self.image_ref_map[ref_key]
                        if not data.get('inserted', False):
                            # Inject Image!
                            full_markdown += f"![{data['caption']}]({data['path']})\n"
                            full_markdown += f"*{data['caption']}*\n\n"
                            # Mark as inserted so we don't insert twice
                            data['inserted'] = True
                            print(f"-> Inserted {ref_key} after reference.")
            
            elif item['type'] == 'image_fallback':
                # This is an image that was NOT bound to a caption
                # We just insert it in flow
                full_markdown += f"![]( {item['path']} )\n\n"

        # Step 3: Cleanup - Insert any images that were bound but never referenced
        full_markdown += "\n---\n### Appendix: Unreferenced Figures\n\n"
        for key, data in self.image_ref_map.items():
            if not data.get('inserted', False):
                full_markdown += f"![{data['caption']}]({data['path']})\n"
                full_markdown += f"*{data['caption']}*\n\n"

        # Save MD
        md_path = os.path.join(self.output_dir, "output.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(full_markdown)
            
        print(f"Markdown saved to {md_path}")
        return md_path

def main():
    parser = argparse.ArgumentParser(description="Convert Double-Column PDF to EPUB/Markdown")
    parser.add_argument("pdf_path", help="Path to input PDF")
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print("File not found.")
        return

    converter = PdfToEpubConverter(args.pdf_path)
    md_file = converter.convert()
    
    # Optional: Calls pandoc (if installed)
    epub_file = md_file.replace(".md", ".epub")
    print(f"Converting to EPUB: {epub_file}...")
    try:
        import pypandoc
        # Checks if pandoc is installed
        pypandoc.convert_file(md_file, 'epub', outputfile=epub_file)
        print("Success! EPUB created.")
    except Exception as e:
        print("Pandoc conversion failed (Pandoc might not be installed).")
        print("You have the valid Markdown + Images. You can convert manually.")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
