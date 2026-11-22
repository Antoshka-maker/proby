<?php
declare(strict_types=1);
// Картинка превью для Telegram 1200×630: название, первая фраза, время чтения.
// Если рядом с файлом новеллы лежит картинка с тем же именем (.jpg/.png), берётся она.

function og_serve(string $slug): void
{
    $site = (string)cfg('site_name');
    $title = $site; $sub = (string)cfg('lead'); $meta = ''; $ver = '0'; $custom = null;
    if ($slug !== '_site') {
        $found = null;
        foreach (novellas(true) as $n) if ($n['slug'] === $slug) { $found = $n; break; }
        if (!$found) { http_response_code(404); exit; }
        $title = $found['title'];
        $sub = $found['first'];
        $meta = minutes_label($found['minutes']) . ' чтения';
        $ver = (string)$found['mtime'];
        $base = NOV_DIR . '/' . pathinfo($found['file'], PATHINFO_FILENAME);
        foreach (['jpg', 'jpeg', 'png', 'webp'] as $e) if (is_file("$base.$e")) { $custom = "$base.$e"; break; }
    }
    if ($custom) {
        header('Content-Type: ' . (str_ends_with($custom, 'png') ? 'image/png' : (str_ends_with($custom, 'webp') ? 'image/webp' : 'image/jpeg')));
        header('Cache-Control: public, max-age=86400');
        readfile($custom);
        return;
    }
    $key = md5($slug . $ver . $title . $sub . $site . filemtime(__FILE__));
    $file = CACHE_DIR . "/og-$key.png";
    if (!is_file($file)) {
        foreach (glob(CACHE_DIR . "/og-*.png") ?: [] as $f) if (filemtime($f) < time() - 86400 * 30) @unlink($f);
        og_draw($file, $site, $title, $sub, $meta);
    }
    header('Content-Type: image/png');
    header('Cache-Control: public, max-age=86400');
    readfile($file);
}

function og_wrap(string $text, string $font, float $size, int $maxW, int $maxLines): array
{
    $words = preg_split('~[ ]+~u', str_replace("\u{00A0}", ' ', $text));
    $lines = []; $cur = '';
    foreach ($words as $w) {
        $try = $cur === '' ? $w : "$cur $w";
        $bb = imagettfbbox($size, 0, $font, $try);
        if ($bb[2] - $bb[0] > $maxW && $cur !== '') { $lines[] = $cur; $cur = $w; }
        else $cur = $try;
    }
    if ($cur !== '') $lines[] = $cur;
    if (count($lines) > $maxLines) {
        $lines = array_slice($lines, 0, $maxLines);
        $lines[$maxLines - 1] = rtrim($lines[$maxLines - 1], ' ,.;:—') . '…';
    }
    return $lines;
}

function og_draw(string $file, string $site, string $title, string $sub, string $meta): void
{
    $W = 1200; $H = 630;
    $im = imagecreatetruecolor($W, $H);
    $bg = imagecolorallocate($im, 0x1d, 0x1c, 0x22);
    $fg = imagecolorallocate($im, 0xf2, 0xed, 0xe3);
    $mut = imagecolorallocate($im, 0xa3, 0x9d, 0x92);
    $acc = imagecolorallocate($im, 0xd9, 0x8a, 0x6f);
    imagefilledrectangle($im, 0, 0, $W, $H, $bg);
    imagefilledrectangle($im, 0, 0, 14, $H, $acc);
    $reg = ROOT . '/inc/fonts/PTSerif-Regular.ttf';
    $bold = ROOT . '/inc/fonts/PTSerif-Bold.ttf';
    $ital = ROOT . '/inc/fonts/PTSerif-Italic.ttf';
    if (!is_file($ital)) $ital = $reg;
    $x = 90;
    imagettftext($im, 26, 0, $x, 104, $mut, $reg, mb_strtoupper($site) . ($meta !== '' ? '   ·   ' . $meta : ''));
    $size = mb_strlen($title) > 40 ? 58 : 72;
    $tl = og_wrap($title, $bold, $size, $W - $x * 2, 2);
    $y = 210 + ($size - 58);
    foreach ($tl as $l) { imagettftext($im, $size, 0, $x, $y, $fg, $bold, $l); $y += (int)($size * 1.25); }
    $y += 20;
    $sub = trim($sub, '«» ');
    if ($sub !== '') {
        $sl = og_wrap('«' . $sub . '»', $ital, 31, $W - $x * 2, 4 - max(0, count($tl) - 1));
        foreach ($sl as $l) { imagettftext($im, 31, 0, $x, $y, $mut, $ital, $l); $y += 48; }
    }
    imagepng($im, $file, 6);
    imagedestroy($im);
}
