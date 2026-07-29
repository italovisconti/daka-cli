from __future__ import annotations

import contextlib
import json
import sys
import webbrowser
from importlib.metadata import PackageNotFoundError, version
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from typer.core import TyperCommand, TyperGroup, TyperOption

from .client import Category, DakaClient, DakaError, Product, StoreBranch, TAG_MAP
from .image_render import TerminalProtocol, render_image

try:
    VERSION = version("daka-cli")
except PackageNotFoundError:
    VERSION = "0.1.0"


class SpanishTyperGroup(TyperGroup):
    def get_help_option(self, ctx: Any) -> TyperOption | None:
        option = super().get_help_option(ctx)
        if option is not None:
            option.help = "Mostrar esta ayuda y salir."
        return option


class SpanishTyperCommand(TyperCommand):
    def get_help_option(self, ctx: Any) -> TyperOption | None:
        option = super().get_help_option(ctx)
        if option is not None:
            option.help = "Mostrar esta ayuda y salir."
        return option


app = typer.Typer(no_args_is_help=True, add_completion=False, cls=SpanishTyperGroup)
console = Console()
error_console = Console(stderr=True)


def fail(message: str) -> None:
    error_console.print(f"[bold red]Error:[/] {message}")
    raise typer.Exit(code=1)


def version_callback(value: bool) -> None:
    if value:
        console.print(f"daka-cli v{VERSION}")
        raise typer.Exit()


@app.callback()
def main(
    version_flag: Annotated[
        bool,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Mostrar la versión de daka-cli y salir."),
    ] = False,
) -> None:
    """CLI no oficial para explorar productos, ofertas, fotos, tiendas y precios de Tiendas Daka (Venezuela)."""


def _spinner(text: str = "Consultando Tiendas Daka...") -> Any:
    if sys.stderr.isatty():
        return error_console.status(f"[bold yellow]{text}[/]", spinner="dots")
    return contextlib.nullcontext()


def _serialize(obj: Any) -> Any:
    if hasattr(obj, "__dict__"):
        return {key: _serialize(val) for key, val in obj.__dict__.items() if not key.startswith("_")}
    if isinstance(obj, dict):
        return {key: _serialize(val) for key, val in obj.items()}
    if isinstance(obj, list):
        return [_serialize(val) for val in obj]
    return obj


def _format_price_usd(amount: float | None) -> str:
    if amount is None:
        return "[dim]N/A[/]"
    return f"${amount:,.2f}"


def _format_price_vef(amount: float | None) -> str:
    if amount is None:
        return "[dim]N/A[/]"
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"Bs. {formatted}"


