import time
import os
import sys
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.datamodel.base_models import InputFormat
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

# Check if a PDF path was provided
if len(sys.argv) < 2:
    print("Usage: python tests/verify_docling.py <path_to_pdf>")
    # Create a dummy PDF for testing if none provided? 
    # Better to just exit and ask user.
    sys.exit(1)

input_pdf_path = Path(sys.argv[1])
output_dir = Path("tests/output")
output_dir.mkdir(parents=True, exist_ok=True)

def run_docling_cpu_optimized(pdf_path):
    print(f"🚀 Starting Docling verification on: {pdf_path}")
    
    # 1. Configure Pipeline Options (CPU Optimized)
    pipeline_options = PdfPipelineOptions()
    
    # -- PERFORMANCE SETTINGS --
    # Disable OCR (assuming digital PDF for now) -> Huge speedup
    pipeline_options.do_ocr = False 
    
    # Disable Table Structure Model if you want extreme speed (optional)
    # pipeline_options.do_table_structure = False 
    
    # -- IMAGE EXTRACTION SETTINGS --
    # Enable image generation
    pipeline_options.generate_picture_images = True
    pipeline_options.generate_page_images = False # We don't need full page screenshots usually
    
    # Disable VLM for picture descriptions (Speedup + we don't need captions)
    pipeline_options.do_picture_description = False

    # Force CPU to ensure we simulate the target environment
    # (Docling defaults to GPU if available, but let's see how it runs)
    pipeline_options.accelerator_options.device = "cpu"
    pipeline_options.accelerator_options.num_threads = 4 # Adjust as needed

    # 2. Configure Converter
    # Use pypdfium2 backend for faster loading (optional but recommended)
    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
                backend=PyPdfiumDocumentBackend 
            )
        }
    )

    start_time = time.time()
    
    # 3. Convert
    print("⏳ Converting... (This might trigger model download on first run)")
    conv_result = doc_converter.convert(pdf_path)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"✅ Conversion finished in {duration:.2f} seconds")
    
    # 4. Export to Markdown with Referenced Images
    # Docling's default export_to_markdown() handles images based on internal state
    # We need to ensure we save the images and reference them.
    
    # Export Markdown
    # Note: image_mode="ref" is not a direct argument in export_to_markdown in all versions,
    # let's check the output. Docling usually embeds or ignores. 
    # We might need to iterate over the document elements to save images manually 
    # if the default exporter doesn't support 'save to file' out of the box easily.
    # But let's try the standard export first.
    
    md_content = conv_result.document.export_to_markdown()
    
    # Save text
    md_path = output_dir / f"{pdf_path.stem}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    print(f"📄 Markdown saved to: {md_path}")
    
    # 5. Extract and Save Images Manually (Reliable method)
    # Docling stores images in the document object structure.
    # We need to extract them to the output folder.
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    image_count = 0
    # Iterate through content to find pictures
    # Note: This is an example traversal; actual API might differ slightly based on version.
    # We will simply inspect if 'pictures' attribute exists or traverse the tree.
    
    # Modern Docling approach:
    for i, picture in enumerate(conv_result.document.pictures):
        image_filename = f"{pdf_path.stem}_img_{i}.png"
        image_path = images_dir / image_filename
        
        # Save the PIL Image
        picture.image.save(image_path)
        image_count += 1
        
        # NOTE: The default markdown export probably doesn't link to THESE files.
        # We might need to replace placeholders or write a custom serializer.
        # For this POC, we just want to verify we CAN get the images.
        
    print(f"🖼️  Extracted {image_count} images to {images_dir}")

    return md_path

if __name__ == "__main__":
    run_docling_cpu_optimized(input_pdf_path)
