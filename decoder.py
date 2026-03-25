#!/usr/bin/env python3
"""
Декодер обфусцированных PHP файлов (ERESMINAMA / ionic php compiler)
Использование:
    python3 decoder.py encoded_file.php              — вывод в консоль
    python3 decoder.py encoded_file.php decoded.php   — сохранить в файл
    python3 decoder.py /path/to/folder/               — декодировать все файлы в папке
"""

import re, base64, os, sys, glob

def decode_php(filepath):
    """Декодирует один обфусцированный PHP файл"""
    with open(filepath, 'rb') as f:
        content = f.read()

    # Шаг 1: Найти inner eval — base64 строку внутри eval()
    match = re.search(rb"OOO0000O0'\]\('([A-Za-z0-9+/=]+)'\)", content)
    if not match:
        return None, "Файл не обфусцирован (нет inner eval)"

    # Шаг 2: Декодировать inner eval — получить промежуточный PHP код
    inner = base64.b64decode(match.group(1)).decode('utf-8')

    # Шаг 3: Извлечь таблицу замены символов (strtr mapping)
    strtr_match = re.search(r"'([^']{30,})','([A-Za-z0-9+/=]{30,})'", inner)
    if not strtr_match:
        return None, "Не найден strtr маппинг"
    from_chars = strtr_match.group(1)  # например: ERSMINAamniser...
    to_chars   = strtr_match.group(2)  # стандартный base64 алфавит

    # Создать таблицу замены (использовать минимальную длину обеих строк)
    mapping_len = min(len(from_chars), len(to_chars))
    if mapping_len == 0:
        return None, "Strtr маппинг пуст"
    mapping = str.maketrans(from_chars[:mapping_len], to_chars[:mapping_len])

    # Шаг 4: Извлечь оффсеты (seek и read)
    hex_vals = re.findall(r',0x([0-9a-fA-F]+)\)', inner)
    seek_offset = int(hex_vals[0], 16)  # начало данных после return;?>
    skip_bytes  = int(hex_vals[1], 16)  # размер мусорного блока

    # Шаг 5: Извлечь размер payload
    size_m = re.search(rb'\$OO00O0000=0x([0-9a-fA-F]+)', content)
    if not size_m:
        return None, "Не найден размер payload"
    payload_size = int(size_m.group(1), 16)

    # Шаг 6: Вырезать payload из файла
    payload_start = seek_offset + skip_bytes
    payload_raw = content[payload_start : payload_start + payload_size]

    # Шаг 7: strtr + base64_decode = чистый PHP код
    payload_mapped = payload_raw.decode('ascii', errors='ignore').translate(mapping)

    # Добавить padding для base64
    pad = (4 - len(payload_mapped) % 4) % 4
    php_bytes = base64.b64decode(payload_mapped + '=' * pad)

    try:
        return php_bytes.decode('utf-8'), None
    except UnicodeDecodeError:
        return php_bytes.decode('latin-1'), None


def main():
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python3 decoder.py <файл.php>")
        print("  python3 decoder.py <файл.php> <выход.php>")
        print("  python3 decoder.py <папка/>")
        sys.exit(1)

    target = sys.argv[1]

    # Если папка — декодировать все .php файлы в ней
    if os.path.isdir(target):
        files = glob.glob(os.path.join(target, '**/*.php'), recursive=True)
        ok = fail = skip = 0
        for f in sorted(files):
            code, err = decode_php(f)
            rel = os.path.relpath(f, target)
            if err:
                if "не обфусцирован" in err.lower():
                    skip += 1
                else:
                    print(f"  ОШИБКА: {rel} — {err}")
                    fail += 1
            else:
                out = code if code.lstrip().startswith('<?') else '<?php\n' + code
                with open(f, 'w', encoding='utf-8') as fw:
                    fw.write(out)
                print(f"  OK: {rel}")
                ok += 1
        print(f"\nИтого: {ok} декодировано, {skip} пропущено, {fail} ошибок")

    # Если файл
    elif os.path.isfile(target):
        code, err = decode_php(target)
        if err:
            print(f"Ошибка: {err}")
            sys.exit(1)
        out = code if code.lstrip().startswith('<?') else '<?php\n' + code
        if len(sys.argv) >= 3:
            with open(sys.argv[2], 'w', encoding='utf-8') as f:
                f.write(out)
            print(f"Сохранено в {sys.argv[2]}")
        else:
            print(out)
    else:
        print(f"Файл или папка не найдена: {target}")
        sys.exit(1)

if __name__ == '__main__':
    main()
