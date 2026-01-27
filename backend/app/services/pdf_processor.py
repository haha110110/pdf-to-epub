import fitz  # PyMuPDF
import os
import re
import io
import logging
from PIL import Image

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self, pdf_path: str, output_dir: str):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.images_dir = os.path.join(output_dir, "images")
        
        # Regex for capturing references (e.g., "Table 1", "表 1")
        self.ref_pattern = re.compile(r'(?:表|图|Table|Figure)\s*(\d+)', re.IGNORECASE)
        self.caption_pattern = re.compile(r'^(?:表|图|Table|Figure)\s*(\d+)', re.IGNORECASE)
        
        self.image_ref_map = {}
        self.doc = None

    def process(self) -> str:
        """
        Main entry point to process the PDF.
        Returns the path to the generated Markdown file.
        """
        os.makedirs(self.images_dir, exist_ok=True)
        self.doc = fitz.open(self.pdf_path)
        
        full_markdown = ""
        all_content_blocks = []
        
        logger.info(f"Processing {len(self.doc)} pages for {self.pdf_path}")
        
        # Step 1: Analyze pages
        for page_num in range(len(self.doc)):
            page_items = self._analyze_page(page_num)
            all_content_blocks.extend(page_items)

        # Step 2: Generate Markdown
        full_markdown = self._generate_markdown(all_content_blocks)
        
        # Save MD
        md_path = os.path.join(self.output_dir, "content.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(full_markdown)
            
        logger.info(f"Markdown content saved to {md_path}")
        self.doc.close()
        
        return md_path

    def _compress_image(self, img_bytes, img_name):
        try:
            image = Image.open(io.BytesIO(img_bytes))
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            # Force extension to .jpg since we convert to JPEG
            # This ensures EPUB readers don't get confused by PNG extension with JPEG content
            base_name = os.path.splitext(img_name)[0]
            new_filename = f"{base_name}.jpg"
            
            save_path = os.path.join(self.images_dir, new_filename)
            image.save(save_path, "JPEG", quality=75)
            
            # Return relative path for Markdown usage
            return f"images/{new_filename}"
        except Exception as e:
            logger.warning(f"Failed to compress image {img_name}: {e}")
            return None

    def _analyze_page(self, page_num):
        page = self.doc[page_num]
        width = page.rect.width
        midpoint = width / 2
        
        blocks = page.get_text("blocks")
        images = page.get_images(full=True)
        
        page_images = []
        
        # 1. Process Images
        for img_idx, img in enumerate(images):
            xref = img[0]
            try:
                base_image = self.doc.extract_image(xref)
                image_bytes = base_image["image"]
                img_ext = base_image["ext"]
                img_name = f"p{page_num+1}_img{img_idx}.{img_ext}"
                
                rects = page.get_image_rects(xref)
                if not rects:
                    continue
                bbox = rects[0]
                
                saved_path = self._compress_image(image_bytes, img_name)
                if saved_path:
                    page_images.append({
                        'type': 'image',
                        'bbox': bbox,
                        'path': saved_path,
                        'xref': xref
                    })
            except Exception as e:
                logger.error(f"Error extracting image {xref}: {e}")

        # 2. Process Text
        text_blocks = []
        for b in blocks:
            text_content = b[4].strip()
            if not text_content:
                continue
            text_blocks.append({
                'type': 'text',
                'bbox': fitz.Rect(b[:4]),
                'text': text_content
            })

        # 3. Bind Captions
        self._bind_captions(page_images, text_blocks)

        # 4. Sort Items
        raw_items = [t for t in text_blocks if t.get('type') != 'caption_consumed']
        remaining_images = [i for i in page_images if i.get('type') != 'image_consumed']
        
        for img in remaining_images:
            raw_items.append({
                'type': 'image_fallback',
                'bbox': img['bbox'],
                'path': img['path']
            })

        # Sort Logic (Left Col -> Right Col)
        left_col = []
        right_col = []
        full_width = []

        for item in raw_items:
            x0 = item['bbox'].x0
            w = item['bbox'].width
            
            if w > width * 0.7:
                full_width.append(item)
            elif x0 < midpoint:
                left_col.append(item)
            else:
                right_col.append(item)

        left_col.sort(key=lambda x: x['bbox'].y0)
        right_col.sort(key=lambda x: x['bbox'].y0)
        
        return left_col + right_col

    def _bind_captions(self, page_images, text_blocks):
        Y_THRESHOLD = 30
        bound_indices = set()
        
        for img in page_images:
            best_caption = None
            best_dist = float('inf')
            
            for i, txt in enumerate(text_blocks):
                if i in bound_indices: continue
                
                dist_below = txt['bbox'].y0 - img['bbox'].y1
                dist_above = img['bbox'].y0 - txt['bbox'].y1
                
                is_close = (0 < dist_below < Y_THRESHOLD) or (0 < dist_above < Y_THRESHOLD)
                
                if is_close:
                    match = self.caption_pattern.search(txt['text'])
                    if match:
                        dist = min(abs(dist_below), abs(dist_above))
                        if dist < best_dist:
                            best_dist = dist
                            best_caption = txt
            
            if best_caption:
                key = self._normalize_ref_key(best_caption['text'])
                if key:
                    self.image_ref_map[key] = {
                        'path': img['path'],
                        'caption': best_caption['text']
                    }
                    best_caption['type'] = 'caption_consumed'
                    img['type'] = 'image_consumed'

    def _generate_markdown(self, items):
        md_out = ""
        
        # We need to merge text blocks that are likely part of the same paragraph.
        # Simple heuristic:
        # If block ends with sentence-ending punctuation (., 。, ?, !), it's end of para.
        # Otherwise, we merge with next block.
        
        buffer_text = ""
        
        for i, item in enumerate(items):
            if item['type'] == 'text':
                text = item['text']
                
                # Check refs in the raw segment (needed for insertion logic)
                # But we want to insert images AFTER the paragraph ends or near the ref?
                # The current logic inserts immediately. Let's keep immediate insertion for now, 
                # but we need to accumulate text for the Markdown output.
                
                # Clean up newlines within the block itself (PDF blocks often have internal \n)
                # Replace internal \n with nothing (for Chinese) or space (for English)?
                # Heuristic: if char before \n is Chinese, no space. 
                text = re.sub(r'(?<=[\u4e00-\u9fff])\n(?=[\u4e00-\u9fff])', '', text)
                text = text.replace('\n', ' ')

                # Add to buffer
                if buffer_text:
                    # Decide joiner: Space if English, Empty if Chinese
                    last_char = buffer_text[-1]
                    first_char = text[0]
                    if self._is_cjk(last_char) and self._is_cjk(first_char):
                        buffer_text += text
                    else:
                        buffer_text += " " + text
                else:
                    buffer_text = text

                # Check if this block looks like end of paragraph
                # 1. Ends with punctuation
                # 2. Or next item is NOT text (e.g. image)
                # 3. Or next text item is "far" (not implemented here, we rely on punctuation)
                
                is_end_of_para = False
                if re.search(r'[。！？\.\!\?]\s*$', text):
                    is_end_of_para = True
                
                # Look ahead
                next_item = items[i+1] if i+1 < len(items) else None
                if next_item and next_item['type'] != 'text':
                    is_end_of_para = True
                
                if is_end_of_para or next_item is None:
                    md_out += f"{buffer_text}\n\n"
                    
                    # Check refs in the accumulated paragraph
                    refs = self._extract_refs_from_text(buffer_text)
                    for ref_key in refs:
                        if ref_key in self.image_ref_map:
                            data = self.image_ref_map[ref_key]
                            if not data.get('inserted', False):
                                md_out += f"![{data['caption']}]({data['path']})\n"
                                md_out += f"*{data['caption']}*\n\n"
                                data['inserted'] = True
                    
                    buffer_text = "" # Reset buffer

            elif item['type'] == 'image_fallback':
                # If we have buffer text pending, flush it first (unless we want image inside para?)
                # Usually image breaks paragraph.
                if buffer_text:
                     md_out += f"{buffer_text}\n\n"
                     buffer_text = ""
                
                md_out += f"![]({item['path']})\n\n"
        
        # Flush remaining
        if buffer_text:
            md_out += f"{buffer_text}\n\n"

        # Appendix
        md_out += "\n---\n### Appendix: Unreferenced Figures\n\n"
        for key, data in self.image_ref_map.items():
            if not data.get('inserted', False):
                md_out += f"![{data['caption']}]({data['path']})\n"
                md_out += f"*{data['caption']}*\n\n"
                
        return md_out

    def _is_cjk(self, char):
        if not char: return False
        return '\u4e00' <= char <= '\u9fff'

    def _normalize_ref_key(self, text):
        match = self.caption_pattern.search(text)
        if match:
            return re.sub(r'\s+', '', match.group(0)).lower()
        return None

    def _extract_refs_from_text(self, text):
        found_keys = []
        for m in self.ref_pattern.finditer(text):
            raw = m.group(0)
            key = re.sub(r'\s+', '', raw).lower()
            found_keys.append(key)
        return found_keys
