# utils/pdf_utils.py

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
import io


# ---------------------------------------------------
# 1️⃣ CHALLAN PDF  (simple, usable)
# ---------------------------------------------------
def challan_pdf(meta, rows):
    """
    meta = {
      'challan_no','date','from_city','to_city',
      'truck_no','driver_name','driver_mobile',
      'hire','loading_hamali','unloading_hamali',
      'other_exp','balance'
    }

    rows = [
      { 'token_no', 'party_name', 'weight', 'amount' }
    ]
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    pw, ph = A4
    margin = 15 * mm

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(pw / 2, ph - 35, "TRANSPORT CHALLAN")

    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(
        pw / 2,
        ph - 55,
        f"{meta['from_city']} → {meta['to_city']}"
    )

    # Top details
    c.setFont("Helvetica", 10)
    y = ph - 80
    c.drawString(margin, y, f"Challan No: {meta['challan_no']}")
    c.drawString(pw / 2, y, f"Date: {meta['date']}")

    y -= 15
    c.drawString(margin, y, f"Truck: {meta['truck_no']}")
    c.drawString(pw / 2, y, f"Driver: {meta['driver_name']} ({meta['driver_mobile']})")

    # Table
    table_data = [["Token No", "Party", "Weight", "Amount (₹)"]]
    total_weight = 0
    total_amount = 0

    for r in rows:
        w = r.get("weight", 0) or 0
        a = r.get("amount", 0) or 0
        total_weight += w
        total_amount += a
        table_data.append([
            str(r.get("token_no", "")),
            str(r.get("party_name", "")),
            f"{w:.0f}",
            f"{a:.2f}",
        ])

    table_data.append(["TOTAL", "", f"{total_weight:.0f}", f"{total_amount:.2f}"])

    t = Table(table_data, colWidths=[60, 200, 60, 80])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

        ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#FFF2CC')),
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -2), 9),

        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FFD966')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),

        ('ALIGN', (2, 1), (3, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.8, colors.black),
    ]))

    w, h = t.wrap(0, 0)
    t.drawOn(c, margin, ph - 130 - h)

    # Summary below table
    y2 = ph - 130 - h - 30
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y2, f"Gadi Bhadha (Hire): {meta['hire']:.2f}")
    y2 -= 14
    c.drawString(margin, y2, f"Loading Hamali: {meta['loading_hamali']:.2f}")
    y2 -= 14
    c.drawString(margin, y2, f"Unloading Hamali: {meta['unloading_hamali']:.2f}")
    y2 -= 14
    c.drawString(margin, y2, f"Other Exp: {meta['other_exp']:.2f}")
    y2 -= 16
    c.drawString(margin, y2, f"Balance: {meta['balance']:.2f}")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------
# 2️⃣ BILL PDF  (STYLE LIKE WEEKLY BILL SAMPLE)
# ---------------------------------------------------
def bill_pdf(header, rows):
    """
    header = {
        'party_name',
        'from_date',
        'to_date',
        'total_weight',
        'total_pkgs',
        'total_amount',
        # optional:
        'old_balance' (float, default 0.0)
    }

    rows = [
      {
        'token_no',
        'datetime',
        'from_city',
        'to_city',
        'weight',
        'packages',
        'amount',
      }
    ]
    """
    party_name = header["party_name"]
    from_date = header["from_date"]
    to_date = header["to_date"]
    total_weight = header["total_weight"]
    total_pkgs = header["total_pkgs"]
    total_amount = header["total_amount"]
    old_balance = float(header.get("old_balance", 0.0))

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    pw, ph = A4
    margin = 15 * mm

    # Title & header text (similar to weekly bill style)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(pw / 2, ph - 35, "BILL")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, ph - 60, f"Party: {party_name}")
    c.drawString(margin, ph - 75, f"Period: {from_date} to {to_date}")

    # Try to determine route from first row, if available
    route_text = ""
    if rows:
        f = rows[0].get("from_city", "")
        t = rows[0].get("to_city", "")
        if f and t:
            route_text = f"Route: {f} → {t}"
            c.drawString(margin, ph - 90, route_text)

    # Table data
    table_start_y = ph - 120
    table_data = [["DATE", "TOKEN NO", "FROM", "TO", "WT (KG)", "PKGS", "AMOUNT (Rs)"]]

    for r in rows:
        dt_str = str(r.get("datetime", "")) or ""
        # Just date part (e.g. "10-11-2025 04:50 PM" -> "10-11-2025")
        date_only = dt_str.split(" ")[0] if dt_str else ""
        table_data.append([
            date_only,
            str(r.get("token_no", "")),
            str(r.get("from_city", "")),
            str(r.get("to_city", "")),
            f"{float(r.get('weight', 0) or 0):.0f}",
            f"{float(r.get('packages', 0) or 0):.0f}",
            f"{float(r.get('amount', 0) or 0):.2f}",
        ])

    # SUBTOTAL row
    table_data.append([
        "SUBTOTAL",
        "",
        "",
        "",
        f"{total_weight:.0f}",
        f"{total_pkgs:.0f}",
        f"{total_amount:.2f}",
    ])

    # Blank row
    table_data.append(["", "", "", "", "", "", ""])

    # OLD BALANCE row
    table_data.append([
        "OLD BALANCE",
        "",
        "",
        "",
        "",
        "",
        f"{old_balance:.2f}",
    ])

    # FINAL TOTAL row
    final_total = total_amount + old_balance
    table_data.append([
        "FINAL TOTAL",
        "",
        "",
        "",
        f"{total_weight:.0f}",     # normally same weight
        f"{total_pkgs:.0f}",
        f"{final_total:.2f}",
    ])

    col_widths = [60, 60, 70, 70, 60, 50, 80]
    t = Table(table_data, colWidths=col_widths)

    last_row = len(table_data) - 1
    old_bal_row = last_row - 1
    blank_row = last_row - 2
    subtotal_row = blank_row - 1

    style = [
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), "CENTER"),

        # Data rows (1 .. subtotal_row-1)
        ('BACKGROUND', (0, 1), (-1, subtotal_row - 1), colors.HexColor("#FFF2CC")),
        ('FONTNAME', (0, 1), (-1, subtotal_row - 1), "Helvetica"),
        ('FONTSIZE', (0, 1), (-1, subtotal_row - 1), 8.5),

        # SUBTOTAL row
        ('BACKGROUND', (0, subtotal_row), (-1, subtotal_row), colors.HexColor("#D9E2F3")),
        ('FONTNAME', (0, subtotal_row), (-1, subtotal_row), "Helvetica-Bold"),

        # Blank row
        ('BACKGROUND', (0, blank_row), (-1, blank_row), colors.white),
        ('GRID', (0, blank_row), (-1, blank_row), 0, colors.white),

        # OLD BALANCE row
        ('BACKGROUND', (0, old_bal_row), (-1, old_bal_row), colors.HexColor("#E7E6E6")),
        ('FONTNAME', (0, old_bal_row), (-1, old_bal_row), "Helvetica-Bold"),

        # FINAL TOTAL row
        ('BACKGROUND', (0, last_row), (-1, last_row), colors.HexColor("#4472C4")),
        ('TEXTCOLOR', (0, last_row), (-1, last_row), colors.white),
        ('FONTNAME', (0, last_row), (-1, last_row), "Helvetica-Bold"),
        ('FONTSIZE', (0, last_row), (-1, last_row), 9.5),

        # Alignment
        ('ALIGN', (0, 1), (3, last_row), "LEFT"),
        ('ALIGN', (4, 1), (6, last_row), "RIGHT"),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.8, colors.black),
        ('LINEABOVE', (0, subtotal_row), (-1, subtotal_row), 1.2, colors.black),
        ('LINEABOVE', (0, last_row), (-1, last_row), 1.2, colors.black),
    ]

    t.setStyle(TableStyle(style))

    w, h = t.wrap(0, 0)
    t.drawOn(c, margin, table_start_y - h)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------
# 3️⃣ LEDGER PDF  (STYLE LIKE WEEKLY LEDGER SAMPLE)
# ---------------------------------------------------
def ledger_pdf(header, rows):
    """
    header = {
      'party_name',
      'from_date',
      'to_date',
      'opening_balance',
      'closing_balance'
    }

    rows = [
      {
        'date',      # "dd-mm-YYYY"
        'type',      # TOKEN / PAYMENT
        'details',   # e.g. "Token #12" / "Payment (Cash)"
        'debit',     # float
        'credit',    # float
        'balance',   # float (running)
      }
    ]
    """
    party_name = header["party_name"]
    from_date = header["from_date"]
    to_date = header["to_date"]
    opening_balance = float(header.get("opening_balance", 0.0))
    closing_balance = float(header.get("closing_balance", 0.0))

    # compute totals
    total_debit = sum(float(r.get("debit", 0) or 0) for r in rows)
    total_credit = sum(float(r.get("credit", 0) or 0) for r in rows)

    # Add TOTAL row at bottom (like summary)
    total_row = {
        "date": "",
        "type": "TOTAL",
        "details": "",
        "debit": total_debit,
        "credit": total_credit,
        "balance": closing_balance,
    }
    all_rows = list(rows) + [total_row]

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    pw, ph = A4
    margin = 15 * mm

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(pw / 2, ph - 35, "LEDGER")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, ph - 60, f"Party: {party_name}")
    c.drawString(margin, ph - 75, f"Period: {from_date} to {to_date}")
    c.drawString(margin, ph - 90, f"Opening Balance: {opening_balance:.2f}")
    c.drawString(margin, ph - 105, f"Closing Balance: {closing_balance:.2f}")

    table_start_y = ph - 135
    table_data = [["DATE", "TYPE", "DETAILS", "DEBIT (₹)", "CREDIT (₹)", "BALANCE (₹)"]]

    for r in all_rows:
        table_data.append([
            r.get("date", ""),
            r.get("type", ""),
            r.get("details", ""),
            f"{float(r.get('debit', 0) or 0):.2f}",
            f"{float(r.get('credit', 0) or 0):.2f}",
            f"{float(r.get('balance', 0) or 0):.2f}",
        ])

    col_widths = [60, 50, 160, 60, 60, 70]
    t = Table(table_data, colWidths=col_widths)

    last_row = len(table_data) - 1  # TOTAL row index

    style = [
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), "CENTER"),

        # Normal rows
        ('BACKGROUND', (0, 1), (-1, last_row - 1), colors.HexColor("#FFF2CC")),
        ('FONTNAME', (0, 1), (-1, last_row - 1), "Helvetica"),
        ('FONTSIZE', (0, 1), (-1, last_row - 1), 8.5),

        # TOTAL row (last)
        ('BACKGROUND', (0, last_row), (-1, last_row), colors.HexColor("#FFD966")),
        ('FONTNAME', (0, last_row), (-1, last_row), "Helvetica-Bold"),

        # Alignments
        ('ALIGN', (0, 1), (2, last_row), "LEFT"),
        ('ALIGN', (3, 1), (5, last_row), "RIGHT"),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.8, colors.black),
        ('LINEABOVE', (0, last_row), (-1, last_row), 1.2, colors.black),
    ]

    t.setStyle(TableStyle(style))

    w, h = t.wrap(0, 0)
    t.drawOn(c, margin, table_start_y - h)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()
