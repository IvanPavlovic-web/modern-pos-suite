import concurrent.futures
import multiprocessing
import threading

MAX_CORES = multiprocessing.cpu_count()


def parallel_import_products(products_data, batch_size=100):
    """
    CPU-bound: paralelna validacija/normalizacija velikog broja proizvoda.
    Koristi ProcessPoolExecutor sa max_workers = broj jezgara.
    """
    batches = [products_data[i:i + batch_size] for i in range(0, len(products_data), batch_size)]

    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_CORES) as executor:
        results = list(executor.map(_process_batch, batches))

    flattened = [item for sub in results for item in sub]
    return flattened


def _process_batch(batch):
    processed = []
    for p in batch:
        processed.append({
            'name': (p.get('name') or '').strip(),
            'barcode': (p.get('barcode') or '').strip() or None,
            'price': float(p.get('price') or 0),
            'stock': int(p.get('stock') or 0),
            'tax_rate': float(p.get('tax_rate') or 20),
            'discount_percent': float(p.get('discount_percent') or 0),
        })
    return processed


def parallel_generate_receipts(sales, generate_fn):
    """
    I/O-bound: generisanje više PDF računa paralelno preko thread pool-a.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CORES) as executor:
        futures = {executor.submit(generate_fn, sale): sale for sale in sales}
        results = {}
        for fut in concurrent.futures.as_completed(futures):
            sale = futures[fut]
            try:
                results[sale.id] = fut.result()
            except Exception as e:
                results[sale.id] = {'error': str(e)}
    return results


def run_in_thread(target, *args, **kwargs):
    """
    Pokreni funkciju u pozadinskom thread-u (da ne blokira request).
    """
    t = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t