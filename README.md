# PDF to Smart EPUB Converter

A specialized tool for converting **Science/Academic Double-Column PDFs** into readable EPUBs.
It features "**Smart Relocation**": if the text says "see Table 1", the script automatically moves the `Table 1` image to appear right after that paragraph.

## Features
*   **Column Detection**: Automatically reorders left/right columns into a single linear reading flow.
*   **Smart Relocation**: detects captions (e.g., "Table 1", "表 1") and moves images to their citation point.
*   **Image Compression**: Reduces file size by compressing extracted images.
*   **Local Processing**: Uses `PyMuPDF` (runs locally, no API keys, $0 cost).

## Requirements
*   Python 3.8+
*   Pandoc (optional, for final EPUB generation)

## Installation

1.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2.  Install **Pandoc** (Required for EPUB creation):
    *   **Mac**: `brew install pandoc`
    *   **Windows/Linux**: Download from [pandoc.org](https://pandoc.org/)

## Usage

```bash
python pdf_to_epub.py /path/to/your/document.pdf
```

The script will create an `output/` folder containing:
*   `output.md`: The structured Markdown.
*   `output.epub`: The final eBook.
*   `images/`: The extracted and compressed images.
