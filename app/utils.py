from xhtml2pdf import pisa
from io import BytesIO

def generar_pdf_desde_html(html_content):
    """Recibe un string con HTML y devuelve los bytes del PDF.
       Retorna None si hubo un error."""
    
    output = BytesIO()

    #pisa.CreatePDF convierte el HTML en el buffer output.
    pisa_status = pisa.CreatePDF(BytesIO(html_content.encode('utf-8')), dest=output)

    if pisa_status.err:
        return None
    
    #Regresamos al inicio del buffer para leerlo.
    output.seek(0)
    return output.read()
