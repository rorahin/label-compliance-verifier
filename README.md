# AI-Powered Alcohol Label Verification

A prototype web application that assists alcohol label compliance review by comparing application data against information extracted from uploaded label images.

**Live application:**  
https://label-compliance-verifier.onrender.com

## Overview

The application allows a reviewer to enter expected application information and upload an alcohol label image.

A second label image is optional so information split between front and back labels can be evaluated together.

The system:

1. Validates uploaded images securely.
2. Processes images entirely in memory.
3. Extracts label text using local OCR.
4. Parses structured label information.
5. Compares detected values with application data.
6. Returns one of three outcomes:
   - `PASS`
   - `FAIL`
   - `REVIEW`

`REVIEW` is used when OCR uncertainty makes an automatic decision inappropriate.

## Fields Verified

The prototype currently verifies:

- Brand name
- Class / type
- Alcohol content
- Net contents
- Government Warning wording

The Government Warning text is checked against the required reference wording.

Visual requirements such as warning font size, bold type, contrast, and physical placement are not automatically verified by this prototype.

## Multi-Image Verification

Real alcohol bottles frequently split required information across different label panels.

For example:

- the front label may contain brand name, type, ABV, and net contents
- the back label may contain the Government Warning

The application therefore supports:

- one required primary label image
- one optional additional label image

OCR evidence from both images is combined before validation.

## Technology

### Backend

- Python 3.12
- FastAPI
- Uvicorn
- Jinja2

### OCR / Image Processing

- RapidOCR
- ONNX Runtime
- OpenCV
- Pillow
- NumPy

OCR is performed locally by the application. The prototype does not depend on an external OCR or AI API.

### Testing and Code Quality

- Pytest
- Ruff
- Bandit

## Architecture

```text
Application Data
       |
       v
+-------------------+
|   FastAPI App     |
+-------------------+
       |
       +------------------------------+
       |                              |
       v                              v
Primary Label                  Additional Label
(required)                       (optional)
       |                              |
       v                              v
 Image Validation               Image Validation
       |                              |
       v                              v
     OCR                            OCR
       |                              |
       +--------------+---------------+
                      |
                      v
               Combined OCR Text
                      |
                      v
              Structured Parsing
                      |
                      v
             Compliance Validation
                      |
                      v
              PASS / FAIL / REVIEW
```

## Validation Approach

### Brand Name and Class / Type

Text is normalized before comparison so harmless capitalization differences do not create false mismatches.

For example:

```text
Stone's Throw
STONE'S THROW
```

are treated as equivalent.

### Alcohol Content

The application extracts percentage values such as:

```text
45%
45% Alc./Vol.
```

and compares the detected value with the application value.

### Net Contents

Volume values are normalized to milliliters.

For example:

```text
750 mL
0.75 L
```

are treated as equivalent.

### Government Warning

The required Government Warning wording is compared against OCR-extracted text.

If the complete required wording is recovered correctly, the wording check can pass even if an individual OCR line has a lower confidence score.

If OCR uncertainty prevents a reliable determination, the result is routed to `REVIEW` rather than making an unsupported automatic compliance decision.

## OCR Confidence

OCR confidence is treated as an uncertainty signal, not as a regulatory probability.

Low-confidence evidence can cause a field to be routed to manual review rather than automatically passed or failed.

## Security and Privacy

Uploaded images are treated as untrusted input.

The application:

- restricts accepted image formats to JPEG, PNG, and WebP
- validates decoded image content rather than trusting file extensions
- limits upload size
- limits decoded pixel count
- rejects malformed images
- reduces decompression-bomb and resource-exhaustion risk
- resizes large images before OCR
- processes uploaded images in memory
- does not intentionally persist uploaded label images
- does not require a database
- uses security-related HTTP response headers
- runs as a non-root user in Docker
- uses privacy-conscious request logging and request IDs

## Local Setup

### Requirements

- Python 3.12
- Git

Create a virtual environment:

```bash
python3.12 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install application dependencies:

```bash
python -m pip install -r requirements.txt
```

Install development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run the application:

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Testing and Quality Checks

Run the tests:

```bash
python -m pytest -q
```

Run the full local quality gate:

```bash
make check
```

This checks:

- Ruff formatting
- Ruff linting
- Bandit static security analysis
- Pytest

## Docker

Build:

```bash
docker build -t label-compliance-verifier .
```

Run:

```bash
docker run --rm -p 8000:8000 label-compliance-verifier
```

Then open:

```text
http://127.0.0.1:8000
```

## Deployment

The prototype is deployed as a Dockerized web service on Render.

**Live URL:**  
https://label-compliance-verifier.onrender.com

The application does not require a database or persistent file storage.

## Real-World Testing

The prototype was tested with real front and back alcohol bottle photographs in addition to synthetic test data.

Using two images from the same bottle demonstrated that evidence can be combined across label panels:

```text
Brand Name          PASS
Class / Type        PASS
Alcohol Content     PASS
Net Contents        PASS
Government Warning  PASS
```

This real-world test motivated the optional secondary-image feature.

## Performance

The OCR models remain loaded in the running process after initialization, so warm requests are substantially faster than the initial startup request.

The demonstration deployment uses a free hosting instance that may sleep after inactivity. A cold start can therefore exceed the stakeholder's approximately five-second usability target.

An always-running production instance would avoid this hosting-level cold-start delay.

## Assumptions and Limitations

This is a focused proof of concept rather than a complete TTB compliance engine.

Current assumptions:

- application information is entered manually
- up to two images belong to the same product
- OCR-readable text is sufficient for the implemented checks
- uncertain OCR results should be routed to a human reviewer
- uploaded images do not need to be retained

The prototype does not currently verify:

- Government Warning font size
- bold formatting
- contrast
- physical placement
- every beverage-specific TTB labeling rule
- producer or importer address compliance
- country-of-origin compliance
- large batch processing
- direct COLA integration

These trade-offs keep the prototype focused on a reliable core workflow.

## Design Philosophy

The application is intended to assist compliance reviewers rather than replace human judgment.

Routine, high-confidence comparisons can be automated while ambiguous cases are surfaced as `REVIEW`.

This allows automation to reduce repetitive matching work without treating uncertain OCR output as a definitive regulatory decision.