@app.command("buscar", help="Buscar productos en Tiendas Daka con filtros y ordenación.", cls=SpanishTyperCommand)
def search_cmd(
    query: Annotated[str, typer.Argument(help="Texto a buscar (ej: televisor, aire, nevera)")] = "",
    categoria: Annotated[
        str | None,
        typer.Option("--categoria", "-c", help="ID o nombre/slug de categoría para filtrar"),
    ] = None,
    orden: Annotated[
        str | None,
        typer.Option(
            "--orden",
            "-s",
            help="Criterio de ordenación: precio-asc, precio-desc, descuento, nuevos, antiguos, nombre-asc, nombre-desc",
        ),
    ] = None,
    min_precio: Annotated[float | None, typer.Option("--min-precio", help="Precio mínimo en USD")] = None,
    max_precio: Annotated[float | None, typer.Option("--max-precio", help="Precio máximo en USD")] = None,
    limite: Annotated[int, typer.Option("--limite", "-l", help="Cantidad máxima de resultados")] = 20,
    offset: Annotated[int, typer.Option("--offset", "-o", help="Offset de paginación")] = 0,
    as_json: Annotated[bool, typer.Option("--json", "-j", help="Mostrar respuesta en formato JSON")] = False,
) -> None:
    client = DakaClient()

    category_id = None
    if categoria:
        category_id = categoria
        if not categoria.startswith("pcat_"):
            with _spinner("Buscando categoría..."):
                try:
                    all_cats = client.get_categories()
                    matches = []
                    cat_lower = categoria.lower()

                    def find_cat(cats: list[Category]):
                        for c in cats:
                            if cat_lower in c.name.lower() or cat_lower in c.handle.lower():
                                matches.append(c)
                            find_cat(c.children)

                    find_cat(all_cats)
                    if matches:
                        category_id = matches[0].id
                    else:
                        fail(f"No se encontró ninguna categoría con el nombre '{categoria}'.")
                except DakaError as e:
                    fail(str(e))

    with _spinner(f"Buscando productos '{query}'..."):
        try:
            products, total = client.search_products(
                query=query,
                category_id=category_id,
                min_price=min_precio,
                max_price=max_precio,
                sort=orden,
                limit=limite,
                offset=offset,
            )
        except DakaError as e:
            fail(str(e))
            return

    if as_json:
        out = {
            "query": query,
            "total": total,
            "count": len(products),
            "offset": offset,
            "limit": limite,
            "products": [_serialize(p) for p in products],
        }
        console.print_json(data=out)
        return

    if not products:
        console.print("[yellow]No se encontraron productos que coincidan con la búsqueda.[/]")
        return

    title_info = f"Resultados de búsqueda ({len(products)} de {total})"
    if orden:
        title_info += f" [orden: {orden}]"

    table = Table(
        title=title_info,
        box=None,
        header_style="bold magenta",
        title_style="bold cyan",
    )
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Producto", style="bold white", min_width=35)
    table.add_column("Precio (USD)", justify="right", style="bold green")
    table.add_column("Precio (VEF)", justify="right", style="yellow")
    table.add_column("Descuento", justify="center", style="bold red")
    table.add_column("Handle / Slug", style="dim white")

    for idx, p in enumerate(products, start=offset + 1):
        price_usd_str = _format_price_usd(p.price_usd)
        if p.has_discount:
            price_usd_str = f"[bold green]{price_usd_str}[/] [dim strike]({_format_price_usd(p.original_price_usd)})[/]"

        disc_str = f"-{p.discount_percentage:.0f}%" if p.has_discount else "-"

        table.add_row(
            str(idx),
            escape(p.title),
            price_usd_str,
            _format_price_vef(p.price_vef),
            disc_str,
            p.handle,
        )

    console.print(table)
    console.print(f"\n[dim]Para ver el detalle de un producto ejecuta:[/] [bold cyan]daka ver <handle>[/]")


@app.command("ofertas", help="Listar productos en oferta, promociones y mayores descuentos.", cls=SpanishTyperCommand)
def offers_cmd(
    tipo: Annotated[
        str,
        typer.Option(
            "--tipo",
            "-t",
            help="Tipo de promoción: ofertas (Ofertas del Día), descuentos (Mejores Descuentos), top (Productos Tops), envio-gratis, nuevos",
        ),
    ] = "ofertas",
    limite: Annotated[int, typer.Option("--limite", "-l", help="Cantidad de productos a mostrar")] = 15,
    as_json: Annotated[bool, typer.Option("--json", "-j", help="Mostrar respuesta en formato JSON")] = False,
) -> None:
    client = DakaClient()
    tag_id = TAG_MAP.get(tipo.lower(), TAG_MAP["ofertas"])

    with _spinner(f"Cargando promociones de '{tipo}'..."):
        try:
            products, total = client.search_products(tag_id=tag_id, sort="descuento", limit=limite)
        except DakaError as e:
            fail(str(e))
            return

    if as_json:
        console.print_json(data=[_serialize(p) for p in products])
        return

    if not products:
        console.print("[yellow]No se encontraron ofertas en este momento.[/]")
        return

    table = Table(
        title=f"🔥 Promociones y Ofertas de Tiendas Daka ({tipo.upper()})",
        box=None,
        header_style="bold magenta",
        title_style="bold red",
    )
    table.add_column("#", justify="right", style="dim", width=3)
    table.add_column("Producto", style="bold white", min_width=35)
    table.add_column("Precio Oferta", justify="right", style="bold green")
    table.add_column("Precio Original", justify="right", style="dim strike red")
    table.add_column("Ahorro", justify="center", style="bold yellow")
    table.add_column("Handle", style="dim cyan")

    for idx, p in enumerate(products, start=1):
        savings = f"-{p.discount_percentage:.0f}%" if p.has_discount else "OFERTA"
        orig_str = _format_price_usd(p.original_price_usd) if p.has_discount else "-"

        table.add_row(
            str(idx),
            escape(p.title),
            _format_price_usd(p.price_usd),
            orig_str,
            savings,
            p.handle,
        )

    console.print(table)


