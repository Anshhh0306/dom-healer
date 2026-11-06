from __future__ import annotations

import pytest

from dom_healer.dom import parse_html

OLD_SHOP = """<!doctype html>
<html lang="en"><head><title>Trail Shop</title><style>.btn{color:red}</style></head>
<body>
<header class="site-header">
  <nav class="main-nav" aria-label="Main">
    <a href="/" class="nav-link">Home</a>
    <a href="/deals" class="nav-link">Deals</a>
    <a href="/cart" class="nav-link" id="cart-link">Cart (2)</a>
  </nav>
</header>
<main id="content">
  <h1>Trail shoes</h1>
  <div class="product-grid">
    <div class="product-card" data-sku="TR-100">
      <h3 class="product-title">Trail Runner 2</h3><span class="price">$120</span>
      <button class="btn btn-primary add-to-cart" data-testid="add-TR-100">Add to cart</button>
    </div>
    <div class="product-card" data-sku="SK-200">
      <h3 class="product-title">Summit Kicks</h3><span class="price">$95</span>
      <button class="btn btn-primary add-to-cart" data-testid="add-SK-200">Add to cart</button>
    </div>
    <div class="product-card" data-sku="MH-300">
      <h3 class="product-title">Mesa Hiker</h3><span class="price">$140</span>
      <button class="btn btn-primary add-to-cart" data-testid="add-MH-300">Add to cart</button>
    </div>
  </div>
  <form id="newsletter" name="newsletter" action="/subscribe">
    <label for="nl-email">Email</label>
    <input id="nl-email" name="email" type="email" placeholder="you@example.com">
    <label><input type="checkbox" name="weekly" id="weekly"> Weekly digest</label>
    <button type="submit" class="btn subscribe">Subscribe</button>
  </form>
  <table class="orders">
    <thead><tr><th>Order</th><th>Status</th><th>Total</th><th>Actions</th></tr></thead>
    <tbody>
      <tr><td>#1001</td><td class="status">Shipped</td><td>$120</td><td><a href="/o/1001" class="view">View</a></td></tr>
      <tr><td>#1002</td><td class="status">Pending</td><td>$95</td><td><a href="/o/1002" class="view">View</a></td></tr>
    </tbody>
  </table>
</main>
<footer class="site-footer"><p>&copy; Trail Shop</p></footer>
</body></html>
"""

NEW_SHOP = """<!doctype html>
<html lang="en"><head><title>Trail Shop</title></head>
<body>
<div class="sc-hKwDye kQwYzP">
<header class="css-1x9f2ab">
  <nav class="css-k2l9xq" aria-label="Main">
    <div class="_a3f9c"><a href="/" class="css-p0q1r2">Home</a></div>
    <div class="_a3f9c"><a href="/cart?ref=nav" class="css-p0q1r2" id=":r1f:">Bag (2)</a></div>
    <div class="_a3f9c"><a href="/deals" class="css-p0q1r2">Deals</a></div>
  </nav>
</header>
<main id="content">
  <h1>Trail shoes</h1>
  <div class="flex flex-wrap gap-4">
    <div class="sc-bdfBwQ" data-sku="MH-300">
      <div class="sc-gsTCUz"><h3 class="css-t1t2l3">Mesa Hiker</h3></div><span class="css-pr1c3x">$140</span>
      <div class="sc-wrap1"><button class="inline-flex items-center px-3 py-2 bg-indigo-600">Add to bag</button></div>
    </div>
    <product-card data-sku="SK-200">
      <template shadowrootmode="open">
        <div class="sc-gsTCUz"><h3 class="css-t1t2l3">Summit Kicks</h3></div><span class="css-pr1c3x">$95</span>
        <div class="sc-wrap1"><button class="inline-flex items-center px-3 py-2 bg-indigo-600">Add to bag</button></div>
      </template>
    </product-card>
    <div class="sc-bdfBwQ" data-sku="TR-100">
      <div class="sc-gsTCUz"><h3 class="css-t1t2l3">Trail Runner 2</h3></div><span class="css-pr1c3x">$120</span>
      <div class="sc-wrap1"><button class="inline-flex items-center px-3 py-2 bg-indigo-600">Add to bag</button></div>
    </div>
    <button class="inline-flex items-center px-3 py-2 bg-indigo-600" hidden>Add to bag</button>
  </div>
  <form id="f-7f3a" name="newsletter" action="/subscribe">
    <div class="css-field"><label><input type="checkbox" name="weekly" id=":r2:"> Weekly digest</label></div>
    <div class="css-field"><label for=":r3:">Email address</label>
      <div class="css-wrap"><input id=":r3:" name="email" type="email" placeholder="you@example.com"></div></div>
    <button type="submit" class="css-btn9z">Subscribe</button>
  </form>
  <div role="table" class="css-orders1">
    <div role="row"><span role="columnheader">Order</span><span role="columnheader">Placed</span>
      <span role="columnheader">Status</span><span role="columnheader">Total</span><span role="columnheader">Actions</span></div>
    <div role="row"><span role="cell">#1002</span><span role="cell">May 2</span><span role="cell">Pending</span>
      <span role="cell">$95</span><span role="cell"><a href="/o/1002" class="css-lnk">View</a></span></div>
    <div role="row"><span role="cell">#1001</span><span role="cell">May 1</span><span role="cell">Shipped</span>
      <span role="cell">$120</span><span role="cell"><a href="/o/1001" class="css-lnk">View</a></span></div>
  </div>
</main>
<footer class="css-f00t3r"><p>&copy; Trail Shop</p></footer>
</div>
</body></html>
"""


@pytest.fixture
def old_html() -> str:
    return OLD_SHOP


@pytest.fixture
def new_html() -> str:
    return NEW_SHOP


@pytest.fixture
def old_doc():
    return parse_html(OLD_SHOP)


@pytest.fixture
def new_doc():
    return parse_html(NEW_SHOP)
