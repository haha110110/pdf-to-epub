import logging
import sys
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions

logging.basicConfig(level=logging.INFO)

# Use command line arg if provided, otherwise default
pdf_path_str = sys.argv[1] if len(sys.argv) > 1 else "/app/data/projects/0d6729e5-f222-4a83-b344-6f4292495a12/source.pdf"
pdf_path = Path(pdf_path_str)

print(f"Processing {pdf_path}...")

pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = False
pipeline_options.do_table_structure = True
pipeline_options.do_picture_description = False

doc_converter = DocumentConverter(
    allowed_formats=[InputFormat.PDF],
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
)

print("Starting conversion...")
try:
    conv_res = doc_converter.convert(pdf_path)
    print("Conversion complete!")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
