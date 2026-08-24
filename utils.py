import os
from decimal import Decimal
import re
import pymupdf
from datetime import datetime


def get_fare_amount_uber(receipt):
    clip = pymupdf.Rect(438.0, 158.0, 578.0, 193.0)
    fare = receipt[0].get_text("text", clip=clip)
    return Decimal(fare[1:].strip())


def get_license_uber(receipt):
    clip = pymupdf.Rect(495.0, 514.5, 578.0, 527.5)
    license_number = receipt[0].get_text("text", clip=clip)
    return license_number.strip()


def get_date_uber(receipt):
    clip = pymupdf.Rect(481.0, 26.5, 567.0, 40.5)
    date_str = receipt[0].get_text("text", clip=clip)
    return datetime.strptime(date_str.strip(), "%d %b %Y").strftime("%Y-%m-%d")


def get_fare_amount_rapido(receipt):
    clip = pymupdf.Rect(253.0, 235.0, 355.0, 273.0)
    text = receipt[0].get_text("text", clip=clip)

    # Match an optional ₹ followed by a decimal number
    match = re.search(r"₹?\s*([\d,]+(?:\.\d+)?)", text)
    if not match:
        raise ValueError(f"Could not find fare amount in:\n{text}")

    amount = match.group(1).replace(",", "")
    return Decimal(amount)


def get_ride_id_rapido(receipt):
    clip = pymupdf.Rect(421.0, 69.5, 583.0, 86.5)
    ride_id = receipt[0].get_text("text", clip=clip)
    return ride_id.strip()


def get_date_rapido(receipt):
    clip = pymupdf.Rect(387.0, 168.0, 593.0, 190.0)
    date_str = receipt[0].get_text("text", clip=clip).strip()

    # Remove st, nd, rd, th from day numbers
    date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)

    return datetime.strptime(
        date_str,
        "%b %d %Y, %I:%M %p"
    ).strftime("%Y-%m-%d")


def pdf_contains_pin(pdf_path, pin):
    """Return True if the PDF contains the specified PIN code."""
    try:
        with pymupdf.open(pdf_path) as doc:
            for page in doc:
                if pin in page.get_text():
                    return True

        return False

    except Exception as e:
        print(f"Could not read {os.path.basename(pdf_path)}: {e}")
        return False




#
# doc = pymupdf.open("workspace/rapido_receipts/CAB_RECEIPT_RD17830441671526808.pdf")
# page = doc[0]
# print( f'Extracted Text : {get_ride_id_rapido(doc)} | {get_fare_amount_rapido(doc)} | {get_date_rapido(doc)}')
#
#
#
#
#
# # Returns a list of Rect objects surrounding each match
# locations = page.search_for("154")
# for rect in locations[:1]:
#     rect[0] = int(rect[0]-39)
#     rect[1] = int(rect[1]-2)
#     rect[2] = int(rect[2]+20)
#     rect[3] = int(rect[3]+2)
#
#     print(rect)  # e.g. Rect(72.0, 120.5, 210.0, 134.0)
#
#     # Create a shape object to draw on
#     shape = page.new_shape()
#
#     # Draw the rectangle
#     shape.draw_rect(pymupdf.Rect(387.0, 169.0, 593.0, 189.0)) # (rect)
#
#     # Apply colors and line width, then finish the path
#     shape.finish(
#         color=pymupdf.pdfcolor["red"],
#         width=1
#     )
#
#     # Commit the shape to the page
#     shape.commit()
#
#     text_extracted = doc[0].get_text("text", clip=rect)
#
#     # Save the PDF
#     doc.save("output.pdf")
#
#     print( f'Extracted Text : {get_fare_amount_rapido(doc)}')
