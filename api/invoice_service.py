import io
import os
from decimal import Decimal, ROUND_HALF_UP

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .models import Invoice

ACCENT = colors.HexColor("#185FA5")
INK = colors.HexColor("#1A1F29")
MUTED = colors.HexColor("#6B7280")
FAINT = colors.HexColor("#9AA1AC")
HAIRLINE = colors.HexColor("#E6E8EC")
PANEL = colors.HexColor("#F7F8FA")
WHITE = colors.white

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

for reg, bold, rpath, bpath in [
    ("Uni", "UniBold",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("Uni", "UniBold",
     os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans.ttf"),
     os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans-Bold.ttf")),
]:
    if os.path.exists(rpath) and os.path.exists(bpath):
        try:
            pdfmetrics.registerFont(TTFont(reg, rpath))
            pdfmetrics.registerFont(TTFont(bold, bpath))
            FONT, FONT_BOLD = reg, bold
            break
        except Exception:
            continue


def _money(symbol, amount):
    q = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{symbol} {q:,.2f}"


def _p(text, font=None, size=9, color=INK, align=TA_LEFT, leading=None):
    return Paragraph(text, ParagraphStyle(
        "s", fontName=font or FONT, fontSize=size, textColor=color,
        alignment=align, leading=leading or size * 1.35,
    ))


def build_invoice_pdf(invoice):
    buffer = io.BytesIO()
    sym = invoice.currency_symbol
    frm, to = invoice.billing_from, invoice.billing_to

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=16 * mm, bottomMargin=18 * mm,
        title=f"Invoice {invoice.invoice_id}",
    )
    W = doc.width
    story = []

    header = Table(
        [[
            [_p(frm.name, FONT_BOLD, 17, INK, leading=20),
             _p(f"{frm.email}  \u00b7  {frm.phone_number}", FONT, 8.5, MUTED, leading=12)],
            [_p("INVOICE", FONT_BOLD, 9, ACCENT, TA_RIGHT, leading=12),
             _p(invoice.invoice_id, FONT_BOLD, 15, INK, TA_RIGHT, leading=18)],
        ]],
        colWidths=[W * 0.6, W * 0.4],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header)

    story.append(Spacer(1, 10))
    strip = Table([[""]], colWidths=[W], rowHeights=[3])
    strip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(strip)
    story.append(Spacer(1, 16))

    def party(label, info, lines):
        cell = [
            _p(label, FONT_BOLD, 7.5, FAINT, leading=11),
            Spacer(1, 5),
            _p(info.name, FONT_BOLD, 10.5, INK, leading=14),
        ]
        cell += [_p(l, FONT, 8.5, MUTED, leading=12) for l in lines]
        return cell

    meta = [
        _p("DATE OF ISSUE", FONT_BOLD, 7.5, FAINT, leading=11),
        Spacer(1, 5),
        _p(invoice.current_date, FONT, 9, INK, leading=13),
        Spacer(1, 8),
        _p("DUE DATE", FONT_BOLD, 7.5, FAINT, leading=11),
        Spacer(1, 5),
        _p(invoice.due_date, FONT, 9, INK, leading=13),
    ]

    from_lines = [l for l in frm.address.split("\n") if l]
    to_lines = [to.email] + [l for l in to.address.split("\n") if l] + [to.phone_number]

    parties = Table(
        [[party("FROM", frm, from_lines), party("BILL TO", to, to_lines), meta]],
        colWidths=[W * 0.38, W * 0.38, W * 0.24],
    )
    parties.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), PANEL),
        ("LEFTPADDING", (0, 0), (0, 0), 14),
        ("LEFTPADDING", (1, 0), (-1, -1), 10),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    story.append(parties)
    story.append(Spacer(1, 22))

    rows = [[
        _p("DESCRIPTION", FONT_BOLD, 7.5, WHITE, leading=11),
        _p("QTY", FONT_BOLD, 7.5, WHITE, TA_RIGHT, leading=11),
        _p("UNIT PRICE", FONT_BOLD, 7.5, WHITE, TA_RIGHT, leading=11),
        _p("AMOUNT", FONT_BOLD, 7.5, WHITE, TA_RIGHT, leading=11),
    ]]

    subtotal = Decimal("0")
    for it in invoice.items:
        line = it.price * it.quantity
        subtotal += line
        desc = [_p(it.name, FONT, 9.5, INK, leading=13)]
        if it.description:
            desc.append(_p(it.description, FONT, 8, FAINT, leading=11))
        rows.append([
            desc,
            _p(str(it.quantity), FONT, 9.5, INK, TA_RIGHT, leading=13),
            _p(_money(sym, it.price), FONT, 9.5, INK, TA_RIGHT, leading=13),
            _p(_money(sym, line), FONT, 9.5, INK, TA_RIGHT, leading=13),
        ])

    items = Table(rows, colWidths=[W * 0.50, W * 0.12, W * 0.19, W * 0.19], repeatRows=1)
    istyle = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, -1), 12),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 12),
        ("LEFTPADDING", (1, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-2, -1), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING", (0, 1), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 9),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, HAIRLINE),
    ]
    for i in range(2, len(rows), 2):
        istyle.append(("BACKGROUND", (0, i), (-1, i), PANEL))
    items.setStyle(TableStyle(istyle))
    story.append(items)
    story.append(Spacer(1, 4))

    discount_amt = subtotal * invoice.discount / Decimal("100")
    taxable = subtotal - discount_amt
    tax_amt = taxable * invoice.tax_rate / Decimal("100")
    grand = taxable + tax_amt

    def srow(label, value):
        return [
            "",
            _p(label, FONT, 9, MUTED, TA_RIGHT, leading=13),
            _p(value, FONT, 9, INK, TA_RIGHT, leading=13),
        ]

    summary = Table(
        [
            srow("Subtotal", _money(sym, subtotal)),
            srow(f"Discount ({invoice.discount:g}%)", f"\u2212 {_money(sym, discount_amt)}"),
            srow(f"Tax ({invoice.tax_rate:g}%)", f"+ {_money(sym, tax_amt)}"),
        ],
        colWidths=[W * 0.50, W * 0.31, W * 0.19],
    )
    summary.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(summary)
    story.append(Spacer(1, 8))

    total_band = Table(
        [[
            _p("TOTAL DUE", FONT_BOLD, 11, WHITE, TA_RIGHT, leading=15),
            _p(_money(sym, grand), FONT_BOLD, 13, WHITE, TA_RIGHT, leading=15),
        ]],
        colWidths=[W * 0.7, W * 0.3],
    )
    total_band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    story.append(total_band)

    story.append(Spacer(1, 26))
    note = invoice.notes or "Thank you for your business."
    footer = Table(
        [[_p("NOTES", FONT_BOLD, 7.5, FAINT, leading=11)],
         [_p(note, FONT, 8.5, MUTED, leading=13)]],
        colWidths=[W],
    )
    footer.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (0, 0), 12),
        ("BOTTOMPADDING", (0, 0), (0, 0), 4),
        ("TOPPADDING", (0, 1), (0, 1), 0),
        ("BOTTOMPADDING", (0, 1), (0, 1), 0),
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, HAIRLINE),
    ]))
    story.append(footer)

    doc.build(story)
    buffer.seek(0)
    return buffer