@app.command("ver", help="Mostrar el detalle de un producto (con renderizado de imagen en terminal).", cls=SpanishTyperCommand)
def view_cmd(
    producto: Annotated[str, typer.Argument(help="Handle, ID (prod_...) o URL del producto")],
    show_image: Annotated[bool, typer.Option("--img/--no-img", help="Mostrar la imagen del producto en la terminal")] = True,
    img_width: Annotated[int, typer.Option("--img-ancho", "-w", help="Ancho de la imagen en columnas de terminal")] = 35,
    protocolo: Annotated[str, typer.Option("--protocolo", help="Protocolo de imagen: auto, kitty, iterm, ansi")] = "auto",
    open_browser: Annotated[bool, typer.Option("--open", "-o", help="Abrir el producto en el navegador web")] = False,
    as_json: Annotated[bool, typer.Option("--json", "-j", help="Mostrar producto en formato JSON")] = False,
) -> None:
    client = DakaClient()

    with _spinner("Obteniendo detalle del producto..."):
        try:
            p = client.get_product(producto)
        except DakaError as e:
            fail(str(e))
            return

    if open_browser:
        console.print(f"[green]Abriendo[/] {p.web_url} [green]en el navegador...[/]")
        webbrowser.open(p.web_url)

    if as_json:
        console.print_json(data=_serialize(p))
        return

    # Render Product Image in Terminal if requested
    img_rendered_str = ""
    if show_image and (p.thumbnail or p.images):
        img_url = p.thumbnail or p.images[0]
        with _spinner("Descargando y procesando foto del producto..."):
            img_rendered_str = render_image(img_url, width=img_width, protocol=protocolo) # type: ignore

    if img_rendered_str:
        sys.stdout.write(img_rendered_str + "\n")
        sys.stdout.flush()

    title_text = f"[bold white]{escape(p.title)}[/]"
    if p.brand:
        title_text = f"[bold blue][{escape(p.brand)}][/] " + title_text

    usd_str = f"[bold green size=16]{_format_price_usd(p.price_usd)}[/]"
    vef_str = f"[bold yellow]{_format_price_vef(p.price_vef)}[/]"

    if p.has_discount:
        usd_str += f"  [dim strike red]({_format_price_usd(p.original_price_usd)})[/] [bold red]¡OFERTA -{p.discount_percentage:.0f}%![/]"

    panel_content = f"{title_text}\n\n"
    panel_content += f"[bold]Precio USD:[/] {usd_str}\n"
    panel_content += f"[bold]Precio VEF:[/] {vef_str}\n"
    panel_content += f"[bold]ID:[/] [dim]{p.id}[/] | [bold]Handle:[/] [cyan]{p.handle}[/]\n"
    panel_content += f"[bold]URL Web:[/] [link={p.web_url}]{p.web_url}[/link]\n"

    if p.categories:
        panel_content += f"[bold]Categorías:[/] [cyan]{', '.join(p.categories)}[/]\n"

    if p.description:
        desc_clean = escape(p.description.strip())
        panel_content += f"\n[bold yellow]Descripción:[/\n{desc_clean}\n"

    console.print(Panel(panel_content, title="[bold cyan]Detalle del Producto[/]", border_style="cyan"))

    if p.specifications:
        spec_table = Table(title="Especificaciones", box=None, header_style="bold yellow", title_style="bold yellow")
        spec_table.add_column("Característica", style="bold white", width=25)
        spec_table.add_column("Valor", style="dim white")
        for key, val in p.specifications.items():
            spec_table.add_row(escape(key), escape(str(val)))
        console.print(spec_table)

    if len(p.variants) > 1:
        var_table = Table(title="Variantes disponibles", box=None, header_style="bold magenta", title_style="bold magenta")
        var_table.add_column("Variante", style="bold white")
        var_table.add_column("SKU", style="dim white")
        var_table.add_column("Precio USD", style="bold green")
        for v in p.variants:
            var_table.add_row(escape(v.title), v.sku or "-", _format_price_usd(v.price_usd))
        console.print(var_table)

    if p.images:
        console.print(f"\n[bold magenta]Imágenes ({len(p.images)}):[/]")
        for i, img_url in enumerate(p.images[:5], 1):
            console.print(f"  [dim]{i}.[/] {img_url}")


