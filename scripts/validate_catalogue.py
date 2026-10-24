"""Reject broken or substantially depleted refreshes before publishing either file."""
import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(directory, name):
    return json.loads((directory / name).read_text(encoding='utf-8'))


def validate_product(product):
    asin = product.get('asin', '')
    require(re.fullmatch(r'[A-Z0-9]{10}', asin), 'Invalid ASIN')
    require(isinstance(product.get('title'), str) and product['title'].strip(), f'{asin}: missing title')
    image = urlparse(product.get('imageUrl', ''))
    require(image.scheme == 'https' and bool(image.hostname) and (
        image.hostname.endswith('.media-amazon.com') or
        image.hostname.endswith('.ssl-images-amazon.com') or
        image.hostname.endswith('.amazon.com')
    ), f'{asin}: invalid Amazon image URL')
    for key in ('productUrl', 'amazonUrl'):
        url = urlparse(product.get(key, ''))
        require(url.scheme == 'https' and url.hostname in ('www.amazon.in', 'amazon.in')
                and url.path == f'/dp/{asin}', f'{asin}: invalid {key}')
    require(parse_qs(urlparse(product['amazonUrl']).query).get('tag') == ['catchdeal07-21'],
            f'{asin}: missing affiliate tag')


def validate(directory, baseline=None):
    catalogue = read(directory, 'products.json')
    index = read(directory, 'search_index.json')
    for data in (catalogue, index):
        timestamp = datetime.fromisoformat(data['generatedAt'])
        require(timestamp.tzinfo is not None, 'Generation date must include a timezone')
        if baseline is not None:
            age = (datetime.now(timezone.utc) - timestamp).total_seconds()
            require(-300 <= age <= 86400, 'Fresh data must have been collected within the last day')
    products, categories, terms = catalogue['products'], catalogue['categories'], index['terms']
    require(isinstance(products, list) and 30 <= len(products) <= 300, 'Need 30–300 products')
    require(isinstance(categories, list) and len(categories) >= 4, 'Need at least four categories')
    require(isinstance(terms, dict) and len(terms) >= 100, 'Need at least 100 populated search terms')
    if baseline is not None:
        require(bool(terms.get('gaming chair')), 'Gaming chair search must have products')
    require(catalogue['productCount'] == len(products), 'Catalogue product count mismatch')
    ids = {category['id'] for category in categories}
    require(len(ids) == len(categories), 'Duplicate categories')
    asins = set()
    for product in products:
        validate_product(product)
        require(product['asin'] not in asins, 'Duplicate catalogue ASIN')
        asins.add(product['asin'])
        require(product.get('id') == product['asin'], 'Product ID must match ASIN')
        require(product.get('category') in ids and product.get('categoryLabel'), 'Invalid category')
    for category in ids:
        require(sum(p['category'] == category for p in products) >= 2, 'Category needs two products')
    references = 0
    for term, entries in terms.items():
        require(isinstance(term, str) and term.strip(), 'Invalid search term')
        require(isinstance(entries, list) and 1 <= len(entries) <= 5, 'Need 1–5 results per search')
        require(len({p['asin'] for p in entries}) == len(entries), 'Duplicate ASIN within search term')
        for product in entries:
            validate_product(product)
        references += len(entries)
    require(index['termCount'] == len(terms) and index['productCount'] == references,
            'Search metadata does not match its entries')
    if baseline is not None:
        old_catalogue = read(baseline, 'products.json')
        old_index = read(baseline, 'search_index.json')
        require(len(products) >= math.ceil(len(old_catalogue['products']) * .8),
                'Refresh lost more than 20% of catalogue products')
        require(len(terms) >= math.ceil(len(old_index['terms']) * .8),
                'Refresh lost more than 20% of search coverage')
    print(f'Validated {len(products)} products, {len(categories)} categories, '
          f'{len(terms)} search terms and {references} references')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    validate(args.directory, args.baseline)
