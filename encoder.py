#!/usr/bin/env python3
"""
Энкодер PHP файлов в формат ERESMINAMA
Использование:
    python3 encoder.py clean.php encoded.php
"""

import base64, os, sys, random, string

def encode_php(source_path, output_path):
    """Кодирует чистый PHP файл в обфусцированный формат"""

    with open(source_path, 'r', encoding='utf-8') as f:
        php_code = f.read()

    # Убрать <?php если есть — он будет в обёртке
    php_code = php_code.lstrip()
    if php_code.startswith('<?php'):
        php_code = php_code[5:].lstrip()

    # Шаг 1: Определить таблицу замены
    standard = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    custom   = 'ERSMINAamniserBbCcDdFfGgHhJjKkLlOoPpQqTtUuVvWwXxYyZz0123456789+/='
    mapping  = str.maketrans(standard, custom[:len(standard)])

    # Шаг 2: base64 кодирование + замена символов
    payload_b64 = base64.b64encode(php_code.encode('utf-8')).decode('ascii')
    payload_encoded = payload_b64.translate(mapping)

    # Шаг 3: Сгенерировать мусорный блок (0x1a8 = 424 байта)
    skip_size = 0x1a8
    junk = ''.join(random.choices(
        string.ascii_letters + string.digits + '+/', k=skip_size
    ))

    # Шаг 4: Параметры
    payload_size = len(payload_encoded)
    seek_offset  = 0x528  # стандартный оффсет для обёртки ниже

    # Шаг 5: Inner eval (промежуточный код)
    inner_php = (
        "$O000O0O00=$GLOBALS['OOO000O00']($OOO0O0O00,'rb');"
        f"$GLOBALS['O0O00OO00']($O000O0O00,0x{seek_offset:x});"
        "$OO00O00O0=$GLOBALS['OOO0000O0']($GLOBALS['OOO00000O']("
        f"$GLOBALS['O0O00OO00']($O000O0O00,0x{skip_size:x}),"
        f"'{custom}','{standard}'));eval($OO00O00O0);"
    )
    inner_b64 = base64.b64encode(inner_php.encode('utf-8')).decode('ascii')

    # Шаг 6: Собрать обёртку
    wrapper = (
        "<?php /* ERESMINAMA */"
        "$OOO000000=urldecode('%66%67%36%73%62%65%68%70%72%61%34%63%6f%5f%74%6e%64');"
        "$GLOBALS['OOO0000O0']=$OOO000000[4].$OOO000000[9].$OOO000000[3].$OOO000000[5]"
        ".$OOO000000[2].$OOO000000[10].$OOO000000[13].$OOO000000[16];"
        "$GLOBALS['OOO0000O0'].=$GLOBALS['OOO0000O0'][3].$OOO000000[11]"
        ".$OOO000000[12].$GLOBALS['OOO0000O0'][7].$OOO000000[5];"
        "$GLOBALS['OOO000O00']=$OOO000000[0].$OOO000000[12].$OOO000000[7]"
        ".$OOO000000[5].$OOO000000[15];"
        "$GLOBALS['O0O000O00']=$OOO000000[0].$OOO000000[1].$OOO000000[5]"
        ".$OOO000000[14];"
        "$GLOBALS['O0O000O00']=$O0O000O00.$OOO000000[3];"
        "$GLOBALS['O0O00OO00']=$OOO000000[0].$OOO000000[8].$OOO000000[5]"
        ".$OOO000000[9].$OOO000000[16];"
        "$GLOBALS['OOO00000O']=$OOO000000[3].$OOO000000[14].$OOO000000[8]"
        ".$OOO000000[14].$OOO000000[8];"
        "$OOO0O0O00=__FILE__;"
        f"$OO00O0000=0x{payload_size:x};"
        f"eval($GLOBALS['OOO0000O0']('{inner_b64}'));"
        "return;?>"
    )

    # Шаг 7: Добавить padding чтобы seek_offset совпадал
    current_len = len(wrapper.encode('utf-8'))
    if current_len < seek_offset:
        wrapper_padded = wrapper[:-10] + ' ' * (seek_offset - current_len) + wrapper[-10:]
    else:
        wrapper_padded = wrapper

    # Шаг 8: Записать: обёртка + мусор + payload
    with open(output_path, 'wb') as f:
        f.write(wrapper_padded.encode('utf-8'))
        # Убедиться что мы на нужном оффсете
        current = f.tell()
        if current < seek_offset:
            f.write(b' ' * (seek_offset - current))
        f.write(junk.encode('ascii'))
        f.write(payload_encoded.encode('ascii'))

    print(f"Закодировано: {source_path} -> {output_path}")
    print(f"  Размер payload: {payload_size} байт")


def main():
    if len(sys.argv) < 3:
        print("Использование: python3 encoder.py <исходник.php> <выход.php>")
        sys.exit(1)
    encode_php(sys.argv[1], sys.argv[2])

if __name__ == '__main__':
    main()