@app.command("imagen", help="Renderizar la imagen de un producto directamente en la terminal (Kitty, iTerm2, ANSI).", cls=SpanishTyperCommand)
def image_cmd(
    producto: Annotated[str, typer.Argument(help="Handle, ID (prod_...) o URL del producto")],
    ancho: Annotated[int, typer.Option("--ancho", "-w", help="Ancho en columnas de terminal")] = 40,
    idx: Annotated[int, typer.Option("--idx", "-i", help="Índice de la imagen (1 para la principal, 2, 3...)")] = 1,
    protocolo: Annotated[str, typer.Option("--protocolo", "-p", help="Protocolo: auto, kitty, iterm, ansi")] = "auto",
) -> None:
    client = DakaClient()

    with _spinner("Obteniendo fotos del producto..."):
        try:
            p = client.get_product(producto)
        except DakaError as e:
            fail(str(e))
            return

    if not p.images and not p.thumbnail:
        fail("Este producto no tiene imágenes disponibles.")

    img_urls = p.images or ([p.thumbnail] if p.thumbnail else [])
    target_idx = max(0, min(idx - 1, len(img_urls) - 1))
    target_url = img_urls[target_idx]

    console.print(f"[bold cyan]📸 Renderizando imagen ({target_idx + 1}/{len(img_urls)}):[/] [dim]{p.title}[/]")

    with _spinner("Renderizando gráfica..."):
        rendered_str = render_image(target_url, width=ancho, protocol=protocolo) # type: ignore

    sys.stdout.write(rendered_str + "\n")
    sys.stdout.flush()


@app.command("comparar", help="Comparar dos productos lado a lado.", cls=SpanishTyperCommand)
def compare_cmd(
    producto1: Annotated[str, typer.Argument(help="Primer producto (handle, ID o URL)")],
    producto2: Annotated[str, typer.Argument(help="Segundo producto (handle, ID o URL)")],
) -> None:
    client = DakaClient()

    with _spinner("Cargando productos para comparación..."):
        try:
            p1 = client.get_product(producto1)
            p2 = client.get_product(producto2)
        except DakaError as e:
            fail(str(e))
            return

    table = Table(title="⚖️ Comparación de Productos", box=None, header_style="bold cyan", title_style="bold yellow")
    table.add_column("Característica", style="bold white", width=22)
    table.add_column(p1.title[:35], style="green", width=35)
    table.add_column(p2.title[:35], style="cyan", width=35)

    table.add_row("Precio USD", _format_price_usd(p1.price_usd), _format_price_usd(p2.price_usd))
    table.add_row("Precio VEF", _format_price_vef(p1.price_vef), _format_price_vef(p2.price_vef))
    table.add_row("Descuento", f"-{p1.discount_percentage:.0f}%" if p1.has_discount else "No", f"-{p2.discount_percentage:.0f}%" if p2.has_discount else "No")
    table.add_row("Marca", p1.brand or "-", p2.brand or "-")
    table.add_row("Categorías", ", ".join(p1.categories) if p1.categories else "-", ", ".join(p2.categories) if p2.categories else "-")

    all_keys = set(p1.specifications.keys()).union(set(p2.specifications.keys()))
    for key in sorted(all_keys):
        v1 = p1.specifications.get(key, "-")
        v2 = p2.specifications.get(key, "-")
        table.add_row(key, str(v1), str(v2))

    console.print(table)


