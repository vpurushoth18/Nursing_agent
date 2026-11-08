from docx import Document
import json
import re

def parse_rubric_to_json(rubric_path):
    doc = Document(rubric_path)
    rubric_data = {"sections": []}
    current_section = None

    if not doc.tables:
        return rubric_data

    table = doc.tables[0]

    for row in table.rows:
        # 1. Clean cells: remove whitespace and normalize "smart" quotes/newlines
        cells = []
        for cell in row.cells:
            text = cell.text.strip()
            # Replace smart quotes with standard ones to avoid JSON encoding issues
            text = text.replace('“', '"').replace('”', '"').replace('’', "'")
            # Replace multiple newlines/tabs with a single space
            text = re.sub(r'\s+', ' ', text)
            cells.append(text)

        if not cells or not cells[0]:
            continue

        # Skip header row
        if "TEST ITEM" in cells[0]:
            continue

        # Signal 1: Detect Section Header (ALL CAPS and contains PT)
        if cells[0].isupper() and len(cells) > 1 and "PT" in cells[1]:
            current_section = {
                "section_name": cells[0],
                "total_points": cells[1],
                "criteria": [] 
            }
            rubric_data["sections"].append(current_section)
            continue

        # Signal 2: Detect Criterion (Point value in the second column)
        if len(cells) > 1:
            clean_val = cells[1].replace('PT', '').strip()
            if clean_val.isdigit():
                if current_section is not None:
                    # Collect description from all cells except the point value cell
                    description = " ".join([c for i, c in enumerate(cells) if i != 1 and c])

                    current_section["criteria"].append({
                        "id": f"item_{len(rubric_data['sections'])}_{len(current_section['criteria'])}",
                        "description": description.strip(),
                        "point_value": int(clean_val),
                        "points_earned": 0,
                        "evidence": "",
                        "timestamp": ""
                    })

    return rubric_data