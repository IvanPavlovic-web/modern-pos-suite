from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
import io


def _header(c, width, height, title):
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 16)
    c.drawCentredString(width / 2, height - 25 * mm, 'POS SISTEM d.o.o.')
    c.setFont('Helvetica', 9)
    c.drawCentredString(width / 2, height - 31 * mm, 'Ulica Zmaja od Bosne 1, Sarajevo')
    c.drawCentredString(width / 2, height - 36 * mm, 'ID: 4200000000000  |  PDV: 200000000000')
    c.setFont('Helvetica-Bold', 13)
    c.drawCentredString(width / 2, height - 50 * mm, title)


def generate_receipt(sale):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    _header(c, width, height, 'FISKALNI RAČUN')

    c.setFont('Helvetica', 10)
    c.drawString(20 * mm, height - 60 * mm, f'Broj računa: {sale.receipt_number}')
    c.drawString(20 * mm, height - 66 * mm, f'Datum: {sale.created_at.strftime("%d.%m.%Y %H:%M:%S")}')
    c.drawString(20 * mm, height - 72 * mm, f'Kasir: {sale.cashier.username if sale.cashier else "-"}')

    payment_label = sale.get_payment_method_display()
    if sale.payment_method == 'SPLIT' and sale.payment_splits:
        parts = [f"{p.get('method', '')}: {p.get('amount', 0)} KM" for p in sale.payment_splits]
        payment_label = 'Split: ' + ', '.join(parts)
    c.drawString(20 * mm, height - 78 * mm, f'Plaćanje: {payment_label}')

    if sale.customer_name:
        c.drawString(20 * mm, height - 84 * mm, f'Kupac: {sale.customer_name}')

    c.line(20 * mm, height - 88 * mm, width - 20 * mm, height - 88 * mm)

    c.setFont('Helvetica-Bold', 10)
    c.drawString(20 * mm, height - 94 * mm, 'Artikal')
    c.drawString(100 * mm, height - 94 * mm, 'Kol.')
    c.drawString(120 * mm, height - 94 * mm, 'Cijena')
    c.drawString(150 * mm, height - 94 * mm, 'Ukupno')

    y = height - 100 * mm
    c.setFont('Helvetica', 10)

    for item in sale.items.all():
        c.drawString(20 * mm, y, item.product.name[:35])
        c.drawString(100 * mm, y, str(item.quantity))
        c.drawString(120 * mm, y, f'{item.unit_price:.2f}')
        c.drawString(150 * mm, y, f'{item.line_total:.2f}')
        y -= 6 * mm

    c.line(20 * mm, y - 3 * mm, width - 20 * mm, y - 3 * mm)

    c.setFont('Helvetica-Bold', 11)
    if sale.discount_amount and sale.discount_amount > 0:
        c.drawString(20 * mm, y - 12 * mm, f'Popust ({sale.discount_percent}%): -{sale.discount_amount:.2f} KM')
        y -= 8 * mm
    c.drawString(20 * mm, y - 12 * mm, f'PDV: {sale.total_tax:.2f} KM')
    c.drawString(20 * mm, y - 20 * mm, f'UKUPNO: {sale.total:.2f} KM')

    c.setFont('Helvetica-Oblique', 8)
    c.drawCentredString(width / 2, 20 * mm, 'Hvala na kupovini!')

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def generate_refund_receipt(refund):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    _header(c, width, height, 'STORNO RAČUN')

    c.setFont('Helvetica', 10)
    c.drawString(20 * mm, height - 60 * mm, f'Broj storna: {refund.receipt_number}')
    c.drawString(20 * mm, height - 66 * mm, f'Original: {refund.original_sale.receipt_number}')
    c.drawString(20 * mm, height - 72 * mm, f'Datum: {refund.created_at.strftime("%d.%m.%Y %H:%M:%S")}')
    c.drawString(20 * mm, height - 78 * mm, f'Kasir: {refund.cashier.username if refund.cashier else "-"}')
    c.drawString(20 * mm, height - 84 * mm, f'Način: {refund.get_payment_method_display()}')

    if refund.reason:
        c.drawString(20 * mm, height - 90 * mm, f'Razlog: {refund.reason[:60]}')

    c.line(20 * mm, height - 94 * mm, width - 20 * mm, height - 94 * mm)

    c.setFont('Helvetica-Bold', 10)
    c.drawString(20 * mm, height - 100 * mm, 'Artikal')
    c.drawString(100 * mm, height - 100 * mm, 'Kol.')
    c.drawString(120 * mm, height - 100 * mm, 'Cijena')
    c.drawString(150 * mm, height - 100 * mm, 'Ukupno')

    y = height - 106 * mm
    c.setFont('Helvetica', 10)

    for item in refund.items.all():
        c.drawString(20 * mm, y, item.sale_item.product.name[:35])
        c.drawString(100 * mm, y, str(item.quantity))
        c.drawString(120 * mm, y, f'{item.unit_price:.2f}')
        c.drawString(150 * mm, y, f'{item.line_total:.2f}')
        y -= 6 * mm

    c.line(20 * mm, y - 3 * mm, width - 20 * mm, y - 3 * mm)

    c.setFont('Helvetica-Bold', 12)
    c.drawString(20 * mm, y - 15 * mm, f'UKUPNO ZA POVRAT: {refund.total:.2f} KM')

    c.setFont('Helvetica-Oblique', 8)
    c.drawCentredString(width / 2, 20 * mm, 'Storno račun')

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer