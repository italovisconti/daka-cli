<p align="center">
  <img src="static/daka-cli-logo.png" alt="daka-cli logo" width="340" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/CLI-Typer-ff6348" alt="Typer" />
  <img src="https://img.shields.io/badge/TUI-Rich-212121" alt="Rich" />
  <img src="https://img.shields.io/badge/License-MIT-4CAF50" alt="License" />
</p>

<h1 align="center">daka-cli</h1>

<p align="center">
  CLI no oficial para explorar productos, buscar ofertas, consultar precios en USD y Bs., armar presupuestos, ubicar sucursales físicas y calcular la tasa de cambio de <strong>Tiendas Daka</strong> (Venezuela) desde tu terminal.
</p>

<p align="center">
  <em>"— ¿Para qué sirve eso?"</em><br>
  <em>"— ¿Nunca has querido revisar Daka desde la terminal...?"</em>
</p>

---

## Índice

- [Instalación](#instalación)
- [Guía de Uso](#guía-de-uso)
  - [Carrito y Simulador de Presupuesto](#carrito-y-simulador-de-presupuesto)
  - [Buscar Productos](#buscar-productos)
  - [Ofertas y Promociones](#ofertas-y-promociones)
  - [Ver y Abrir Productos](#ver-y-abrir-productos)
  - [Comparar Productos](#comparar-productos)
  - [Sucursales Físicas](#sucursales-físicas)
  - [Tasa de Cambio y Conversión](#tasa-de-cambio-y-conversión)
  - [Categorías](#categorías)
- [Licencia](#licencia)

---

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/italovisconti/daka-cli.git
cd daka-cli

# Instalar en modo editable
pip install -e .
```

---

## Guía de Uso

### Carrito y Simulador de Presupuesto
Arma una cotización o presupuesto agregando productos al carrito virtual local. Calcula totales en USD y VEF (a la tasa de Daka) y permite exportar a CSV, JSON o TXT.

```bash
# Agregar un producto al carrito (por slug, ID o búsqueda)
daka carrito add "televisor lg"
daka carrito add "nevera midea" -n 2

# Ver productos en el carrito y total cotizado en USD y Bs.
daka carrito

# Eliminar un producto por índice (#) o nombre
daka carrito rm 1

# Exportar cotización a archivo CSV, JSON o TXT
daka carrito export cotizacion_cocina.csv

# Vaciar carrito
daka carrito clear
```

### Buscar Productos
Busca productos por texto, categoría, rango de precio o criterio de orden.

```bash
# Búsqueda simple
daka buscar "televisor"

# Ordenar por precio ascendente
daka buscar "televisor" -s precio-asc

# Filtrar por categoría y rango de precio (USD)
daka buscar "aire" -c "Aires y Ventilación" --min-precio 100 --max-precio 300
```

### Ofertas y Promociones
Consulta promociones destacadas y productos con mayor descuento.

```bash
# Ofertas del día
daka ofertas

# Mayores descuentos
daka ofertas --tipo descuentos
```

### Ver y Abrir Productos
Muestra la ficha técnica completa o abre el producto en el navegador.

```bash
# Ver ficha técnica
daka ver <SLUG_O_ID_PRODUCTO>

# Abrir en el navegador web
daka abrir <SLUG_O_ID_PRODUCTO>
```

### Comparar Productos
Compara especificaciones y precios de dos productos lado a lado.

```bash
daka comparar <SLUG_PRODUCTO_1> <SLUG_PRODUCTO_2>
```

### Sucursales Físicas
Lista las tiendas Daka en Venezuela con su dirección, horario y ubicación en Google Maps.

```bash
# Listar todas las tiendas
daka tiendas

# Filtrar por ciudad
daka tiendas -c caracas
```

### Tasa de Cambio y Conversión
Calcula la tasa de cambio implícita en Bs./USD de Daka y convierte montos.

```bash
# Consultar tasa actual
daka bcv

# Convertir un monto en USD a Bs.
daka bcv 150
```

### Categorías
Muestra el árbol jerárquico de categorías disponibles en la tienda.

```bash
daka categorias
```

---

## Licencia

[MIT License](LICENSE)