@app.command("tiendas", help="Listar las sucursales físicas de Tiendas Daka en Venezuela.", cls=SpanishTyperCommand)
def stores_cmd(
    ciudad: Annotated[str | None, typer.Option("--ciudad", "-c", help="Filtrar por ciudad (ej: Caracas, Valencia, Maracay)")] = None,
    as_json: Annotated[bool, typer.Option("--json", "-j", help="Mostrar sucursales en formato JSON")] = False,
) -> None:
    client = DakaClient()

    with _spinner("Cargando sucursales de Tiendas Daka..."):
        try:
            stores = client.get_stores(city=ciudad)
        except DakaError as e:
            fail(str(e))
            return

    if as_json:
        console.print_json(data=[_serialize(s) for s in stores])
        return

    if not stores:
        console.print(f"[yellow]No se encontraron sucursales de Tiendas Daka{' para ' + ciudad if ciudad else ''}.[/]")
        return

    table = Table(
        title=f"🏬 Sucursales Físicas de Tiendas Daka ({len(stores)})",
        box=None,
        header_style="bold magenta",
        title_style="bold cyan",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Sucursal", style="bold white", width=25)
    table.add_column("Ciudad", style="bold yellow", width=15)
    table.add_column("Dirección", style="dim white", width=45)
    table.add_column("Horario", style="cyan", width=15)
    table.add_column("Google Maps", style="link blue")

    for idx, s in enumerate(stores, start=1):
        schedule = f"{s.opening_time} - {s.closing_time}"
        maps_link = s.maps_url or "-"

        table.add_row(
            str(idx),
            escape(s.name),
            escape(s.city),
            escape(s.address),
            schedule,
            maps_link,
        )

    console.print(table)


@app.command("bcv", help="Calcular la tasa de cambio implícita de Tiendas Daka (USD <-> VEF).", cls=SpanishTyperCommand)
def bcv_cmd(
    monto_usd: Annotated[float | None, typer.Argument(help="Monto opcional en USD a convertir a Bolívares")] = None,
) -> None:
    client = DakaClient()

    with _spinner("Calculando tasa implícita de Daka..."):
        try:
            rate = client.get_implied_bcv_rate()
        except DakaError as e:
            fail(str(e))
            return

    panel_text = f"[bold white]Tasa de cambio implícita de Tiendas Daka:[/] [bold green size=18]1 USD = {rate:,.2f} VEF[/]\n"
    panel_text += "[dim]Calculada en tiempo real mediante muestreo de precios oficiales en Daka.[/]\n"

    if monto_usd is not None:
        total_vef = monto_usd * rate
        formatted_vef = _format_price_vef(total_vef)
        panel_text += f"\n[bold yellow]Conversión:[/] ${_format_price_usd(monto_usd)} USD = [bold yellow]{formatted_vef}[/]"

    console.print(Panel(panel_text, title="[bold yellow]💱 Calculadora de Cambio Daka[/]", border_style="yellow"))


@app.command("categorias", help="Listar las categorías de productos de Tiendas Daka.", cls=SpanishTyperCommand)
def categories_cmd(
    as_tree: Annotated[bool, typer.Option("--arbol/--lista", "-t/-l", help="Mostrar en forma de árbol jerárquico")] = True,
    as_json: Annotated[bool, typer.Option("--json", "-j", help="Mostrar categorías en formato JSON")] = False,
) -> None:
    client = DakaClient()

    with _spinner("Cargando categorías..."):
        try:
            categories = client.get_categories()
        except DakaError as e:
            fail(str(e))
            return

    if as_json:
        console.print_json(data=[_serialize(c) for c in categories])
        return

    if as_tree:
        tree = Tree("[bold cyan]Tiendas Daka - Categorías de Productos[/]")

        def add_subcategories(node: Tree, cat_list: list[Category]):
            for cat in cat_list:
                cat_label = f"[bold white]{escape(cat.name)}[/] [dim cyan]({cat.handle})[/] [dim]ID: {cat.id}[/]"
                sub_node = node.add(cat_label)
                if cat.children:
                    add_subcategories(sub_node, cat.children)

        add_subcategories(tree, categories)
        console.print(tree)
    else:
        table = Table(title="Categorías de Tiendas Daka", box=None, header_style="bold magenta")
        table.add_column("Nombre", style="bold white")
        table.add_column("Handle / Slug", style="dim cyan")
        table.add_column("ID de Categoría", style="dim white")

        def add_rows(cat_list: list[Category], level: int = 0):
            indent = "  " * level
            prefix = "• " if level > 0 else ""
            for cat in cat_list:
                table.add_row(f"{indent}{prefix}{escape(cat.name)}", cat.handle, cat.id)
                if cat.children:
                    add_rows(cat.children, level + 1)

        add_rows(categories)
        console.print(table)


@app.command("abrir", help="Abrir un producto directamente en el navegador web.", cls=SpanishTyperCommand)
def open_cmd(
    producto: Annotated[str, typer.Argument(help="Handle, ID (prod_...) o URL del producto")],
) -> None:
    client = DakaClient()

    with _spinner("Buscando enlace del producto..."):
        try:
            p = client.get_product(producto)
        except DakaError as e:
            fail(str(e))
            return

    console.print(f"[bold green]Abriendo[/] [cyan]{p.title}[/] en el navegador web...")
    webbrowser.open(p.web_url)


if __name__ == "__main__":
    app()
