<?php
declare(strict_types=1);

const ROOT = __DIR__ . '/..';
const NOV_DIR = ROOT . '/content/novelly';
const DATA_DIR = ROOT . '/data';
const CACHE_DIR = ROOT . '/cache';
const ASSET_VER = '7';

function cfg(?string $key = null)
{
    static $c = null;
    if ($c === null) {
        $c = require ROOT . '/config.php';
        $f = DATA_DIR . '/settings.json';
        if (is_file($f)) {
            $s = json_decode((string)file_get_contents($f), true);
            if (is_array($s)) foreach ($s as $k => $v) if ($v !== '' && $v !== null) $c[$k] = $v;
        }
    }
    return $key === null ? $c : ($c[$key] ?? '');
}

function h(string $s): string { return htmlspecialchars($s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }

function site_url(): string
{
    $u = rtrim((string)cfg('site_url'), '/');
    if ($u !== '') return $u;
    $https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') || ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https';
    return ($https ? 'https' : 'http') . '://' . ($_SERVER['HTTP_HOST'] ?? 'localhost');
}

function plural(int $n, string $one, string $few, string $many): string
{
    $n10 = $n % 10; $n100 = $n % 100;
    if ($n10 === 1 && $n100 !== 11) return $one;
    if ($n10 >= 2 && $n10 <= 4 && ($n100 < 10 || $n100 >= 20)) return $few;
    return $many;
}

function minutes_label(int $m): string { return $m . ' ' . plural($m, 'минута', 'минуты', 'минут'); }

// ---------- транслит для адресов ----------
function slugify(string $s): string
{
    $map = ['а'=>'a','б'=>'b','в'=>'v','г'=>'g','д'=>'d','е'=>'e','ё'=>'e','ж'=>'zh','з'=>'z','и'=>'i','й'=>'y','к'=>'k','л'=>'l','м'=>'m','н'=>'n','о'=>'o','п'=>'p','р'=>'r','с'=>'s','т'=>'t','у'=>'u','ф'=>'f','х'=>'h','ц'=>'ts','ч'=>'ch','ш'=>'sh','щ'=>'sch','ъ'=>'','ы'=>'y','ь'=>'','э'=>'e','ю'=>'yu','я'=>'ya'];
    $s = mb_strtolower($s, 'UTF-8');
    $s = strtr($s, $map);
    $s = preg_replace('~[^a-z0-9]+~', '-', $s);
    $s = trim((string)$s, '-');
    if (strlen($s) > 60) $s = rtrim(substr($s, 0, 60), '-');
    return $s !== '' ? $s : 'novella';
}

// ---------- типографика ----------
// Курсив и жирный из docx приходят метками U+E000..U+E003, чтобы пережить экранирование
const EM_O = "\u{E000}", EM_C = "\u{E001}", ST_O = "\u{E002}", ST_C = "\u{E003}";
const NBSP = "\u{00A0}";

function typo(string $t): string
{
    $t = str_replace(["\r", "\t", "\u{200B}", "\u{FEFF}"], ['', ' ', '', ''], $t);
    $t = preg_replace('~[ \x{00A0}]{2,}~u', ' ', $t);
    $t = trim($t, " \u{00A0}\n");
    // многоточие
    $t = preg_replace('~\.{3,}~u', '…', $t);
    // прямая речь в начале абзаца: «- Текст» / «– Текст»
    $t = preg_replace('~^(' . EM_O . '|' . ST_O . ')?[\-–—−]\s*~u', '$1—' . NBSP, $t);
    // тире между словами: « - », « – », « — », «--»
    $t = preg_replace('~\s+(?:--|[\-–—−])\s+~u', NBSP . '— ', $t);
    $t = preg_replace('~([,.!?…»])(?:--|[\-–—−])\s~u', '$1' . NBSP . '— ', $t);
    // кавычки: все варианты в прямые, потом ёлочки и лапки по вложенности
    $t = str_replace(['“', '”', '„', '«', '»', '″'], '"', $t);
    $t = quotes($t);
    // апостроф
    $t = preg_replace("~(\p{L})'(\p{L})~u", '$1’$2', $t);
    // неразрывный пробел после коротких слов и перед частицами
    // предлоги, союзы и все слова из 1-2 букв, кроме частиц (же, ли, бы), которые сами липнут к предыдущему слову
    $short = '(?!(?:же|ли|бы|ль)[\s' . NBSP . '])(?:[а-яёА-ЯЁa-zA-Z]{1,2}|без|для|над|под|при|про|изо|обо|ото|из-за|из-под|сквозь|через|между|перед)';
    for ($i = 0; $i < 2; $i++) {
        $t = preg_replace('~(?<=^|[\s(«„' . EM_O . ST_O . NBSP . '])(' . $short . ') (?=\S)~u', '$1' . NBSP, $t);
    }
    $t = preg_replace('~ (ли|же|бы|ль|ж|б)(?=[\s.,!?…:;»“' . EM_C . ST_C . ']|$)~u', NBSP . '$1', $t);
    // число и единица: «5 %», «№ 5», «10 км»
    $t = preg_replace('~(\d) (%|км|м|см|кг|г|руб|₽|лет|года|год)\b~u', '$1' . NBSP . '$2', $t);
    $t = preg_replace('~№\s*(\d)~u', '№' . NBSP . '$1', $t);
    return $t;
}

function quotes(string $t): string
{
    $out = '';
    $depth = 0;
    $chars = preg_split('//u', $t, -1, PREG_SPLIT_NO_EMPTY);
    $n = count($chars);
    for ($i = 0; $i < $n; $i++) {
        $c = $chars[$i];
        if ($c !== '"') { $out .= $c; continue; }
        $prev = $i > 0 ? $chars[$i - 1] : '';
        $next = $i + 1 < $n ? $chars[$i + 1] : '';
        $opening = ($prev === '' || preg_match('~[\s(\[{—–\-' . NBSP . EM_O . ST_O . '"]~u', $prev)) && $next !== '' && !preg_match('~\s~u', $next);
        if ($opening) {
            $out .= $depth === 0 ? '«' : '„';
            $depth++;
        } else {
            if ($depth > 0) $depth--;
            $out .= $depth === 0 ? '»' : '“';
        }
    }
    return $out;
}

function para_html(string $t): string
{
    $t = h($t);
    $t = str_replace(NBSP, '&nbsp;', $t);
    $t = str_replace([EM_O, EM_C, ST_O, ST_C], ['<em>', '</em>', '<strong>', '</strong>'], $t);
    // пустые и соседние теги курсива
    $t = str_replace(['<em></em>', '</em><em>', '<strong></strong>', '</strong><strong>'], '', $t);
    return $t;
}

function plain(string $t): string
{
    return str_replace([EM_O, EM_C, ST_O, ST_C], '', $t);
}

function is_separator(string $p): bool
{
    return (bool)preg_match('/^[\s*#~•·—–\-_=]+$/u', plain($p)) && mb_strlen(trim(plain($p))) >= 1 && mb_strlen(trim(plain($p))) <= 12;
}

// ---------- чтение файлов ----------
function read_docx(string $path): array
{
    $zip = new ZipArchive();
    if ($zip->open($path) !== true) return [];
    $xml = $zip->getFromName('word/document.xml');
    $zip->close();
    if (!$xml) return [];
    $dom = new DOMDocument();
    $dom->loadXML($xml, LIBXML_NONET | LIBXML_COMPACT);
    $xp = new DOMXPath($dom);
    $xp->registerNamespace('w', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main');
    $paras = [];
    foreach ($xp->query('//w:body//w:p') as $p) {
        $style = '';
        $ps = $xp->query('./w:pPr/w:pStyle/@w:val', $p);
        if ($ps->length) $style = strtolower($ps->item(0)->nodeValue);
        $lines = [''];
        foreach ($xp->query('.//w:r', $p) as $r) {
            $it = $xp->query('./w:rPr/w:i[not(@w:val="0" or @w:val="false")]', $r)->length > 0;
            $bd = $xp->query('./w:rPr/w:b[not(@w:val="0" or @w:val="false")]', $r)->length > 0;
            $buf = '';
            foreach ($r->childNodes as $ch) {
                if (!($ch instanceof DOMElement)) continue;
                $ln = $ch->localName;
                if ($ln === 't') $buf .= $ch->textContent;
                elseif ($ln === 'tab') $buf .= ' ';
                elseif ($ln === 'br' || $ln === 'cr') {
                    if ($ch->getAttribute('w:type') === 'page') continue;
                    $lines[count($lines) - 1] .= wrap_fmt($buf, $it, $bd);
                    $buf = '';
                    $lines[] = '';
                } elseif ($ln === 'noBreakHyphen') $buf .= '-';
            }
            $lines[count($lines) - 1] .= wrap_fmt($buf, $it, $bd);
        }
        foreach ($lines as $k => $l) {
            $paras[] = ['text' => $l, 'title' => $k === 0 && (str_starts_with($style, 'title') || str_starts_with($style, 'heading') || $style === '1' || str_contains($style, 'заголов'))];
        }
    }
    return $paras;
}

function wrap_fmt(string $s, bool $it, bool $bd): string
{
    if ($s === '') return '';
    if (trim($s) === '') return $s;
    // пробелы оставляем снаружи меток
    preg_match('~^(\s*)(.*?)(\s*)$~us', $s, $m);
    $core = $m[2];
    if ($it) $core = EM_O . $core . EM_C;
    if ($bd) $core = ST_O . $core . ST_C;
    return $m[1] . $core . $m[3];
}

function read_txt(string $path): array
{
    $raw = (string)file_get_contents($path);
    if (!mb_check_encoding($raw, 'UTF-8')) $raw = mb_convert_encoding($raw, 'UTF-8', 'Windows-1251');
    $raw = preg_replace('~^\x{FEFF}~u', '', $raw);
    $raw = str_replace("\r\n", "\n", $raw);
    // абзацы: пустая строка или просто перевод строки
    $paras = [];
    foreach (explode("\n", $raw) as $line) {
        // _курсив_ и *курсив* в текстовых файлах
        $line = preg_replace('~(?<![\p{L}\d*_])_(\S(?:[^_]*\S)?)_(?![\p{L}\d_])~u', EM_O . '$1' . EM_C, $line);
        $line = preg_replace('~(?<![\p{L}\d*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\p{L}\d*])~u', EM_O . '$1' . EM_C, $line);
        $paras[] = ['text' => $line, 'title' => false];
    }
    return $paras;
}

// Разбор файла новеллы в структуру
function parse_novella(string $path): ?array
{
    $ext = strtolower(pathinfo($path, PATHINFO_EXTENSION));
    $raw = $ext === 'docx' ? read_docx($path) : read_txt($path);
    $meta = [];
    $metaFile = preg_replace('~\.(docx|txt|md)$~i', '.json', $path);
    if (is_file($metaFile)) $meta = json_decode((string)file_get_contents($metaFile), true) ?: [];

    $paras = [];
    $title = '';
    foreach ($raw as $p) {
        $t = trim(str_replace("\u{00A0}", ' ', $p['text']));
        if ($t === '' || trim(plain($t)) === '') continue;
        // служебные строки в txt: «Название: ...»
        if (!$paras && preg_match('~^(Название|Заголовок)\s*:\s*(.+)$~ui', plain($t), $m)) { $title = trim($m[2]); continue; }
        if ($title === '' && !$paras && ($p['title'] || (mb_strlen(plain($t)) <= 80 && !preg_match('~[.!?…:;,]$~u', plain($t))))) {
            $title = trim(plain($t));
            continue;
        }
        $paras[] = $t;
    }
    if (!empty($meta['title'])) $title = $meta['title'];
    if ($title === '') $title = 'Без названия';
    if (!$paras) return null;

    $blocks = [];
    $words = 0;
    foreach ($paras as $p) {
        if (is_separator($p)) {
            if ($blocks && end($blocks)['type'] !== 'sep') $blocks[] = ['type' => 'sep'];
            continue;
        }
        $tp = typo($p);
        $words += count(preg_split('~[\s\x{00A0}]+~u', trim(plain($tp)), -1, PREG_SPLIT_NO_EMPTY));
        $blocks[] = ['type' => 'p', 'html' => para_html($tp), 'dialog' => str_starts_with(plain($tp), '—')];
    }
    while ($blocks && end($blocks)['type'] === 'sep') array_pop($blocks);

    // первая фраза: первое предложение первого обычного абзаца
    $first = '';
    foreach ($blocks as $b) if ($b['type'] === 'p') {
        $txt = html_entity_decode(strip_tags($b['html']), ENT_QUOTES | ENT_HTML5, 'UTF-8');
        $first = first_sentence($txt);
        break;
    }
    if (!empty($meta['first'])) $first = typo($meta['first']);

    $wpm = max(100, (int)cfg('wpm'));
    return [
        'title' => typo_title($title),
        'blocks' => $blocks,
        'words' => $words,
        'minutes' => max(1, (int)round($words / $wpm)),
        'first' => $first,
        'hidden' => !empty($meta['hidden']),
    ];
}

function typo_title(string $t): string
{
    return plain(typo($t));
}

function first_sentence(string $t): string
{
    $t = trim($t);
    if (preg_match('~^(.{20,}?[.!?…])(?:\s|$)~us', $t, $m)) $s = $m[1];
    else $s = $t;
    if (mb_strlen($s) > 170) {
        $s = mb_substr($s, 0, 170);
        $s = preg_replace('~[\s\x{00A0}]+\S*$~u', '', $s) . '…';
    }
    // «Свет он зажигал…» без висящих кавычек
    if (substr_count($s, '«') > substr_count($s, '»')) $s .= '»';
    return $s;
}

// Список новелл с кешем
function novellas(bool $withHidden = false): array
{
    $files = glob(NOV_DIR . '/*.{docx,txt,md}', GLOB_BRACE) ?: [];
    $files = array_values(array_filter($files, fn($f) => basename($f)[0] !== '_' && basename($f)[0] !== '~'));
    natcasesort($files);
    $files = array_values($files);
    $sig = md5(implode('|', array_map(fn($f) => $f . filemtime($f) . (is_file(preg_replace('~\.\w+$~', '.json', $f)) ? filemtime(preg_replace('~\.\w+$~', '.json', $f)) : 0), $files)) . filemtime(ROOT . '/inc/lib.php') . ((string)cfg('wpm')));
    $cacheFile = CACHE_DIR . '/novellas-' . $sig . '.json';
    $list = null;
    if (is_file($cacheFile)) $list = json_decode((string)file_get_contents($cacheFile), true);
    if (!is_array($list)) {
        $list = [];
        $seen = [];
        foreach ($files as $f) {
            $n = parse_novella($f);
            if (!$n) continue;
            $base = pathinfo($f, PATHINFO_FILENAME);
            $slug = slugify(preg_replace('~^\d+[\s._-]*~u', '', $base) ?: $n['title']);
            if (isset($seen[$slug])) $slug .= '-' . (count($seen) + 1);
            $seen[$slug] = 1;
            $n['slug'] = $slug;
            $n['file'] = basename($f);
            $n['mtime'] = filemtime($f);
            $list[] = $n;
        }
        foreach (glob(CACHE_DIR . '/novellas-*.json') ?: [] as $old) @unlink($old);
        @file_put_contents($cacheFile, json_encode($list, JSON_UNESCAPED_UNICODE));
    }
    if (!$withHidden) $list = array_values(array_filter($list, fn($n) => empty($n['hidden'])));
    return $list;
}

function page_text(string $name): array
{
    // content/ob-avtore.txt и подобные: абзацы через перевод строки
    $f = ROOT . '/content/' . $name . '.txt';
    if (!is_file($f)) return [];
    $out = [];
    foreach (read_txt($f) as $p) {
        $t = trim($p['text']);
        if ($t === '') continue;
        $out[] = is_separator($t) ? ['type' => 'sep'] : ['type' => 'p', 'html' => para_html(typo($t))];
    }
    return $out;
}

function asset(string $p): string { return '/assets/' . $p . '?v=' . ASSET_VER; }
