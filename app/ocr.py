import sys
import time

from rapidocr import RapidOCR


# Load the OCR models once when this module starts.
ocr_engine = RapidOCR()


def extract_text(image_path: str):
    start = time.perf_counter()

    result = ocr_engine(image_path)

    total_time = time.perf_counter() - start

    lines = []

    if result.txts:
        for text, score in zip(result.txts, result.scores):
            lines.append({
                "text": text,
                "confidence": float(score)
            })

    return {
        "lines": lines,
        "inference_seconds": float(result.elapse),
        "total_seconds": total_time
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python app/ocr.py <image_path>")
        sys.exit(1)

    data = extract_text(sys.argv[1])

    print("\n--- OCR TEXT ---")

    if not data["lines"]:
        print("No text detected.")
    else:
        for line in data["lines"]:
            print(
                f'{line["confidence"]:.3f}  {line["text"]}'
            )

    print("\n--- PERFORMANCE ---")
    print(
        f'RapidOCR inference: '
        f'{data["inference_seconds"]:.3f} seconds'
    )
    print(
        f'Total execution:     '
        f'{data["total_seconds"]:.3f} seconds'
    )
