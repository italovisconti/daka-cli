<p align="center">
  <!-- LOGO_PLACEHOLDER: Reemplaza la URL de abajo con la imagen o ruta de tu logo -->
  <img src="https://via.placeholder.com/150?text=LOGO+DAKA-CLI" alt="daka-cli logo" width="180" />
</p>

<h1 align="center">daka-cli</h1>

<p align="center">
  CLI no oficial para explorar productos, buscar ofertas, consultar precios en USD y Bs., ubicar sucursales físicas y calcular la tasa de cambio de <strong>Tiendas Daka</strong> (Venezuela) desde tu terminal.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/CLI-Typer-ff6348" alt="Typer" />
  <img src="https://img.shields.io/badge/TUI-Rich-212121" alt="Rich" />
  <img src="https://img.shields.io/badge/License-MIT-4CAF50" alt="License" />
</p>

---

## 📦 Instalación

```bash
# Clonar el repositorio
git clone https://github.com/italovisconti/daka-cli.git
cd daka-cli

# Instalar en modo editable
pip install -e .
```

---

## 🚀 Guía de Uso

### 🔍 Buscar Productos
Busca productos por texto, categoría, rango de precio o criterio de orden.

```bash
# Búsqueda simple
daka buscar "televisor"

# Ordenar por precio ascendente
daka buscar "televisor" -s precio-asc

# Filtrar por categoría y rango de precio (USD)
daka buscar "aire" -c "Aires y Ventilación" --min-precio 100 --max-precio 300
```

### 🔥 Ofertas y Promociones
Consulta promociones destacadas y productos con mayor descuento.

```bash
# Ofertas del día
daka ofertas

# Mayores descuentos
daka ofertas --tipo descuentos
```

### 👁️ Ver y Abrir Productos
Muestra la ficha técnica completa o abre el producto en el navegador.

```bash
# Ver ficha técnica
daka ver <SLUG_O_ID_PRODUCTO>

# Abrir en el navegador web
daka abrir <SLUG_O_ID_PRODUCTO>
```

### ⚔️ Comparar Productos
Compara especificaciones y precios de dos productos lado a lado.

```bash
daka comparar <SLUG_PRODUCTO_1> <SLUG_PRODUCTO_2>
```

### 🏬 Sucursales Físicas
Lista las tiendas Daka en Venezuela con su dirección, horario y ubicación en Google Maps.

```bash
# Listar todas las tiendas
daka tiendas

# Filtrar por ciudad
daka tiendas -c caracas
```

### 💵 Tasa de Cambio y Conversión
Calcula la tasa de cambio implícita en Bs./USD de Daka y convierte montos.

```bash
# Consultar tasa actual
daka bcv

# Convertir un monto en USD a Bs.
daka bcv 150
```

### 🗂️ Categorías
Muestra el árbol jerárquico de categorías disponibles en la tienda.

```bash
daka categorias
```

---

## 📄 Licencia

[MIT License](LICENSE)
