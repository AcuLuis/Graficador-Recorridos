"""Paleta del lienzo.

Cada color tiene un solo significado: los tonos fríos identifican
componentes, el naranja es la selección, el amarillo una acción pendiente
y el verde el resultado de un algoritmo.
"""

FONDO = '#f5f7fa'

# Nodos según la componente conexa (se asigna por el menor nodo de la
# componente, así que no cambia al editar otras partes del grafo).
PALETA_COMPONENTES = ['#2563eb', '#0d9488', '#7c3aed', '#db2777', '#0891b2', '#4f46e5', '#9333ea', '#0369a1']

NODO_AISLADO = '#94a3b8'
NODO_SELECCIONADO = '#f97316'
BORDE_SELECCIONADO = '#9a3412'
NODO_ORIGEN_ARISTA = '#facc15'
BORDE_ORIGEN_ARISTA = '#a16207'
BORDE_DESTACADO = '#0f172a'

ARISTA = '#64748b'
ARISTA_SELECCIONADA = NODO_SELECCIONADO
RESULTADO = '#16a34a'

ETIQUETA_PESO = '#0f172a'
BORDE_ETIQUETA = '#cbd5e1'

TEXTO_CLARO = '#ffffff'
TEXTO_OSCURO = '#0f172a'


def color_componente(nodo_minimo):
    return PALETA_COMPONENTES[hash(nodo_minimo) % len(PALETA_COMPONENTES)]


def texto_sobre(color_hex):
    """Color de texto legible sobre un fondo (luminancia relativa simple)."""
    color_hex = color_hex.lstrip('#')
    r, g, b = (int(color_hex[i:i + 2], 16) / 255 for i in (0, 2, 4))
    luminancia = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return TEXTO_OSCURO if luminancia > 0.6 else TEXTO_CLARO
