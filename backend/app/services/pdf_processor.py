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
        
        # Use "dict" to get blocks in reading order (Text + Images)
        # sort=True ensures reading order is prioritized (Top-Left -> Bottom-Right)
        # content = page.get_text("dict", sort=True)
        content = page.get_text("dict") 
        blocks = content.get("blocks", [])
        
        page_items = []
        
        for i, block in enumerate(blocks):
            bbox = fitz.Rect(block['bbox'])
            
            if block['type'] == 0: # Text Block
                # Group lines into a single paragraph text
                # We want "Raw Line by Line" roughly preserved, but joined meaningfully?
                # User asked for raw lines.
                # A text block contains "lines", which contain "spans".
                
                block_text = ""
                for line in block["lines"]:
                    for span in line["spans"]:
                         block_text += span["text"]
                    # Add newline after each visual line in the PDF
                    block_text += "\n"
                
                block_text = block_text.strip()
                if not block_text:
                    continue
                
                page_items.append({
                    'type': 'text',
                    'bbox': bbox,
                    'text': block_text
                })
                
            elif block['type'] == 1: # Image Block
                # The image data is in block['image']
                image_bytes = block['image']
                img_ext = block['ext']
                img_name = f"p{page_num+1}_block{i}.{img_ext}"
                
                saved_path = self._compress_image(image_bytes, img_name)
                if saved_path:
                    page_items.append({
                        'type': 'image_fallback', # Treated as inline image
                        'bbox': bbox,
                        'path': saved_path
                    })
        
        return page_items

    def _generate_markdown(self, items):
        md_out = ""
        
        for item in items:
            if item['type'] == 'text':
                text = item['text']
                # Clean up multiple newlines?
                # The user wants "original line by line".
                # We already added \n in _analyze_page.
                
                # Heuristic: If we want to separate blocks significantly:
                md_out += f"{text}\n\n"
            
            elif item['type'] == 'image_fallback':
                md_out += f"![]({item['path']})\n\n"
        
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
